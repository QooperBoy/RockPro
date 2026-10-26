import copy
import hashlib
import json
import unittest
from rockpro_cad.core_case.working_mounts import build_working_standard,plan_component_translation


def fixture(source='a'*64):
    identity=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
    def row(i,path,kind):return dict(id=i,path=path,type=kind,name='source',
                                    world_mm=copy.deepcopy(identity),parent_mm=copy.deepcopy(identity))
    rows=[row(1,'root','Z_ELEMENT_UNKNOWN'),row(2,'root/2','Z_ELEMENT_ASSEMBLY'),
          row(3,'root/2/3','Z_ELEMENT_PART'),row(4,'root/4','Z_ELEMENT_PART')]
    data={'source_sha256':source,'rows':rows,'errors':[],'file_guid':'same-guid'}
    return data


def build(data):
    raw=json.dumps(data).encode('utf-8')
    return build_working_standard(raw,data['source_sha256'],hashlib.sha256(raw).hexdigest())


class WorkingMountTests(unittest.TestCase):
    def test_source_hash_not_shared_file_guid_defines_reference_identity(self):
        a=build(fixture());b=build(fixture('b'*64))
        self.assertNotEqual(a['nodes'][0]['source_reference_key'],b['nodes'][0]['source_reference_key'])
        self.assertEqual(a['nodes'][2]['requires_plywood_cutout'],'unknown')
        self.assertFalse(a['executable_template']);self.assertFalse(a['production_approved'])

    def test_changed_inventory_or_source_rejected(self):
        raw=json.dumps(fixture()).encode()
        with self.assertRaisesRegex(ValueError,'Inventory revision'):build_working_standard(raw,'a'*64,'c'*64)
        with self.assertRaisesRegex(ValueError,'Source revision'):build_working_standard(raw,'b'*64,hashlib.sha256(raw).hexdigest())

    def test_translation_preserves_reflections_fixed_parts_and_original_data(self):
        data=fixture();data['rows'][1]['world_mm'][0][0]=-1
        data['rows'][2]['world_mm'][0][0]=-1
        before=copy.deepcopy(data);standard=build(data)
        plan=plan_component_translation(standard,'root/2/3',[10,20,30])
        self.assertEqual(plan['root_geometry_parent_translation_mm'],[-10,20,30])
        self.assertEqual(plan['targets'][2]['world_frame_mm'][0][0],-1)
        self.assertEqual(plan['targets'][2]['world_frame_mm'][3][:3],[10,20,30])
        self.assertEqual(plan['targets'][3]['world_frame_mm'][3][:3],[0,0,0])
        self.assertEqual(data,before);self.assertFalse(plan['catalog_geometry_scaled'])

    def test_invalid_frames_missing_parents_and_nonfinite_motion_rejected(self):
        data=fixture();data['rows'][1]['world_mm'][0][0]=2
        with self.assertRaisesRegex(ValueError,'scaling'):build(data)
        data=fixture();data['rows'].pop(1)
        with self.assertRaisesRegex(ValueError,'hierarchy'):build(data)
        standard=build(fixture())
        with self.assertRaisesRegex(ValueError,'Finite'):plan_component_translation(standard,'root/2',[0,float('nan'),0])
        with self.assertRaisesRegex(ValueError,'explicit'):plan_component_translation(standard,'root/999',[0,0,0])
        standard['nodes'][1]['world_frame_mm'][3][0]=1.7e308
        with self.assertRaisesRegex(ValueError,'Finite'):plan_component_translation(standard,'root/2',[1.7e308,0,0])


if __name__=='__main__':unittest.main()
