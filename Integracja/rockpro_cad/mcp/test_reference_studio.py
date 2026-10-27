import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

from rockpro_cad.family_concepts import build_catalog, sha, validate_draft
from rockpro_cad.reference_studio import make_handler, load_preview


def fixture(root):
    root = Path(root)
    (root / 'native-02').mkdir()
    (root / 'working-standard-v1').mkdir()
    models = []
    for i in range(1, 8):
        key = f'M{i:02d}'
        source = sha(key.encode())
        raw = json.dumps({'synthetic': True, 'key': key}).encode()
        (root / 'native-02' / (key + '-inventory.json')).write_bytes(raw)
        standard = dict(source_sha256=source, inventory_sha256=sha(raw), physical_part_count=1,
                        nodes=[dict(type='Z_ELEMENT_PART', source_path='root/2', name_raw='Płyta'),
                               dict(type='Z_ELEMENT_ASSEMBLY', source_path='root/3', name_raw='Pokrywa')])
        (root / 'working-standard-v1' / (key + '.json')).write_text(json.dumps(standard), encoding='utf-8')
        models.append(dict(key=key, sha256=source, name=key + '.ics'))
    (root / 'manifest.json').write_text(json.dumps(dict(models=models)), encoding='utf-8')


def draft(catalog):
    return dict(schema='rockpro.concept-draft/1', catalog_binding=catalog['binding'],
                family_id='screens', variant_id='M01', internal_mm=[600, 500, 350],
                cover_height_mm=None, opening='source_unconfirmed', transport='source_unconfirmed', notes='', sliding_shelves=None)


class ReferenceStudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture(self.root)
        self.catalog, self.images = build_catalog(self.root)

    def test_seven_references_are_six_candidates_without_merging_screen_revisions(self):
        self.assertEqual(self.catalog['reference_count'], 7)
        self.assertEqual(self.catalog['family_count'], 6)
        screens = next(f for f in self.catalog['families'] if f['id'] == 'screens')
        self.assertEqual([v['id'] for v in screens['variants']], ['M01', 'M07'])
        self.assertNotEqual(screens['variants'][0]['source_sha256'], screens['variants'][1]['source_sha256'])
        self.assertFalse(self.catalog['cad_generation'])

    def test_changed_inventory_is_refused(self):
        (self.root / 'native-02' / 'M02-inventory.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'binding mismatch'):
            build_catalog(self.root)

    def test_confirmed_shelf_function_does_not_guess_count_stroke_or_cad_readiness(self):
        workstation = next(f for f in self.catalog['families'] if f['id'] == 'workstation')
        self.assertIn('sliding_shelves', workstation['confirmed_functions'])
        d = draft(self.catalog)
        d.update(family_id='workstation', variant_id='M04', sliding_shelves=dict(count=None, requested_travel_mm=None))
        self.assertFalse(validate_draft(d, self.catalog)['cad_ready'])
        d['sliding_shelves'] = dict(count=4, requested_travel_mm=300)
        self.assertTrue(validate_draft(d, self.catalog)['valid_draft'])
        d['sliding_shelves']['count'] = 2.5
        with self.assertRaises(ValueError):
            validate_draft(d, self.catalog)

    def test_unknown_family_variant_and_stale_catalog_are_refused(self):
        for field, value in [('variant_id', 'M02'), ('family_id', 'unknown'), ('catalog_binding', 'old')]:
            d = draft(self.catalog)
            d[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_draft(d, self.catalog)

    def test_preview_requires_bound_source_and_preserves_the_four_slide_values(self):
        self.catalog['workstation_preview'] = dict(source_sha256='a'*64, baseline_external_mm=[800, 740, 880])
        d = draft(self.catalog)
        d.update(family_id='workstation', variant_id='M04', preview=dict(source_sha256='a'*64,
                 external_mm=[900, 800, 950], shelf_travel_mm=[0, 100, 200, 300], covers_visible=False))
        self.assertTrue(validate_draft(d, self.catalog)['valid_draft'])
        for field, value in [('external_mm', [100, 800, 950]), ('shelf_travel_mm', [0, 0, 0, 501]),
                             ('source_sha256', 'b'*64), ('covers_visible', 1)]:
            bad = copy.deepcopy(d)
            bad['preview'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_draft(bad, self.catalog)

    def test_preview_loader_rejects_changed_geometry(self):
        folder = self.root / 'mesh'
        folder.mkdir()
        ref = next(v for f in self.catalog['families'] for v in f['variants'] if v['id'] == 'M04')
        model = dict(kind='workstation_native_preview', units='m', source_sha256=ref['source_sha256'],
                     inventory_sha256=ref['inventory_sha256'], geometry_sha256=sha(b'original'))
        (folder / 'model.json').write_text(json.dumps(model), encoding='utf-8')
        (folder / 'geometry.bin').write_bytes(b'original')
        self.assertEqual(load_preview(folder, self.catalog)[1], model)
        (folder / 'geometry.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            load_preview(folder, self.catalog)

    def test_dimensions_are_requirements_and_do_not_promote_cad_readiness(self):
        d = draft(self.catalog)
        before = copy.deepcopy(d)
        self.assertTrue(validate_draft(d, self.catalog)['valid_draft'])
        self.assertFalse(validate_draft(d, self.catalog)['cad_ready'])
        self.assertEqual(d, before)
        for invalid in (True, float('nan'), float('inf'), 0, -10, 10001, '600'):
            d = draft(self.catalog)
            d['internal_mm'][0] = invalid
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                validate_draft(d, self.catalog)

    def test_http_validates_without_writes_and_blocks_wrong_origin_and_private_paths(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.catalog, {}, 'session'))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port)
            headers = {'Origin': f'http://127.0.0.1:{server.server_port}', 'X-RockPro-Session': 'session'}
            conn.request('POST', '/session/validate', json.dumps(draft(self.catalog)), headers)
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            self.assertFalse(json.loads(response.read())['cad_ready'])
            headers['Origin'] = 'https://other.example'
            conn.request('POST', '/session/validate', '{}', headers)
            response = conn.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
            conn.request('GET', '/session/../manifest.json')
            response = conn.getresponse()
            self.assertEqual(response.status, 404)
            response.read()
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
