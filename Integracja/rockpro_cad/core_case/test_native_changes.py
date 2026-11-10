import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.native_changes import observed_pose_changes, guard_native_changes, review_handle_update, guard_handle_update
from rockpro_cad.core_case.contracts import ValidationError


def snapshot():
    return dict(binding={'case_id':'test','parameter_names':['L']},file_guid='test-guid',parameters={'L':'650 mm'},
                members=[dict(id='handles/left',node_id=682,group_id='handles',
                              matrix_world_mm=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[100,0,120,1]]),
                         dict(id='handles/right',node_id=836,group_id='handles',
                              matrix_world_mm=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[550,0,120,1]])])


class NativeChangesTests(unittest.TestCase):
    def test_one_member_move_blocks_and_does_not_rewrite_evidence(self):
        base=snapshot();actual=copy.deepcopy(base);actual['members'][0]['matrix_world_mm'][3][0]+=12
        preserved=copy.deepcopy(actual)
        result=observed_pose_changes(base,actual)
        self.assertEqual(result['changes'][0]['delta'],[12,0,0])
        self.assertEqual(result['changes'][0]['group_id'],'handles')
        with self.assertRaises(ValidationError) as caught:guard_native_changes(base,actual)
        self.assertEqual(caught.exception.code,'SYMMETRY_MANUAL_CONFLICT')
        self.assertEqual(actual,preserved)
    def test_rigid_rotation_and_whole_group_moves_still_need_decision(self):
        base=snapshot();actual=copy.deepcopy(base)
        actual['members'][0]['matrix_world_mm'][:3]=[[0,1,0,0],[-1,0,0,0],[0,0,1,0]]
        self.assertTrue(observed_pose_changes(base,actual)['changes'][0]['rotation_changed'])
        actual=copy.deepcopy(base)
        for row in actual['members']:row['matrix_world_mm'][3][2]+=5
        self.assertEqual(len(observed_pose_changes(base,actual)['changes']),2)
    def test_unchanged_noise_and_resize_are_distinct(self):
        base=snapshot();actual=copy.deepcopy(base);actual['members'][0]['matrix_world_mm'][3][0]+=.001
        self.assertFalse(guard_native_changes(base,actual)['blocked'])
        actual['parameters']['L']='700 mm'
        with self.assertRaises(ValidationError) as caught:guard_native_changes(base,actual)
        self.assertEqual(caught.exception.code,'NATIVE_REPLAN_REQUIRED')
    def test_identity_or_incomplete_scope_cannot_be_accepted(self):
        for mutation in (lambda x:x.update(file_guid='other'),
                         lambda x:x['members'].pop(),
                         lambda x:x['members'].append(copy.deepcopy(x['members'][0]))):
            base=snapshot();actual=copy.deepcopy(base);mutation(actual)
            with self.assertRaises(ValidationError):guard_native_changes(base,actual)


def four_handles(resized=False):
    v=dict(RP_Length=700 if resized else 650,RP_Depth=550 if resized else 500,
           RP_BaseHeight=330 if resized else 300,RP_LidHeight=81,RP_Thickness=9.8,
           RP_DisplayGap=0,RP_JointGap=8.63)
    positions=([[0,137.5,165],[0,412.5,165],[700,137.5,165],[700,412.5,165]] if resized else
               [[0,125,150],[0,375,150],[650,125,150],[650,375,150]])
    rows=[];mapping=[]
    for i,(side,slot) in enumerate([('left',1),('left',2),('right',1),('right',2)]):
        identity=f'handles/{side}/{slot}'
        rotation=[[0,-1,0,0],[-1,0,0,0],[0,0,-1,0]] if side=='left' else [[0,1,0,0],[1,0,0,0],[0,0,-1,0]]
        rows.append(dict(id=identity,node_id=100+i,group_id='handles',matrix_world_mm=rotation+[positions[i]+[1]]))
        mapping.append(dict(logical_id=identity,id=100+i))
    return dict(binding={'case_id':'four-handles'},file_guid='same-guid',
                parameters={k:f'{n} mm' for k,n in v.items()},members=rows),mapping,v


class HandleRevisionTests(unittest.TestCase):
    def test_legal_native_resize_is_not_a_manual_move_and_target_is_previewed(self):
        base,mapping,_=four_handles();current,_,v=four_handles(True)
        result=guard_handle_update(base,current,mapping,2,dict(v,RP_Length=720,RP_Depth=580))
        self.assertFalse(result['blocked']);self.assertTrue(result['parameter_resize_observed'])
        self.assertEqual(result['watched_handles'],4)
        self.assertEqual(result['proposed_members'][-1]['matrix_world_mm'][3],[720,435,165,1])
        self.assertFalse(result['full_case_approved'])
    def test_move_of_fourth_handle_after_resize_is_preserved_and_blocks(self):
        base,mapping,_=four_handles();current,_,v=four_handles(True)
        current['members'][-1]['matrix_world_mm'][3][1]+=12
        preserved=copy.deepcopy(current)
        result=review_handle_update(base,current,mapping,2,v)
        self.assertEqual(result['manual_changes'][0]['id'],'handles/right/2')
        self.assertEqual(result['manual_changes'][0]['delta'],[0,12,0])
        with self.assertRaises(ValidationError):guard_handle_update(base,current,mapping,2,v)
        self.assertEqual(current,preserved)
        current['parameters']['RP_Depth']='500 mm + 50 mm'
        with self.assertRaises(ValidationError):review_handle_update(base,current,mapping,2,v)
