"""Portable vendor meshes must be selectable without approving native mounting."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rockpro_cad import supplier_parts as s,studio_parts,part_images

class SupplierPartsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.patch=patch.object(s,'FOLDER',self.root);self.patch.start();self.addCleanup(self.patch.stop)
        mesh=gzip.compress(json.dumps(dict(schema='rockpro.part-mesh/1',units='m',frame='mount.local_uvn')).encode(),mtime=0)
        image=b'\x89PNG\r\n\x1a\nfixture'
        (self.root/'part.mesh.json.gz').write_bytes(mesh);(self.root/'part.png').write_bytes(image)
        self.data=dict(schema='rockpro.supplier-parts/1',assets=dict(test=dict(mesh='part.mesh.json.gz',mesh_sha256=hashlib.sha256(mesh).hexdigest(),image='part.png',image_sha256=hashlib.sha256(image).hexdigest())),items=[dict(id='supplier-test',asset_id='test',sku='ACTUAL-K',name='Actual vendor part',family_id='handles',source_url='https://example.com/part',concept_envelope_mm=[100,70])])
        self.write()
    def write(self):
        (self.root/'index.json').write_text(json.dumps(self.data),encoding='utf-8');s._index.cache_clear()
    def test_definition_resolves_and_mesh_survives_image_decoration(self):
        selected=studio_parts.resolve([dict(part_id='supplier-test',revision=1)])[0]
        self.assertEqual(selected['sku'],'ACTUAL-K')
        self.assertFalse(selected['automatic_placement_approved']);self.assertFalse(selected['production_approved'])
        decorated=part_images.decorate(studio_parts.catalog(),{})
        row=next(r for r in decorated['items'] if r['id']=='supplier-test')
        self.assertTrue(row['show_as_complete_part']);self.assertEqual(row['image']['mesh_compression'],'gzip')
        self.assertIn(row['image']['mesh_url'],s.routes())
    def test_tampered_mesh_and_path_traversal_rejected(self):
        (self.root/'part.mesh.json.gz').write_bytes(b'changed')
        with self.assertRaises(ValueError):s.routes()
        self.data['assets']['test']['mesh']='../outside.gz';self.write()
        with self.assertRaises((ValueError,FileNotFoundError)):s.routes()
    def test_duplicate_ids_rejected(self):
        self.data['items']*=2;self.write()
        with self.assertRaises(ValueError):s.definitions()

if __name__=='__main__':unittest.main()
