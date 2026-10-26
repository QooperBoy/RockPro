import itertools
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.t1_mounting import corner_pose, support_dimensions, hinge_profile_interval, SOCKET_SEAT, PARAMETERS_PL


class MountingTests(unittest.TestCase):
    def test_all_corner_planes_face_case_interior(self):
        for size in [(600,500,350), (760,620,430)]:
            for top,right,rear in itertools.product((False,True),repeat=3):
                r,p=corner_pose(top,right,rear,size)
                for k in range(3):
                    j=next(j for j in range(3) if r[k][j])
                    high=(right,rear,top)[j]
                    self.assertAlmostEqual(p[j]+16.5*r[k][j],size[j] if high else 0)
                    self.assertEqual(-r[k][j],-1 if high else 1)
                det=sum(r[0][i]*(r[1][(i+1)%3]*r[2][(i+2)%3]-r[1][(i+2)%3]*r[2][(i+1)%3]) for i in range(3))
                self.assertEqual(det,1)

    def test_pad_stops_before_profile(self):
        for depth in (500,620,1000):
            start,length=support_dimensions(depth)
            self.assertEqual(start-33,2)
            self.assertEqual(depth-33-(start+length),2)
        with self.assertRaises(ValueError):support_dimensions(50)

    def test_hinge_zone_includes_two_millimetres_each_side(self):
        for x in (150,210,450):
            lo,hi=hinge_profile_interval(x)
            self.assertEqual(x-51-lo,2)
            self.assertEqual(hi-(x+51),2)

    def test_socket_is_seated_on_flange_not_bbox(self):
        for height in (350,430):
            origin=height-SOCKET_SEAT[2]
            self.assertAlmostEqual(origin-33.28911847247994,height)
            self.assertGreater(abs(height+30.20838152752+SOCKET_SEAT[2]-height),3)

    def test_polish_identifiers_are_unique_and_documented(self):
        names=[v[0] for v in PARAMETERS_PL.values()]
        self.assertEqual(len(names),len(set(names)))
        self.assertTrue(all(len(note)>60 for _,note in PARAMETERS_PL.values()))
