import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from rockpro_cad import configurator as c
from rockpro_cad.studio_structure import REQUIRED
from rockpro_cad.mcp import project_store
from rockpro_cad.mcp.test_configurator import concept
from rockpro_cad.mcp.test_studio_closures import row
from rockpro_cad.mcp.test_studio_placement import handles


def complete():
    d=concept();d['internal_mm']=[600,500,800];d['covers'][0]['depth_mm']=115
    d['construction']=dict(enabled=True,wheels=True,stacking=True)
    d['hardware']=[dict(part_id=p,revision=1) for p in REQUIRED+['source-caster-epson','W0968Z','H7159','17251S','270836']]
    d['placements']=[handles(),row(count=2),dict(row('270836','seam-lid-a-rear',2),id='hinges')]
    return d


class StructureTests(unittest.TestCase):
    def test_full_families_and_proper_rotations(self):
        p=c.preview(complete());items=p['construction']['items']
        self.assertEqual(len({x['id'] for x in items}),len(items))
        self.assertEqual(p['construction']['counts']['410429'],8)
        self.assertEqual(p['construction']['counts']['EG-0113'],16)
        self.assertEqual(p['project_summary']['total_count'],76)
        self.assertEqual(p['project_summary']['unplaced_selection'],[])
        self.assertFalse(p['project_summary']['purchase_bom_ready'])
        self.assertEqual({x['family_id'] for x in items},
            {'profiles','corners','braces','wheels','wheel_pads','stacking_sockets'})
        for x in items:
            a,b,z=x['rotation'];cross=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
            self.assertEqual(sum(u*v for u,v in zip(cross,z)),1,x['id'])

    def test_wheels_sockets_and_supports_follow_dimensions(self):
        for size in [[600,500,800],[900,650,900],[380,380,800]]:
            d=complete();d['internal_mm']=size;p=c.preview(d);rows=p['construction']['items']
            wheels={x['stacking_pair']:x for x in rows if x['family_id']=='wheels'}
            height=sum(s['size_mm'][2] for s in p['sections'])
            for socket in [x for x in rows if x['family_id']=='stacking_sockets']:
                wheel=wheels[socket['stacking_pair']]
                self.assertEqual(socket['seat_world_mm'][:2],wheel['position_mm'][:2])
                self.assertAlmostEqual(socket['seat_world_mm'][2],height)
                self.assertEqual(socket['stage_id'],'wheels')
            for pad in [x for x in rows if x['family_id']=='wheel_pads']:
                self.assertGreaterEqual(pad['position_mm'][1],35)
                self.assertLessEqual(pad['position_mm'][1]+pad['size_mm'][1],p['sections'][0]['size_mm'][1]-35)

    def test_profile_interruptions_follow_closures(self):
        d=complete();p=c.preview(d)
        for closure in p['placement']['items']:
            if not closure.get('seam_id'):continue
            center=closure['position_mm'][0];half=closure['footprint_mm'][0]/2+5
            for x in p['construction']['items']:
                if not x['id'].startswith('joint/') or '/'+closure['face']+'/' not in x['id']:continue
                a=x['position_mm'][0];b=a+x['length_mm']
                self.assertTrue(b<=center-half+.001 or a>=center+half-.001)
        moved=copy.deepcopy(d);moved['placements'][1]['edge_inset_mm']=150
        self.assertNotEqual(c.preview(moved)['construction'],p['construction'])

    def test_invalid_requests_and_legacy_are_not_silently_changed(self):
        d=complete()
        for change in [dict(wheels=False,stacking=True,enabled=True),dict(enabled=1,wheels=True,stacking=True)]:
            bad=copy.deepcopy(d);bad['construction']=change
            with self.assertRaises(ValueError):c.preview(bad)
        bad=copy.deepcopy(d);bad['hardware']=[x for x in bad['hardware'] if x['part_id']!='410429']
        with self.assertRaises(ValueError):c.preview(bad)
        bad=copy.deepcopy(d);bad['covers'][0]['depth_mm']=45
        with self.assertRaises(ValueError):c.preview(bad)
        legacy=concept();self.assertEqual(c.preview(legacy)['construction']['items'],[])
        self.assertNotIn('construction',legacy)

    def test_save_reopen_preserves_complete_recipe(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(project_store,'DB_PATH',Path(temp)/'test.sqlite3'):
            saved=c.save_draft(complete());read=c.read_draft(saved['id'])
            self.assertEqual(read,saved)
            self.assertEqual(c.preview(saved['draft']),c.preview(read['draft']))


if __name__=='__main__':unittest.main()
