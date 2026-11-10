"""Synthetic geometric checks for source display meshes, without CAD or customer data."""
import hashlib
import importlib.util
from array import array
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('source_mesh_compiler',Path(__file__).resolve().parents[3]/'scripts/prepare_source_part_meshes.py')
compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)

class SourceMeshTests(unittest.TestCase):
    def fixture(self):
        p=array('f',[0,0,0,.2,0,0,0,.1,0]);n=array('f',[0,0,1]*3);raw=p.tobytes()+n.tobytes()
        row=dict(node_id=7,offset=0,floats=9,matrix=[1,0,0,0,0,1,0,0,0,0,1,0,20,-30,5,1],materials=[dict(count=3,color=1234)])
        return dict(geometry_sha256=hashlib.sha256(raw).hexdigest(),source_binding={'source_sha256':'test'},elements=[row]),raw

    def test_dimensions_source_colour_identity_and_display_only_survive_translation(self):
        model,raw=self.fixture();out=compiler.compile_mesh(model,raw,[7],(0,0,1))
        self.assertEqual(out['elements'][0]['positions'],[-.1,-.05,0,.1,-.05,0,-.1,.05,0])
        self.assertEqual(out['elements'][0]['normals'],[0,0,1]*3)
        self.assertEqual(out['elements'][0]['materials'],model['elements'][0]['materials'])
        self.assertEqual(out['source_binding'],model['source_binding']);self.assertTrue(out['display_only'])
        self.assertEqual(out['frame_status'],'unconfirmed_visual_frame')
        # A change of visual face rotates, never mirrors or scales, the same triangle.
        rotated=compiler.compile_mesh(model,raw,[7],(0,-1,0))['elements'][0]['positions']
        self.assertAlmostEqual(sum((rotated[k]-rotated[k+3])**2 for k in range(3)),.04)

    def test_mixed_sources_missing_nodes_bad_buffers_and_nonfinite_are_rejected(self):
        model,raw=self.fixture()
        with self.assertRaisesRegex(ValueError,'checksum'):compiler.compile_mesh(model,raw+b'x',[7])
        with self.assertRaisesRegex(ValueError,'nodes'):compiler.compile_mesh(model,raw,[8])
        model['elements'][0]['floats']=10
        with self.assertRaisesRegex(ValueError,'buffer'):compiler.compile_mesh(model,raw,[7])
        model['elements'][0]['floats']=9;model['elements'][0]['matrix'][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'transform'):compiler.compile_mesh(model,raw,[7])

if __name__=='__main__':unittest.main()
