import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.handle_decisions import review_handle_decision
from rockpro_cad.core_case.contracts import ValidationError
from test_native_changes import four_handles


class HandleDecisionTests(unittest.TestCase):
    def edited(self):
        baseline,mapping,values=four_handles();current,_,_=four_handles(True)
        current['members'][-1]['matrix_world_mm'][3][1]+=12
        return baseline,current,mapping,values

    def test_no_choice_blocks_and_adoption_preserves_offset_at_new_anchor(self):
        b,c,m,v=self.edited();v.update(RP_Length=720,RP_Depth=600,RP_BaseHeight=340)
        evidence=copy.deepcopy(c)
        pending=review_handle_decision(b,c,m,2,v);self.assertTrue(pending['blocked'])
        adopted=review_handle_decision(b,c,m,2,v,'adopt_offset')
        self.assertFalse(adopted['blocked']);self.assertEqual(adopted['state']['offsets_mm']['handles/right/2'],[0,12,0])
        self.assertEqual(adopted['proposed_members'][-1]['matrix_world_mm'][3][:3],[720,462,170])
        self.assertEqual(c,evidence);self.assertFalse(adopted['full_case_approved'])

    def test_prior_accepted_offset_is_not_reported_as_a_new_manual_change(self):
        b,c,m,v=self.edited();target=dict(v,RP_Length=700,RP_Depth=550,RP_BaseHeight=330)
        adopted=review_handle_decision(b,c,m,2,target,'adopt_offset')
        repeated=review_handle_decision(b,c,m,2,target,prior_state=adopted['state'])
        self.assertFalse(repeated['blocked']);self.assertEqual(repeated['manual_changes'],[])
        repeated['state']['offsets_mm']['handles/right/2'][1]=999
        self.assertEqual(adopted['state']['offsets_mm']['handles/right/2'][1],12)

    def test_restore_rule_is_explicit_and_preserve_absolute_detects_detached_wall(self):
        b,c,m,v=self.edited();v.update(RP_Length=720,RP_Depth=600)
        restore=review_handle_decision(b,c,m,2,v,'restore_rule');self.assertFalse(restore['blocked'])
        self.assertEqual(restore['state']['offsets_mm']['handles/right/2'],[0,0,0])
        preserve=review_handle_decision(b,c,m,2,v,'preserve_absolute')
        self.assertTrue(preserve['blocked']);self.assertIn('HANDLE_OFF_MOUNTING_WALL:handles/right/2',preserve['issues'])

    def test_smaller_wall_requires_fit_for_accepted_offsets(self):
        b,c,m,v=self.edited();c['members'][-1]['matrix_world_mm'][3][1]+=60
        decision=review_handle_decision(b,c,m,2,dict(v,RP_Depth=500),'adopt_offset')
        self.assertTrue(decision['blocked']);self.assertIsNone(decision['state'])

    def test_unknown_identity_rotation_and_unanchored_manual_are_not_silently_adopted(self):
        b,c,m,v=self.edited();manual=review_handle_decision(b,c,m,2,v,'leave_manual')
        self.assertTrue(manual['blocked']);self.assertIn('MANUAL_MEMBERS_REQUIRE_APPROVED_ANCHORS',manual['issues'])
        c['members'][-1]['matrix_world_mm'][:3]=[[1,0,0,0],[0,1,0,0],[0,0,1,0]]
        self.assertTrue(review_handle_decision(b,c,m,2,v,'adopt_offset')['blocked'])
        c['members'][-1]['node_id']=999
        with self.assertRaises(ValidationError):review_handle_decision(b,c,m,2,v,'adopt_offset')


if __name__=='__main__':unittest.main()
