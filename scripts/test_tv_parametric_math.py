"""Regression for feature/part frames; requires no customer file or CAD host."""
import unittest
from prepare_tv_parametric import compose_rotation, axis_growth

IDENTITY=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]

class FeatureFrameTests(unittest.TestCase):
    def test_rotated_insert_does_not_swap_height_and_depth(self):
        # Unequal deltas are deliberate: equal deltas conceal this error.
        feature=[0,-1,0,0,1,0,0,0,0,0,1,0,0,0,0,1]
        world=[0,0,1,0,0,-1,0,0,1,0,0,0,0,0,0,1]
        growth=[[120,0,0],[0,-20,0],[0,0,-30]]
        result=axis_growth(compose_rotation(feature,world),growth)
        self.assertEqual(result,[[0,-20,0],[0,0,-30],[120,0,0]])

    def test_feature_direction_defines_fixed_lower_end(self):
        feature=[0,-1,0,0,1,0,0,0,0,0,1,0,0,0,0,1]
        world=[0,0,1,0,0,-1,0,0,1,0,0,0,0,0,0,1]
        rotation=compose_rotation(feature,world)
        # Local feature X grows toward positive world Y. The part Y axis alone
        # points the other way and must not be used to shift this insert.
        self.assertEqual(rotation[1],1)
        self.assertEqual(world[5],-1)

    def test_identity_retains_three_independent_dimensions(self):
        growth=[[1,0,0],[0,2,0],[0,0,3]]
        self.assertEqual(axis_growth(compose_rotation(IDENTITY,IDENTITY),growth),growth)

if __name__=='__main__':unittest.main()
