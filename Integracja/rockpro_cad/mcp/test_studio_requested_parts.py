import unittest
from rockpro_cad import configurator,studio_requested_parts as p,studio_review,studio_parts,company_catalog

class RequestedPartsTests(unittest.TestCase):
    def test_requested_quantities_and_pack(self):
        model=configurator.preview(p.draft());rows={r['part_id']:r for r in model['project_summary']['rows']}
        for key,quantity in [('H2026',4),(p.CORNER,8),(p.LATCH,4),(p.VENT,2),(p.FEET,8)]:
            self.assertEqual(rows[key]['quantity'],quantity)
        self.assertEqual(rows[p.FEET]['pack_size'],8)
        self.assertFalse(model['project_summary']['production_approved'])
        self.assertEqual(model['project_summary']['unplaced_selection'],[])
    def test_resizing_and_proper_corner_rotations(self):
        d=p.draft();first=configurator.preview(d);d['internal_mm']=[1000,750,1000];second=configurator.preview(d)
        self.assertNotEqual(first['construction']['items'],second['construction']['items'])
        for row in second['construction']['items']:
            a,b,c=row['rotation'];cross=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
            self.assertEqual(sum(x*y for x,y in zip(cross,c)),1)
            if row['part_id']==p.FEET:self.assertEqual(row['position_mm'][2],0)
    def test_concept_limits_are_not_hidden(self):
        report=studio_review.review(p.draft())
        self.assertEqual(report['counts']['error'],0)
        self.assertEqual(sum(r['code']=='concept_geometry' for r in report['issues']),5)
        self.assertFalse(report['production_approved'])
    def test_recipe_rejects_unknown_kit_and_wheels(self):
        for changes in [dict(kit='anything'),dict(wheels=True),dict(extra=True)]:
            d=p.draft();d['construction'].update(changes)
            with self.assertRaises(ValueError):configurator.preview(d)
    def test_top_profiles_stop_outside_latch_envelopes(self):
        model=configurator.preview(p.draft())
        locks=[r for r in model['placement']['items'] if r.get('seam_id')]
        profiles=[r for r in model['construction']['items'] if r['id'].startswith('edge/x/True')]
        self.assertEqual(len(profiles),6)
        for profile in profiles:
            x,y,z=profile['position_mm'];end=x+profile['rotation'][2][0]*profile['length_mm'];a,b=sorted([x,end])
            for lock in locks:
                if lock['position_mm'][1]!=y:continue
                c=lock['position_mm'][0];half=lock['footprint_mm'][0]/2
                self.assertTrue(b<=c-half-5+1e-6 or a>=c+half+5-1e-6)
    def test_catalog_does_not_duplicate_company_ids(self):
        catalog=company_catalog.picker_entries(studio_parts.catalog())
        ids=[r['id'] for r in catalog['items']]
        self.assertEqual(len(ids),len(set(ids)))

if __name__=='__main__':unittest.main()
