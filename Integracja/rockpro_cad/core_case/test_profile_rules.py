"""Independent edge, symmetry and fixed-section policy checks; no CAD imports."""
from collections import Counter
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.profile_rules import rules,value,validate_values

class ProfileRulesTests(unittest.TestCase):
    def setUp(self):
        self.v=dict(RP_Length=2000.,RP_Depth=3000.,RP_BaseHeight=3600.,RP_LidHeight=400.,
                    RP_Thickness=9.8,RP_DisplayGap=0.,RP_JointGap=8.63)
        self.rows=rules()
    def test_complete_groups_have_proper_orthonormal_frames(self):
        self.assertEqual(Counter(r['sku'] for r in self.rows),{'EG-0113':16,'EG-0500_1':4,'EG-0500_2':4,'B1930':4,'B1121':4})
        self.assertEqual(len({r['id'] for r in self.rows}),32)
        for row in self.rows:
            R=row['rotation']
            for i in range(3):
                for j in range(3):self.assertEqual(sum(R[i][k]*R[j][k] for k in range(3)),int(i==j))
            det=sum(R[0][i]*(R[1][(i+1)%3]*R[2][(i+2)%3]-R[1][(i+2)%3]*R[2][(i+1)%3]) for i in range(3))
            self.assertEqual(det,1)
    def test_vertical_runs_leave_thirty_mm_at_each_end(self):
        for half,start,end in [('base',0,3600),('lid',3608.63,4000)]:
            row=next(r for r in self.rows if r['id']==half+'/front-left')
            z=value(row['center'][2],self.v);length=value(row['cut_length'],self.v)
            self.assertAlmostEqual(z-length/2,start+30)
            self.assertAlmostEqual(z+length/2,end-30)
    def test_edge_pairs_remain_centered_after_resize_and_return(self):
        for v in [self.v,dict(self.v,RP_Length=2200,RP_Depth=3200,RP_BaseHeight=3700,RP_LidHeight=450,RP_DisplayGap=80,RP_JointGap=10),self.v]:
            validate_values(v)
            centers={r['id']:[value(s,v) for s in r['center']] for r in self.rows}
            for group in ('top','bottom','base','lid','EG-0500_1','EG-0500_2'):
                suffixes=('front-left','front-right') if group in ('base','lid') else ('left','right')
                a,b=[centers[group+'/'+s] for s in suffixes]
                self.assertAlmostEqual(a[0]+b[0],v['RP_Length'])
                self.assertAlmostEqual(a[1],b[1]);self.assertAlmostEqual(a[2],b[2])
    def test_braces_are_rigid_and_unsafe_dimensions_or_expressions_refuse(self):
        for r in self.rows:
            self.assertEqual(r['cut_length'] is None,r['sku'] in ('B1930','B1121'))
        for delta in (dict(RP_LidHeight=40),dict(RP_Thickness=50),dict(RP_Length=float('nan'))):
            with self.assertRaises(ValueError):validate_values(dict(self.v,**delta))
        with self.assertRaises(ValueError):value('__import__("os")',self.v)

if __name__=='__main__':unittest.main()
