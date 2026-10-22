import copy
import unittest
from hinge_placement import plan_hinge_pairs


def source():
    rows=[]
    for side,x in [('left',155),('right',769)]:
        for role,bounds in [('lid',[-15,-4,0,5,8,20]),('base',[-15,-4,-30,5,8,0])]:
            rows.append(dict(id=len(rows)+1,role=role,side=side,
                             matrix_world_mm=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[x,610,240,1]],
                             local_bounds_mm=bounds))
    return rows


class HingePlacementSmoke(unittest.TestCase):
    def test_identity_blocked_without_parity_proof(self):
        rows=source();before=copy.deepcopy(rows)
        plan=plan_hinge_pairs(rows,[0,0,0],[914,602,352],[914,602,352])
        self.assertEqual(rows,before)
        self.assertEqual(plan['status'],'blocked');self.assertEqual(plan['occurrences'],[])
        self.assertEqual([r['matrix_world_mm'] for r in plan['predicted_occurrences']],
                         [r['matrix_world_mm'] for r in rows])
        self.assertEqual(plan['predicted_occurrences'][0]['root_to_bbox_center_world_mm'][0],-5)

    def test_resize_shared_motion_and_center_symmetry(self):
        rows=source()
        plan=plan_hinge_pairs(rows,[0,0,0],[914,602,352],[1100,720,410],source_pose_verified=True)
        for original,row in zip(rows,plan['occurrences']):
            self.assertEqual(row['translation_mm'],[186 if row['side']=='right' else 0,118,58])
            self.assertEqual(row['matrix_world_mm'][:3],original['matrix_world_mm'][:3])
        for left,right in zip(plan['occurrences'][:2],plan['occurrences'][2:]):
            self.assertEqual(left['bbox_center_world_mm'][0]+right['bbox_center_world_mm'][0],1100)
        self.assertFalse(plan['production_approved'])

    def test_invalid_or_asymmetric_input(self):
        for bad in ('missing','duplicate','nan','scale','asymmetry','splitpair','small'):
            rows=source();target=[1100,720,410]
            if bad=='missing':rows.pop()
            if bad=='duplicate':rows[1]['id']=rows[0]['id']
            if bad=='nan':rows[0]['matrix_world_mm'][3][0]=float('nan')
            if bad=='scale':rows[0]['matrix_world_mm'][0][0]=2
            if bad=='asymmetry':rows[0]['local_bounds_mm'][0]+=2
            if bad=='splitpair':rows[1]['matrix_world_mm'][3][0]+=1
            if bad=='small':target[0]=300
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                plan_hinge_pairs(rows,[0,0,0],[914,602,352],target)


if __name__=='__main__':unittest.main()
