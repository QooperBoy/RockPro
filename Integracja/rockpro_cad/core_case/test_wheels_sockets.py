import copy
import itertools
import unittest
from wheels_sockets import preview_wheels_sockets


def source():
    wheels=[];sockets=[]
    for index,(x,y) in enumerate(itertools.product((150,764),(80,522))):
        for rows,z,node_id in [(wheels,-50,index+1),(sockets,350,index+11)]:
            rows.append(dict(id=node_id,matrix_world_mm=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[x-2,y-3,z-4,1]],
                             local_bounds_mm=[0,1,2,4,5,6]))
    return wheels,sockets


class WheelSocketSmoke(unittest.TestCase):
    def test_missing_poses_are_never_invented(self):
        wheels,sockets=source();wheels[2]['matrix_world_mm']=None;wheels[3]['matrix_world_mm']=None
        before=copy.deepcopy((wheels,sockets))
        report=preview_wheels_sockets(wheels,sockets,[0,0,0],[914,602,352],[914,602,352])
        self.assertEqual((wheels,sockets),before)
        self.assertEqual(report['status'],'blocked');self.assertEqual(report['occurrences'],[])
        self.assertEqual(report['missing_wheel_pose_ids'],[3,4])
        self.assertEqual(len(report['predicted_occurrences']),6)
        self.assertEqual(len(report['candidate_pairs']),2)

    def test_resize_preserves_shared_xy_and_whole_orientations(self):
        wheels,sockets=source()
        report=preview_wheels_sockets(wheels,sockets,[0,0,0],[914,602,352],[1100,720,410])
        for row in report['predicted_occurrences']:
            self.assertEqual(row['translation_mm'][:2],[row['slot'][0]*186,row['slot'][1]*118])
            self.assertEqual(row['matrix_world_mm'][:3],row['source_matrix_world_mm'][:3])
        self.assertTrue(all(pair['source_delta_xy_mm']==[0,0] for pair in report['candidate_pairs']))
        self.assertFalse(report['production_approved'])

    def test_invalid_or_asymmetric_input(self):
        for bad in ('missing','duplicate','nan','asymmetry','scale'):
            wheels,sockets=source()
            if bad=='missing':sockets.pop()
            if bad=='duplicate':sockets[1]['id']=sockets[0]['id']
            if bad=='nan':sockets[0]['matrix_world_mm'][3][0]=float('nan')
            if bad=='asymmetry':sockets[0]['matrix_world_mm'][3][1]+=1
            if bad=='scale':wheels[0]['matrix_world_mm'][0][0]=2
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                preview_wheels_sockets(wheels,sockets,[0,0,0],[914,602,352],[1100,720,410])


if __name__=='__main__':unittest.main()
