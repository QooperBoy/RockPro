import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rockpro_cad import company_catalog as c


def record(code='PN - H7159',suffix='1',duplicate=False):
    return dict(id='company-'+suffix*24,code=code,name='Uchwyt testowy',duplicate_code=duplicate,
        image=None,production_approved=False,geometry_approved=False,cached_stock_raw='0',
        cutout_note='Kontur do sprawdzenia',source=dict(stock_cell='B10'))


class CompanyCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'catalog.json'
        self.env=patch.dict(os.environ,ROCKPRO_COMPANY_CATALOG=str(self.path));self.env.start();self.addCleanup(self.env.stop)
        self.data=dict(schema='rockpro.company-catalog/1',source=dict(sha256='a'*64),items=[record()],summary=dict(records=1))
    def write(self):
        self.path.write_text(json.dumps(self.data),encoding='utf-8');c._load.cache_clear();c._image_routes.cache_clear()
    def test_exact_codes_preserve_variants_and_snapshot_values(self):
        self.data['items'] += [record('PN - H7159K','2'),dict(record('EG - 0113','3'),cached_stock_raw=None),dict(record('Test','4'),cached_stock_raw='1.25')];self.write()
        parts=dict(items=[dict(id='H7159',sku='H7159',name='Uchwyt',aliases=[],image=dict(mesh_url='mesh'),component_only=False)])
        result=c.catalog(parts)
        self.assertEqual(result['items'][0]['geometry_candidates'][0]['id'],'H7159')
        self.assertFalse(result['items'][1]['geometry_candidates'])
        self.assertEqual([r['cached_stock_raw'] for r in result['items']],['0','0',None,'1.25'])
        self.assertEqual(c.normalize_code('EG - 0113'),'EG-0113')
        self.assertNotEqual(c.normalize_code('R1606M'),c.normalize_code('R1606/M'))
        self.assertFalse(result['items'][0]['geometry_approved'])
    def test_duplicate_codes_are_not_merged_or_auto_matched(self):
        self.data['items']=[record(duplicate=True),record(suffix='2',duplicate=True)];self.write()
        result=c.catalog(dict(items=[dict(id='handle',sku='H7159',name='Uchwyt')]))
        self.assertEqual(len(result['items']),2)
        self.assertTrue(all(not r['geometry_candidates'] for r in result['items']))
    def test_bad_image_and_approval_are_refused(self):
        self.data['items'][0]['production_approved']=True;self.write()
        with self.assertRaises(ValueError):c.catalog()
        self.data['items'][0]['production_approved']=False
        image=Path(self.temp.name)/'img.png';image.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        self.data['items'][0]['image']=dict(file='img.png',sha256=hashlib.sha256(image.read_bytes()).hexdigest());self.write()
        self.assertEqual(len(c.images()),1)
        image.write_bytes(b'changed');c._image_routes.cache_clear()
        with self.assertRaises(ValueError):c.images()
        self.data['items'][0]['image']=dict(file='../outside.png',sha256='a'*64);self.write()
        with self.assertRaises((ValueError,FileNotFoundError)):c.images()
    def test_source_dataset_is_not_mutated_by_presentation(self):
        self.write();before=self.path.read_bytes();r=c.catalog();r['items'][0]['name']='changed'
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(c.catalog()['items'][0]['name'],'Uchwyt testowy')
    def test_missing_optional_provider_has_empty_view(self):
        self.assertEqual(c.catalog()['items'],[])

    def test_all_picker_records_keep_duplicate_ids_without_financial_fields(self):
        self.data['items']=[record(duplicate=True),record(suffix='2',duplicate=True)]
        for row in self.data['items']:
            row.update(name='Uchwyt',category='Uchwyty',manufacturer='Test',price_raw='secret-price')
        self.write()
        parts=c.picker_entries(dict(items=[],categories={}))
        self.assertEqual(len(parts['items']),2)
        self.assertNotEqual(parts['items'][0]['id'],parts['items'][1]['id'])
        self.assertTrue(all(r['catalog_only'] and not r['selectable'] for r in parts['items']))
        self.assertNotIn('secret-price',json.dumps(parts))
        self.assertTrue(all('cached_stock_raw' not in r and 'source' not in r for r in parts['items']))


if __name__=='__main__':unittest.main()
