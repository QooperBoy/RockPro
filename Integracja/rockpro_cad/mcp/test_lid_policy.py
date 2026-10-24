import unittest
from lid_policy import minimum_lid_height,validate_lid_height,choose_lid_height,PLYWOOD_COLORREF
from layout import calculate_layout

class LidPolicyTests(unittest.TestCase):
    def test_hinge_height_not_three_times_socket_width(self):
        self.assertEqual(minimum_lid_height([30,40]),40)
        self.assertEqual(choose_lid_height(300,[30]),36)
        self.assertEqual(validate_lid_height(45,[40],300),40)
        with self.assertRaises(ValueError):validate_lid_height(39,[40],300)
    def test_conflict_requires_explicit_constructor_exception(self):
        with self.assertRaises(ValueError):choose_lid_height(300,[80])
        with self.assertRaises(ValueError):validate_lid_height(81,[80],300)
        self.assertEqual(validate_lid_height(81,[80],300,True),80)
        with self.assertRaises(ValueError):validate_lid_height(79,[80],300,True)
        for h in (None,True,0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):minimum_lid_height([h])
    def test_layout_preserves_base_space_and_checks_proportion(self):
        r=calculate_layout(dict(x=100,y=200,z=300,count=1,lid_hinge_height=30,lid_height=40))
        self.assertEqual(r['parameters']['RP_LidHeight'],40)
        self.assertGreaterEqual(r['parameters']['RP_BaseHeight'],349)
        with self.assertRaises(ValueError):calculate_layout(dict(z=300,count=1,lid_hinge_height=30,lid_height=80))
        r=calculate_layout(dict(z=300,count=1,lid_hinge_height=80,lid_height=81,lid_constructor_override=True))
        self.assertTrue(r['lid_policy']['constructor_override'])
    def test_legacy_geometry_and_green_are_preserved(self):
        r=calculate_layout(dict(x=100,y=200,z=300,count=1,clearance=10,thickness=9,lid_height=50))
        self.assertEqual(r['external'],[138,238,338])
        self.assertNotIn('lid_hinge_height',r['spec'])
        self.assertEqual(PLYWOOD_COLORREF,64+(128<<8)+(128<<16))

if __name__=='__main__':unittest.main()
