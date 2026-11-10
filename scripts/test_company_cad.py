"""Offline tests: supplier identity, archive safety and honest catalogue coverage."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scan_company_cad import Page, download_metadata
from ingest_company_cad import ingest, safe_step_entries, step_info, write_preserved

STEP = b'ISO-10303-21;\nDATA;\n#1=MANIFOLD_SOLID_BREP();\nENDSEC;\nEND-ISO-10303-21;'
TEST_ROOT = Path(__file__).resolve().parents[1]/'artifacts'/'company-cad-tests'
TEST_ROOT.mkdir(parents=True, exist_ok=True)

def archive(name, raw=STEP, symlink=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        item = zipfile.ZipInfo(name)
        if symlink:
            item.external_attr = 0o120777 << 16
        z.writestr(item, raw)
    return buffer.getvalue()

class SupplierCadTests(unittest.TestCase):
    def test_main_sku_wins_over_recommendations(self):
        p = Page()
        p.feed('<form id="product_addtocart_form" data-product-sku="C1339/30Z"></form>'
               '<div data-product-sku="C1339/31Z"></div>')
        self.assertEqual(p.primary_sku, 'C1339/30Z')

    def test_sku_text_and_nuxt_table(self):
        p = Page(); p.feed('<span itemprop="sku">L907/928</span>')
        self.assertEqual(p.primary_sku, 'L907/928')
        data = [{'format': 1, 'file': 2, 'id': 3, 'categoryId': 4}, 'STEP', 'part.step', 'uuid', 'CAD']
        rows = download_metadata('<script id="__NUXT_DATA__">'+json.dumps(data)+'</script>')
        self.assertEqual(rows[0]['file'], 'part.step')

    def test_step_envelope_and_geometry_required(self):
        self.assertEqual(step_info(STEP)['entities']['MANIFOLD_SOLID_BREP'], 1)
        self.assertFalse(step_info(STEP)['production_approved'])
        for raw in (b'<html>login required</html>', b'ISO-10303-21;END-ISO-10303-21;'):
            with self.assertRaises(ValueError): step_info(raw)

    def test_zip_traversal_absolute_and_symlink_rejected(self):
        for name in ('../bad.step', '/bad.step', 'C:/bad.step', '..\\bad.step'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_step_entries(archive(name))
        with self.assertRaises(ValueError): safe_step_entries(archive('link.step', symlink=True))

    def test_only_step_is_extracted(self):
        self.assertEqual(safe_step_entries(archive('folder/valid.step')), [('valid.step', STEP)])
        with self.assertRaises(ValueError): safe_step_entries(archive('run.exe'))

    def test_changed_files_preserved(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as d:
            p = Path(d)/'part.step'
            self.assertEqual(write_preserved(p, STEP), p)
            other = write_preserved(p, STEP+b'\n')
            self.assertNotEqual(other, p)
            self.assertEqual(p.read_bytes(), STEP)

    def test_duplicate_rows_and_variant_conflicts_not_merged(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as d:
            root = Path(d); evidence = root/'evidence'; evidence.mkdir()
            src = root/'model.zip'; src.write_bytes(archive('part.step'))
            base = dict(code='E2220', name='Profile', category='Profile i listwy', manufacturer='Penn Elcom',
                        source_url='https://www.penn-elcom.com/profile', primary_manufacturer_sku='E2220-4M',
                        status='source_product_mismatch', identity='different_product_or_variant',
                        cad_links=['https://www.3dcontentcentral.com/download-model.aspx?catalogid=6237&id=1'])
            items = [dict(base, id='a'), dict(base, id='b'), dict(base, id='pending', cad_links=[base['cad_links'][0].replace('id=1','id=2')])]
            (evidence/'discovery.json').write_text(json.dumps(dict(catalog_sha256='test',items=items)), encoding='utf-8')
            controls = dict(selects=[dict(id='', options=[])])
            (evidence/'browser-downloads.json').write_text(json.dumps([dict(model_id='1',configuration='E2220',result=str(src),controls=controls)]), encoding='utf-8')
            result = ingest(evidence, root/'out')
            self.assertEqual(len(result['items']), 3)
            self.assertEqual([r['status'] for r in result['items']], ['configuration_needs_review','configuration_needs_review','model_download_pending'])
            self.assertTrue(result['items'][0]['reference_files'])
            self.assertFalse(result['items'][0]['asset_files'])
            self.assertEqual(result['summary']['errors'], 0)

if __name__ == '__main__': unittest.main()
