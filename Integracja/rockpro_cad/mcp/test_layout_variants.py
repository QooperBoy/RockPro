import copy
import unittest
from layout_variants import preview_device_layouts
from test_device_catalog import fixture


class DeviceLayoutVariantTests(unittest.TestCase):
    def setUp(self):self.spec=dict(count=1,clearance=20,lid_height=25,lid_hinge_height=0,lid_constructor_override=False)
    def preview(self,record=None,spec=None,orientations=None,arrangements=None,**kwargs):
        return preview_device_layouts(record or fixture(),spec or self.spec,orientations or ['XYZ','YXZ','XZY','YZX','ZXY','ZYX'],arrangements or ['X','Y','Z'],**kwargs)
    def test_no_more_than_three_distinct_allowed_geometries(self):
        record=fixture();preserved=copy.deepcopy(record)
        result=self.preview(record)
        self.assertLessEqual(len(result['variants']),3)
        self.assertGreater(len(result['variants']),0)
        self.assertEqual(record,preserved)
        for row in result['variants']:
            self.assertFalse(row['layout']['checks']['collisions']);self.assertTrue(row['removal_check']['passed'])
            self.assertFalse(row['production_approved'])
        single=self.preview(orientations=['XYZ'],arrangements=['X'])
        self.assertEqual(len(single['variants']),1)
    def test_disallowed_orientation_or_external_limit_is_not_silently_relaxed(self):
        result=self.preview(orientations=['XYZ'],arrangements=['X'],max_external_mm=[100,100,100])
        self.assertEqual(result['status'],'manual_design_required');self.assertTrue(result['rejected'])
        with self.assertRaises(ValueError):preview_device_layouts(fixture(),self.spec,['XXZ'],['X'])
    def test_stacked_devices_and_insufficient_hand_space_block_removal(self):
        result=self.preview(spec=dict(self.spec,count=2),orientations=['XYZ'],arrangements=['Z'])
        self.assertFalse(result['variants']);self.assertIn('tor wyjęcia',result['rejected'][0]['reason'])
        result=self.preview(orientations=['XYZ'],arrangements=['X'],removal_clearance_mm=25)
        self.assertFalse(result['variants']);self.assertIn('luzu chwytu',result['rejected'][0]['reason'])
    def test_missing_conflicting_or_unconfirmed_dimensions_cannot_release(self):
        record=fixture();record['observations'][0]['confirmation']='unconfirmed'
        result=self.preview(record)
        self.assertIn('DEVICE_DIMENSIONS_UNCONFIRMED',result['release_blockers'])
        self.assertFalse(result['variants'][0]['production_approved'])
        record['observations'].pop(0)
        result=self.preview(record)
        self.assertEqual(result['status'],'blocked');self.assertFalse(result['variants'])
    def test_source_change_changes_proposal_identity_without_automatic_save(self):
        first=self.preview(orientations=['XYZ'],arrangements=['X'])
        record=fixture();record['observations'][0]['value']=450
        second=self.preview(record,orientations=['XYZ'],arrangements=['X'])
        self.assertNotEqual(first['variants'][0]['id'],second['variants'][0]['id'])
        self.assertTrue(second['constructor_can_edit_or_reject']);self.assertFalse(second['automatic_save'])
