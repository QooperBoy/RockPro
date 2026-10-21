import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.native_reader import read_poses, validate_matrix
from rockpro_cad.core_case.catalog_native import compare_body_signatures, validate_source_binding, native_volume
from rockpro_cad.core_case.native import NativeExecutionError


IDENTITY = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]


class PoseAdapter:
    def root(self): return 0
    def identity(self,node): return {"id":node,"name":str(node),"kind":"scene" if node==0 else "part","type":0 if node==0 else 1}
    def child_count(self,node): return 1 if node==0 else 0
    def child_at(self,node,index): return 1
    def matrix(self,node,global_space): return copy.deepcopy(IDENTITY)
    def bbox(self,node,kind): return {"valid":False,"reason":"unavailable_sentinel"}


class NativeReadEvidenceTests(unittest.TestCase):
    def test_sdk_volume_output_order(self):
        self.assertEqual(native_volume([0.0, 1.25e-6]),(0.0,1.25e-6))
        with self.assertRaises(NativeExecutionError): native_volume([0.001,0.0])
    def test_unavailable_bbox_cannot_be_complete(self):
        result=read_poses(PoseAdapter())
        self.assertEqual(result["status"],"partial")
        self.assertEqual(result["errors"][0]["field"],"bounding_box_local")
        self.assertEqual(result["rows"][1]["matrix_world_mm"],IDENTITY)

    def test_reflection_is_retained_as_raw_diagnostic_not_executable_rotation(self):
        class Reflected(PoseAdapter):
            def matrix(self,node,global_space):
                value=copy.deepcopy(IDENTITY);value[0][0]=-1;return value
        result=read_poses(Reflected())
        row=result["rows"][1]
        self.assertNotIn("matrix_world_mm",row)
        self.assertEqual(row["matrix_world_mm_raw"][0][0],-1)
        self.assertEqual(result["status"],"partial")

    def test_native_shape_signature_refuses_body_and_pose_drift(self):
        before=[{"occurrence_path":[0],"kind":"part","name":"part","local_bounds_mm":[0,0,0,1,2,3],
            "volume_m3":1e-9,"faces":12,"edges":20,"vertices":8,"lumps":1,"matrix_parent_mm":copy.deepcopy(IDENTITY)}]
        compare_body_signatures(before,copy.deepcopy(before))
        for field in ("faces","volume_m3","local_bounds_mm","matrix_parent_mm"):
            after=copy.deepcopy(before)
            if field=="faces": after[0][field]+=1
            elif field=="volume_m3": after[0][field]*=1.01
            elif field=="local_bounds_mm": after[0][field][0]+=0.1
            else: after[0][field][3][0]+=1
            with self.subTest(field=field),self.assertRaises(NativeExecutionError):
                compare_body_signatures(before,after)

    def test_source_binding_must_be_exact_and_proper(self):
        binding={"schema_version":1,"source_path":r"C:\source.ics","source_sha256":"a"*64,
            "source_guid":"guid","node_id":10,"node_name":"H7159","expected_world_matrix_mm":copy.deepcopy(IDENTITY)}
        self.assertEqual(validate_source_binding(binding),binding)
        bad=copy.deepcopy(binding);bad["expected_world_matrix_mm"][0][0]=-1
        with self.assertRaises(ValueError): validate_source_binding(bad)
        bad=copy.deepcopy(binding);bad["node_id"]=True
        with self.assertRaises(ValueError): validate_source_binding(bad)
        bad=copy.deepcopy(binding);bad["schema_version"]=True
        with self.assertRaises(ValueError): validate_source_binding(bad)

    def test_nested_assembly_pose_preserved(self):
        before=[{"occurrence_path":[0],"kind":"assembly","name":"nested", "matrix_parent_mm":copy.deepcopy(IDENTITY)}]
        after=copy.deepcopy(before)
        after[0]["matrix_parent_mm"][3][1]=10
        with self.assertRaises(NativeExecutionError): compare_body_signatures(before,after)

    def test_internal_source_mirror_can_only_be_preserved_explicitly(self):
        mirrored=copy.deepcopy(IDENTITY);mirrored[0][0]=-1
        with self.assertRaises(ValueError): validate_matrix(mirrored)
        self.assertEqual(validate_matrix(mirrored,allow_reflection=True),mirrored)
        before=[{"occurrence_path":[0],"kind":"assembly","name":"opaque", "matrix_parent_mm":mirrored}]
        compare_body_signatures(before,copy.deepcopy(before))
        after=copy.deepcopy(before);after[0]["matrix_parent_mm"]=copy.deepcopy(IDENTITY)
        with self.assertRaises(NativeExecutionError): compare_body_signatures(before,after)


if __name__=="__main__": unittest.main()
