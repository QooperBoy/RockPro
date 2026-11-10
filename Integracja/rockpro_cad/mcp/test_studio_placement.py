import copy
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rockpro_cad import configurator as c
from rockpro_cad.mcp import project_store
from rockpro_cad.mcp.test_configurator import concept, three_piece


def handles(section='body', face='left'):
    return dict(id='carry',part_id='H7159',revision=1,section_id=section,face=face,
        u=.5,v=.5,rotation_deg=0,pattern='symmetric',count_per_wall=2,
        handles_per_wall=2,opposite_wall=True,spread=.5)


def placed():
    d=concept();d['hardware']=[dict(part_id='H7159',revision=1)]
    d['placements']=[handles()];return d


class StudioPlacementTests(unittest.TestCase):
    def test_four_handles_are_aligned_on_opposite_walls_and_resize_without_scaling(self):
        d=placed();before=copy.deepcopy(d)
        for size in ([600,500,350],[900,700,500]):
            d['internal_mm']=size;p=c.preview(d)['placement'];items=p['items']
            self.assertEqual(len(items),4);self.assertEqual({i['face'] for i in items},{'left','right'})
            self.assertEqual({tuple(i['footprint_mm']) for i in items},{(161.,107.)})
            left=sorted((i['position_mm'][1:]) for i in items if i['face']=='left')
            right=sorted((i['position_mm'][1:]) for i in items if i['face']=='right')
            for a,b in zip(left,right):
                for x,y in zip(a,b):self.assertAlmostEqual(x,y)
            self.assertFalse(p['warnings']);self.assertFalse(p['cutouts_generated'])
        self.assertEqual(d['placements'],before['placements'])

    def test_one_centered_handle_per_wall_and_individual_manual_pair(self):
        d=placed();g=d['placements'][0];g.update(count_per_wall=1,handles_per_wall=1,u=.2)
        p=c.preview(d)['placement'];self.assertEqual(len(p['items']),2)
        self.assertTrue(all(i['u']==.5 for i in p['items']))
        g.update(pattern='single',u=.3)
        p=c.preview(d)['placement'];a,b=p['items'];self.assertAlmostEqual(a['position_mm'][1],b['position_mm'][1])
        g['opposite_wall']=False;self.assertEqual(c.preview(d)['placement']['instance_count'],1)

    def test_more_handles_keep_explicit_count_and_uniform_positions(self):
        d=placed();d['placements'][0].update(count_per_wall=4,handles_per_wall=4)
        p=c.preview(d)['placement'];self.assertEqual(p['instance_count'],8)
        coordinates=sorted(i['position_mm'][1] for i in p['items'] if i['face']=='left')
        differences=[b-a for a,b in zip(coordinates,coordinates[1:])]
        self.assertAlmostEqual(min(differences),max(differences))
        for n in (0,17,True):
            d['placements'][0].update(count_per_wall=n,handles_per_wall=n)
            with self.subTest(n=n),self.assertRaises(ValueError):c.preview(d)

    def test_joint_hinges_follow_topology_spacing_resize_and_lid_halves(self):
        d=concept();d['hardware']=[dict(part_id='27095',revision=1)]
        g=dict(id='hinges',part_id='27095',revision=1,pattern='joint_line',joint_id='joint-lid-a',hinge_count=3,edge_inset_mm=80)
        d['placements']=[g]
        for size in ([600,500,350],[900,700,500]):
            d['internal_mm']=size;m=c.preview(d);p=m['placement'];items=p['items'];self.assertEqual(len(items),3)
            xs=[i['position_mm'][0] for i in items];self.assertAlmostEqual(xs[1]-xs[0],xs[2]-xs[1])
            self.assertAlmostEqual(xs[0],80);self.assertAlmostEqual(xs[-1],size[0]+19.6-80)
            self.assertTrue(all(i['face']=='rear' and i['position_mm'][2]==size[2]+19.6 for i in items))
            self.assertEqual({h['section_id'] for h in items[0]['visual_halves']},{'body','lid-a'})
            self.assertFalse(any(w['code']=='unbound_joint' for w in p['warnings']))
        d['covers'][0]['hinge_edge']='low';self.assertTrue(all(i['face']=='front' for i in c.preview(d)['placement']['items']))
        g['hinge_count']=1;self.assertAlmostEqual(c.preview(d)['placement']['items'][0]['position_mm'][0],(900+19.6)/2)
        d['covers'][0]['kind']='removable';self.assertEqual(c.preview(d)['placement']['unresolved_groups'],['hinges'])

    def test_cabinet_hinge_line_is_vertical_and_invalid_rows_are_refused(self):
        d=concept();d['type']='cabinet';d['covers'][0].update(face='front',depth_mm=80)
        d['hardware']=[dict(part_id='27095',revision=1)]
        g=dict(id='hinges',part_id='27095',revision=1,pattern='joint_line',joint_id='joint-lid-a',hinge_count=4,edge_inset_mm=60)
        d['placements']=[g];p=c.preview(d)['placement'];self.assertEqual(len(p['items']),4)
        self.assertTrue(all(i['face']=='right' and i['rotation_deg']==90 for i in p['items']))
        self.assertEqual(len({i['position_mm'][0] for i in p['items']}),1)
        d['covers'][0]['hinge_edge']='low';self.assertTrue(all(i['rotation_deg']==270 for i in c.preview(d)['placement']['items']))
        for patch in [dict(hinge_count=True),dict(hinge_count=17),dict(edge_inset_mm=float('nan')),dict(extra=True)]:
            before=dict(g);g.update(patch)
            with self.assertRaises(ValueError):c.preview(d)
            g.clear();g.update(before)
        g['edge_inset_mm']=1000;self.assertEqual(c.preview(d)['placement']['items'],[])

    def test_invalid_refs_counts_numbers_duplicates_and_extra_fields_are_refused(self):
        for change in [dict(count_per_wall=3),dict(handles_per_wall=True),dict(u=math.nan),dict(v=2),
                       dict(u=True),dict(rotation_deg=45),dict(revision=2),dict(part_id='27095'),
                       dict(part_id=[]),dict(opposite_wall=1),dict(extra='silent'),dict(id='')]:
            d=placed();d['placements'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):c.preview(d)
        d=placed();d['placements']*=2
        with self.assertRaises(ValueError):c.preview(d)

    def test_no_wall_is_invented_and_stale_section_is_preserved_for_retargeting(self):
        d=placed();d['placements'][0]['face']='top'
        p=c.preview(d)['placement'];self.assertEqual(p['items'],[]);self.assertEqual(p['unresolved_groups'],['carry'])
        d['placements'][0]['section_id']='old-lid';before=copy.deepcopy(d)
        self.assertEqual(c.preview(d)['placement']['items'],[]);self.assertEqual(d,before)
        d=three_piece();d['hardware']=[dict(part_id='H7159',revision=1)];d['placements']=[handles('front','front')]
        p=c.preview(d)['placement'];self.assertEqual(p['items'],[]) # Inner/open face cannot mount opposite handle.

    def test_lid_faces_are_section_bound_and_edge_overlap_unknown_are_reported(self):
        d=placed();d['placements'][0].update(section_id='lid-a',face='top',opposite_wall=False)
        m=c.preview(d);self.assertEqual(len(m['placement']['items']),2)
        self.assertTrue(all(i['position_mm'][2]==m['sections'][1]['position_mm'][2]+45 for i in m['placement']['items']))
        d['placements'][0].update(section_id='body',face='left',v=.01,spread=.05)
        p=c.preview(d)['placement'];self.assertTrue(any(w['code']=='edge_clearance' for w in p['warnings']));self.assertTrue(any(w['code']=='overlap' for w in p['warnings']))
        d['hardware'].append(dict(part_id='H2026',revision=1));g=copy.deepcopy(d['placements'][0]);g.update(id='unknown',part_id='H2026');d['placements'].append(g)
        self.assertTrue(any(w['code']=='unknown_envelope' for w in c.preview(d)['placement']['warnings']))
        self.assertFalse(c.preview(d)['cad_ready'])

    def test_revisioned_roundtrip_and_old_v3_remain_compatible(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(project_store,'DB_PATH',Path(temp)/'drafts.sqlite3'):
            d=placed();saved=c.save_draft(d);self.assertEqual(c.read_draft(saved['id'])['draft'],d)
            d['internal_mm'][0]=800;c.save_draft(d,saved['id'],saved['revision'])
            self.assertEqual(c.read_draft(saved['id'])['draft']['placements'][0]['handles_per_wall'],2)
        self.assertEqual(c.preview(concept())['placement']['items'],[])


if __name__=='__main__':unittest.main()
