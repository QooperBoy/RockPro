"""The read-only viewer serves one verified revision for its entire session."""
from contextlib import contextmanager
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from rockpro_cad import layer_viewer
from rockpro_cad.part_registry import contract


def dataset(root, geometry=b'first native mesh'):
    model = {'kind': 'ironcad_native_mesh', 'registry': contract(),
             'geometry_sha256': hashlib.sha256(geometry).hexdigest()}
    model_bytes = json.dumps(model, ensure_ascii=False).encode('utf-8')
    (root / 'model.json').write_bytes(model_bytes)
    (root / 'geometry.bin').write_bytes(geometry)
    return model_bytes, geometry


@contextmanager
def serving(handler):
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/test/'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class LayerRevisionTests(unittest.TestCase):
    def test_verified_bytes_are_frozen_across_file_replacement_and_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected_model, expected_geometry = dataset(root)
            handler = layer_viewer.make_handler(root, 'test')
            # A later export must not silently change an already opened revision.
            dataset(root, b'other revision with a valid new checksum')
            with serving(handler) as url:
                for name, expected in [('model.json', expected_model), ('geometry.bin', expected_geometry)]:
                    with urlopen(url + name, timeout=3) as response:
                        self.assertEqual(response.read(), expected)
                        self.assertEqual(int(response.headers['Content-Length']), len(expected))
                (root / 'geometry.bin').unlink()
                with urlopen(url + 'geometry.bin', timeout=3) as response:
                    self.assertEqual(response.read(), expected_geometry)

    def test_malformed_or_mismatched_revision_is_rejected_before_serving(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for bad in [[], {'kind': 'other'},
                        {'kind': 'ironcad_native_mesh', 'geometry_sha256': '0' * 64},
                        {'kind': 'ironcad_native_mesh', 'geometry_sha256': None},
                        {'kind': 'ironcad_native_mesh', 'registry': None}]:
                dataset(root)
                (root / 'model.json').write_text(json.dumps(bad), encoding='utf-8')
                with self.subTest(model=bad), self.assertRaises(ValueError):
                    layer_viewer.make_handler(root, 'test')

    def test_limits_apply_to_bytes_read_and_allow_exact_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model, geometry = dataset(root)
            with patch.object(layer_viewer, 'MAX_MODEL_BYTES', len(model)), \
                 patch.object(layer_viewer, 'MAX_GEOMETRY_BYTES', len(geometry)):
                layer_viewer.make_handler(root, 'test')
                (root / 'model.json').write_bytes(model + b' ')
                with self.assertRaisesRegex(ValueError, 'limit'):
                    layer_viewer.make_handler(root, 'test')
                (root / 'model.json').write_bytes(model)
                (root / 'geometry.bin').write_bytes(geometry + b'x')
                with self.assertRaisesRegex(ValueError, 'limit'):
                    layer_viewer.make_handler(root, 'test')


if __name__ == '__main__':
    unittest.main()
