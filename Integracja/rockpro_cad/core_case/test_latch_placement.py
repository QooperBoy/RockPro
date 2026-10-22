import copy
import unittest
from latch_placement import plan_latch_pairs


def source():
    rows=[]
    for side,x in [('left',150),('right',764)]:
        for role,bounds in [('lid',[-15,-4,0,15,8,20]),('base',[-18,-5,-30,18,10,0])]:
            rows.append(dict(id=len(rows)+1,role=role,side=side,
                             matrix_world_mm=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[x,11.9,223.59,1]],
                             local_bounds_mm=bounds))
    return rows


class LatchPlacementSmoke(unittest.TestCase):
    def test_A_identity(self):
        rows=source();before=copy.deepcopy(rows)
        plan=plan_latch_pairs(rows,[0,0,0],[914,602,352],[914,602,352])
        self.assertEqual(rows,before)
        self.assertEqual([r['matrix_world_mm'] for r in plan['occurrences']],
                         [r['matrix_world_mm'] for r in rows])
        self.assertFalse(plan['production_approved'])

    def test_resize_pairs_and_symmetry(self):
        rows=source();plan=plan_latch_pairs(rows,[0,0,0],[914,602,352],[1100,720,410])
        for original,row in zip(rows,plan['occurrences']):
            delta=[186 if row['side']=='right' else 0,0,58]
            self.assertEqual(row['translation_mm'],delta)
            self.assertEqual(row['matrix_world_mm'][:3],original['matrix_world_mm'][:3])
            self.assertEqual(row['matrix_world_mm'][3][:3],
                             [original['matrix_world_mm'][3][i]+delta[i] for i in range(3)])
        for left,right in zip(plan['occurrences'][:2],plan['occurrences'][2:]):
            self.assertAlmostEqual(left['bbox_center_world_mm'][0]+right['bbox_center_world_mm'][0],1100)
            self.assertEqual(left['bbox_center_world_mm'][1:],right['bbox_center_world_mm'][1:])

    def test_invalid_input(self):
        for bad in ('missing','duplicate','nan','scale','splitpair','asymmetry','small','short','narrow'):
            rows=source();target=[1100,720,410]
            if bad=='missing':rows.pop()
            if bad=='duplicate':rows[1]['id']=rows[0]['id']
            if bad=='nan':rows[0]['matrix_world_mm'][3][0]=float('nan')
            if bad=='scale':rows[0]['matrix_world_mm'][0][0]=2
            if bad=='splitpair':rows[1]['matrix_world_mm'][3][2]+=1
            if bad=='asymmetry':rows[2]['matrix_world_mm'][3][0]+=1
            if bad=='small':target[2]=100
            if bad=='short':target[2]=104.14
            if bad=='narrow':target[0]=301
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                plan_latch_pairs(rows,[0,0,0],[914,602,352],target)


if __name__=='__main__':unittest.main()
