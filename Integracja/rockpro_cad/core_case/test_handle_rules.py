import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.handle_rules import side_handle_rules
from rockpro_cad.core_case.profile_rules import value


class HandleRulesTests(unittest.TestCase):
    def test_four_handles_face_outward_on_opposite_walls_after_resize(self):
        for depth,length,base in ((500,650,300),(550,700,330)):
            v=dict(RP_Length=length,RP_Depth=depth,RP_BaseHeight=base)
            rows=side_handle_rules(v)
            self.assertEqual(len(rows),4)
            for r in rows:
                p=[value(s,v) for s in r['position']]
                self.assertEqual(p[0],0 if r['side']=='left' else length)
                self.assertIn(p[1],(depth/4,3*depth/4))
                self.assertEqual(p[2],base/2)
                # Asset outward +Y, up -Z. Both frames are proper rotations.
                self.assertEqual(r['rotation'][1],[-1,0,0] if r['side']=='left' else [1,0,0])
                self.assertEqual(r['rotation'][2],[0,0,-1])
                a,b,c=r['rotation']
                self.assertEqual(sum(a[i]*(b[(i+1)%3]*c[(i+2)%3]-b[(i+2)%3]*c[(i+1)%3]) for i in range(3)),1)
    def test_one_per_wall_is_centered_and_pair_does_not_silently_shrink(self):
        v=dict(RP_Length=650,RP_Depth=400,RP_BaseHeight=300)
        with self.assertRaises(ValueError):side_handle_rules(v,2)
        rows=side_handle_rules(v,1)
        self.assertEqual(len(rows),2)
        self.assertEqual([value(r['position'][1],v) for r in rows],[200,200])
        for invalid in (0,3,True,1.5):
            with self.assertRaises(ValueError):side_handle_rules(v,invalid)
