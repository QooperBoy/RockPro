"""Independent hinge/ground-plane/slot equations using synthetic datums."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.transport_rules import make_rules,validate_transport_values
from rockpro_cad.core_case.profile_rules import value

def fixture():
    hinge=dict(export_signature=[dict(bounds_m=[-.068317,-.0207,-.1,.058683,-.0017,.0031])])
    return dict(hinge_base=copy.deepcopy(hinge),hinge_lid=copy.deepcopy(hinge),
        wheel=dict(rubber_cylinder=dict(radius_m=.05,axis=[0,0,1]),contact_point_m=[-.036,-.1321,0]),
        socket=dict(mount_point_m=[0,.05821,-.033289],mount_face=dict(reversed=True,normal=[0,0,1])))

class TransportRulesTests(unittest.TestCase):
    def setUp(self):
        self.v=dict(RP_Length=2000,RP_Depth=3000,RP_BaseHeight=3600,RP_LidHeight=400,
            RP_Thickness=9.8,RP_DisplayGap=0,RP_JointGap=8.63)
        self.rules=make_rules(fixture())
    def point(self,row,v):return [value(s,v) for s in row['anchor']]
    def test_hinge_halves_share_joint_and_explode_only_with_lid(self):
        by={r['id']:r for r in self.rules}
        for v in (self.v,dict(self.v,RP_Length=2200,RP_Depth=3200,RP_BaseHeight=3700,RP_JointGap=10,RP_DisplayGap=80)):
            validate_transport_values(v)
            for side in ('left','right'):
                lo=self.point(by['hinge/'+side+'/base'],v);hi=self.point(by['hinge/'+side+'/lid'],v)
                self.assertEqual(lo[:2],hi[:2]);self.assertAlmostEqual(hi[2]-lo[2],v['RP_DisplayGap'])
    def test_four_ground_contacts_align_socket_xy_and_share_ground(self):
        rows={r['id']:r for r in self.rules}
        contacts=[]
        for r in self.rules:
            if r['kind']!='wheel':continue
            p=self.point(r,self.v);R=r['rotation'];c=r['contact_local_mm']
            world=[p[j]+sum(c[k]*R[k][j] for k in range(3)) for j in range(3)]
            socket=self.point(rows['socket/'+r['pair']],self.v)
            self.assertEqual(world[:2],socket[:2]);self.assertAlmostEqual(world[2],-150.1)
            self.assertEqual(socket[2],4000);contacts.append(world)
        self.assertEqual(len(contacts),4)
        self.assertEqual(sorted({p[0] for p in contacts}),[186,1814])
        self.assertEqual(sorted({p[1] for p in contacts}),[100,2900])
    def test_reject_wrong_wheel_or_flange_sign_and_small_case(self):
        c=fixture();c['wheel']['rubber_cylinder']['radius_m']=.06
        with self.assertRaises(ValueError):make_rules(c)
        c=fixture();c['socket']['mount_face']['reversed']=False
        with self.assertRaises(ValueError):make_rules(c)
        with self.assertRaises(ValueError):validate_transport_values(dict(self.v,RP_Length=400))

if __name__=='__main__':unittest.main()
