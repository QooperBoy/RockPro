"""Offline solid-box checks for the pinned T1 panel layout (not a CAD receipt)."""
import copy
import itertools
import unittest

from rockpro_cad import configurator
from rockpro_cad.mcp.test_configurator import concept, three_piece
from rockpro_cad.mcp.test_studio_structure import complete


def bounds(panel):
    return ([panel['center_mm'][k]-panel['size_mm'][k]/2 for k in range(3)],
            [panel['center_mm'][k]+panel['size_mm'][k]/2 for k in range(3)])


class T1PanelGeometryTests(unittest.TestCase):
    def test_panel_volumes_do_not_overlap_and_envelope_does_not_grow(self):
        for interior, lid in [([600,500,800],115),([380,380,160],110),([900,650,900],125)]:
            with self.subTest(interior=interior):
                draft=complete();draft['internal_mm']=interior
                draft['covers'][0].update(depth_mm=lid,height_override=True)
                # This test isolates panel joinery at its smallest envelope.
                # Transport/cup clearances have separate, stricter tests.
                draft['construction'].update(wheels=False,stacking=False)
                draft['hardware']=[h for h in draft['hardware'] if h['part_id'] not in ('source-caster-epson','W0968Z')]
                original=copy.deepcopy(draft);p=configurator.preview(draft)
                self.assertEqual(draft,original)
                self.assertEqual(len(p['panels']),10)
                for a,b in itertools.combinations(p['panels'],2):
                    alo,ahi=bounds(a);blo,bhi=bounds(b)
                    overlap=[min(ahi[k],bhi[k])-max(alo[k],blo[k]) for k in range(3)]
                    self.assertFalse(all(x>1e-8 for x in overlap),(a,b,overlap))
                actual_min=[min(bounds(x)[0][k] for x in p['panels']) for k in range(3)]
                actual_max=[max(bounds(x)[1][k] for x in p['panels']) for k in range(3)]
                expected=[interior[0]+19.6,interior[1]+19.6,interior[2]+9.8+lid]
                for actual,expect in zip(actual_min+actual_max,[0,0,0]+expected):
                    self.assertAlmostEqual(actual,expect)
                self.assertFalse(p['cad_ready'])

    def test_actual_body_clearance_and_lid_joint_are_measured_from_panels(self):
        draft=complete();p=configurator.preview(draft);body,lid=p['sections']
        left,right,front,rear,floor=p['panels'][:5]
        self.assertAlmostEqual(bounds(right)[0][0]-bounds(left)[1][0],draft['internal_mm'][0])
        self.assertAlmostEqual(bounds(rear)[0][1]-bounds(front)[1][1],draft['internal_mm'][1])
        body_rim=min(bounds(x)[1][2] for x in (left,right,front,rear))
        self.assertAlmostEqual(body_rim-bounds(floor)[1][2],draft['internal_mm'][2])
        self.assertAlmostEqual(body_rim,body['size_mm'][2])
        self.assertAlmostEqual(lid['position_mm'][2],body_rim)
        for panel in p['panels'][5:9]:
            self.assertAlmostEqual(bounds(panel)[0][2]-body_rim,8.63)
            self.assertAlmostEqual(bounds(panel)[1][2],bounds(p['panels'][9])[0][2])
        self.assertEqual(p['joints'][0]['gap_mm'],8.63)
        self.assertEqual(p['joints'][0]['plywood_trim_mm'],8.63)
        self.assertEqual(p['panel_dimensions_status'],'t1_reference_layout_not_cutting')

    def test_corrected_rim_reaches_closures_handles_and_transport(self):
        draft=complete();p=configurator.preview(draft)
        rim=draft['internal_mm'][2]+draft['thickness_mm']
        for item in p['placement']['items']:
            if item.get('seam_id'):
                self.assertAlmostEqual(item['position_mm'][2],rim)
            elif item['part_id']=='H7159':
                self.assertAlmostEqual(item['position_mm'][2],rim/2)
        self.assertEqual(len(p['placement']['faces']),10)
        self.assertEqual({f['panel_index'] for f in p['placement']['faces']},set(range(10)))
        self.assertEqual(p['placement']['unresolved_groups'],[])
        for item in p['construction']['items']:
            if item['family_id']=='stacking_sockets':
                self.assertAlmostEqual(item['seat_world_mm'][2],rim+draft['covers'][0]['depth_mm'])

    def test_scope_keeps_other_families_thicknesses_and_disabled_layout_nominal(self):
        disabled=complete();disabled['construction']['enabled']=False
        removable=complete();removable['covers'][0]['kind']='removable'
        thick=complete();thick['thickness_mm']=12
        cabinet=concept();cabinet['type']='cabinet';cabinet['covers'][0]['face']='front'
        for draft in (disabled,removable,thick,cabinet,three_piece(),concept()):
            with self.subTest(kind=draft['type'],construction=draft.get('construction')):
                p=configurator.preview(draft)
                self.assertEqual(p['panel_dimensions_status'],'nominal_not_cutting')
                self.assertAlmostEqual(p['sections'][0]['size_mm'][2],draft['internal_mm'][2]+2*draft['thickness_mm'])
                self.assertTrue(all(j['gap_mm'] is None for j in p['joints']))


if __name__=='__main__':
    unittest.main()
