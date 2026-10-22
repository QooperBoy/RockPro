"""Independent checks of one candidate mounting datum and wall-relative pair."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.hardware_poc import candidate_datum, plan_hardware_poc, validate_pair
from rockpro_cad.core_case.hardware_poc_native import _direct_parent_box
from rockpro_cad.core_case.native_reader import transform_bbox


def evidence():
    return {'asset_hash':'a'*64,'asset_signature':[{'kind':'assembly','name':'H7159'}],
      'planar_faces_parallel_local_xz':[
       {'face_id':194,'plane_data_type':True,'point_mm':[0,0,0],'normal':[0,1,0],
        'vertex_ids':[1,2,3,4],'vertices_mm':[[-80.5,0,-53.5],[80.5,0,-53.5],[80.5,0,53.5],[-80.5,0,53.5]]},
       {'face_id':353,'plane_data_type':False,'point_mm':[0,1.2,0],'normal':[0,1,0],
        'vertex_ids':[5,6,7,8],'vertices_mm':[[-80.5,1.2,-53.5],[80.5,1.2,-53.5],[80.5,1.2,53.5],[-80.5,1.2,53.5]]}],
      'document':{'file_guid':'asset-guid'},'source_world_matrix_mm':[[0,-1,0,0],[-1,0,0,0],[0,0,-1,0],[558,1350,-1377,1]]}


class MountPlanTests(unittest.TestCase):
    def setUp(self):self.datum=candidate_datum(evidence(),contact_face_id=194,exterior_face_id=353,expected_asset_sha256='a'*64,expected_guid='asset-guid')
    def plan(self,size=(900,600,330)):return plan_hardware_poc(list(size),self.datum)
    def test_exact_inventory_and_one_product(self):
        p=self.plan();self.assertEqual(len(p['proxy_plan']['occurrences']),11)
        self.assertEqual(len(p['handles']),2);self.assertEqual(p['expected_physical_parts'],37)
        self.assertEqual(p['device']['shape'],[300,220,100]);self.assertFalse(p['production_approved'])
    def test_pair_anchors_independent_resize_and_return(self):
        base=self.plan()
        for size in [(1100,600,330),(900,720,330),(900,600,410),(1100,720,410),(900,600,330)]:
            p=self.plan(size);validate_pair(p,p['handles'])
            left,right=p['handles'];self.assertAlmostEqual(left['matrix_mm'][3][0]+right['matrix_mm'][3][0],0)
            self.assertEqual(left['matrix_mm'][3][1],-size[1]/2)
            self.assertEqual(abs(left['matrix_mm'][3][0])+80.5+100,size[0]/2)
            self.assertEqual(p['device'],base['device'])
        self.assertEqual(self.plan(),base)
    def test_reject_missing_duplicate_or_drifted_pair(self):
        p=self.plan()
        for rows in [p['handles'][:1],[p['handles'][0]]*2]:
            with self.assertRaises(ValueError):validate_pair(p,rows)
        for position in [(3,0),(3,1),(3,2),(0,0)]:
            rows=copy.deepcopy(p['handles']);rows[0]['matrix_mm'][position[0]][position[1]]+=.01
            with self.assertRaises(ValueError):validate_pair(p,rows)
    def test_reject_reflection_scaling_nonnumeric(self):
        p=self.plan()
        for value in [-1,1.01,float('nan')]:
            rows=copy.deepcopy(p['handles']);rows[0]['matrix_mm'][0][0]=value
            with self.assertRaises(ValueError):validate_pair(p,rows)
    def test_reject_corrupted_plan_as_its_own_oracle(self):
        for kind in ['wall','rotation','edge']:
            p=self.plan()
            for row in p['handles']:
                if kind=='wall':row['matrix_mm'][3][1]+=30
                if kind=='rotation':row['matrix_mm'][:3]=[[1,0,0,0],[0,1,0,0],[0,0,1,0]]
                if kind=='edge':row['matrix_mm'][3][0]/=2
            with self.assertRaises(ValueError):validate_pair(p,p['handles'])
    def test_reject_contradictory_datum_metadata(self):
        for key,value in [('outward',[0,-1,0]),('up',[0,0,1]),('origin_mm',[1000,0,0])]:
            d=copy.deepcopy(self.datum);d[key]=value
            with self.assertRaises(ValueError):plan_hardware_poc([900,600,330],d)
    def test_reject_small_walls_or_no_device_clearance(self):
        for size in [[500,600,330],[900,230,330],[900,600,190],[True,600,330]]:
            with self.assertRaises(ValueError):self.plan(size)
    def test_reject_wrong_identity_missing_or_ambiguous_plane(self):
        for field,value in [('asset_hash','b'*64),('document',{'file_guid':'wrong'})]:
            e=evidence();e[field]=value
            with self.assertRaises(ValueError):candidate_datum(e,contact_face_id=194,exterior_face_id=353,expected_asset_sha256='a'*64,expected_guid='asset-guid')
        for mutate in ['missing','duplicate','noncoplanar','collinear']:
            e=evidence()
            if mutate=='missing':e['planar_faces_parallel_local_xz'].pop(0)
            if mutate=='duplicate':e['planar_faces_parallel_local_xz'].append(copy.deepcopy(e['planar_faces_parallel_local_xz'][0]))
            if mutate=='noncoplanar':e['planar_faces_parallel_local_xz'][0]['vertices_mm'][0][1]=.1
            if mutate=='collinear':e['planar_faces_parallel_local_xz'][0]['vertices_mm']=[[0,0,0],[1,0,0],[2,0,0],[3,0,0]]
            with self.assertRaises(ValueError):candidate_datum(e,contact_face_id=194,exterior_face_id=353,expected_asset_sha256='a'*64,expected_guid='asset-guid')


class NativeParentBoundsTests(unittest.TestCase):
    def test_nested_part_bounds_already_include_own_translation(self):
        class API:IZPart=object()
        class Part:
            def QueryInterface(self,interface):return self
            def GetBoundingBox(self,local):
                self.assert_false=local is False
                # Local [-2,-3,-4,2,3,4] already moved +5mm in parent X.
                return [.003,-.003,-.004,.007,.003,.004]
        parent=[[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[100,-300,125,1]]
        part=Part();raw=_direct_parent_box(part,API);world=transform_bbox(raw,parent)
        self.assertTrue(part.assert_false)
        self.assertEqual(raw,[3,-3,-4,7,3,4])
        self.assertEqual(world,[103,-303,121,107,-297,129])
        # Applying the part's +5mm transform a second time would produce108..112.
        self.assertNotEqual(world[0],108)

    def test_non_axis_aabb_transform_is_conservative_not_exact_shape_bounds(self):
        s=2**-.5
        parent=[[s,s,0,0],[-s,s,0,0],[0,0,1,0],[0,0,0,1]]
        # Unit disk has exact XY bounds +/-1 after rotation. Its transformed
        # local square AABB instead expands to sqrt(2), so this operation is
        # exact for this pinned POC's signed-axis frames only.
        world=transform_bbox([-1,-1,-1,1,1,1],parent)
        self.assertAlmostEqual(world[3],2**.5)
        self.assertGreater(world[3],1)


if __name__=='__main__':unittest.main()
