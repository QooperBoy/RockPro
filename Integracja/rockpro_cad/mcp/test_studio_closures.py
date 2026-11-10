import copy
import unittest
from rockpro_cad import configurator as c, studio_closures
from rockpro_cad.mcp.test_configurator import concept,three_piece
from rockpro_cad.mcp.test_studio_placement import handles


def row(part='17251S',seam='seam-lid-a-front',count=3):
    return dict(id='closures',part_id=part,revision=1,pattern='closure_line',seam_id=seam,count=count,edge_inset_mm=90,clearance_mm=5,avoid_handles=True)

class ClosureTests(unittest.TestCase):
    def draft(self):
        d=concept();d['hardware']=[dict(part_id=p,revision=1) for p in ['H7159','17251S','27095']];d['placements']=[row()];return d

    def test_seams_roles_removable_cabinet_and_resize(self):
        d=self.draft()
        for size in ([600,500,350],[900,650,500]):
            d['internal_mm']=size;p=c.preview(d)['placement'];items=p['items'];self.assertEqual(len(items),3)
            coords=[i['distance_along_joint_mm'] for i in items];self.assertAlmostEqual(coords[1]-coords[0],coords[2]-coords[1])
            self.assertEqual(len({i['position_mm'][2] for i in items}),1);self.assertTrue(all(i['visual_halves'][1]['section_id']=='lid-a' for i in items))
        d['covers'][0]['hinge_edge']='low';self.assertEqual(c.preview(d)['placement']['items'],[]) # latch row cannot take hinge edge
        d['covers'][0]['kind']='removable';self.assertEqual(len(c.preview(d)['placement']['closure_lines']),4)
        d['placements']=[row('27095','seam-lid-a-front')];self.assertEqual(c.preview(d)['placement']['items'],[])
        d['type']='cabinet';d['covers'][0].update(face='front',kind='hinged',depth_mm=80,hinge_edge='high');d['placements']=[row('27095','seam-lid-a-right',2)]
        p=c.preview(d)['placement'];self.assertEqual(len(p['items']),2);self.assertEqual(len({i['position_mm'][0] for i in p['items']}),1)
        d=three_piece();p=c.preview(d)['placement'];self.assertTrue(p['closure_lines']);self.assertTrue(all(l['roles']==['latches'] for l in p['closure_lines']))

    def test_uniform_solver_avoids_handles_and_does_not_hide_impossible_layout(self):
        self.assertEqual(studio_closures.uniform_positions(600,3,80,100,[]),[80,300,520])
        positions=studio_closures.uniform_positions(600,3,80,100,[(260,340)])
        self.assertIsNotNone(positions);self.assertAlmostEqual(positions[1]-positions[0],positions[2]-positions[1]);self.assertTrue(all(not 260<=p<=340 for p in positions))
        self.assertIsNone(studio_closures.uniform_positions(200,3,80,100,[]))
        d=self.draft();g=handles(face='front');g.update(opposite_wall=False,count_per_wall=1,handles_per_wall=1,v=.9)
        d['placements']=[g,row(count=1)];p=c.preview(d)['placement'];item=next(i for i in p['items'] if i.get('seam_id'));self.assertGreater(abs(item['u']-.5)*619.6,(161+127)/2+5)
        self.assertNotEqual(item['position_mm'][0],619.6/2)
        d['placements'][1]['avoid_handles']=False;self.assertTrue(any(w['code']=='closure_handle_overlap' for w in c.preview(d)['placement']['warnings']))
        d['placements'][1].update(count=16,avoid_handles=True);p=c.preview(d)['placement'];self.assertIn('closures',p['unresolved_groups']);self.assertFalse(any(i.get('seam_id') for i in p['items']))
        self.assertEqual(d['internal_mm'],[600,500,350])

    def test_solver_event_search_preserves_reserve_for_many_counts(self):
        for count in range(1,17):
            for forbidden in ([],[(200,201)],[(70,190),(440,540)],[(0,1000)]):
                positions=studio_closures.uniform_positions(1000,count,50,40,forbidden)
                if positions is None:continue
                self.assertEqual(len(positions),count)
                self.assertTrue(all(50-1e-8<=p<=950+1e-8 for p in positions))
                self.assertTrue(all(not a<=p<=b for p in positions for a,b in forbidden))
                if count>1:
                    pitch=positions[1]-positions[0];self.assertGreaterEqual(pitch,40-1e-8)
                    self.assertTrue(all(abs((b-a)-pitch)<1e-7 for a,b in zip(positions,positions[1:])))

    def test_bad_counts_refs_finite_values_and_component_pair_are_strict(self):
        for patch in [dict(count=True),dict(count=17),dict(clearance_mm=float('nan')),dict(avoid_handles=1),dict(extra=True),dict(revision=7)]:
            d=self.draft();d['placements'][0].update(patch)
            with self.subTest(patch=patch),self.assertRaises(ValueError):c.preview(d)
        d=self.draft();d['placements'][0]['seam_id']='deleted';self.assertEqual(c.preview(d)['placement']['unresolved_groups'],['closures'])
        # Synthetic source components exercise explicit two-reference validation without customer assets.
        chosen={'a':dict(id='a',revision=1,family_id='hinges',component_only=True),'b':dict(id='b',revision=2,family_id='hinges',component_only=True)}
        g=row('a');g.update(mate_part_id='b',mate_revision=2);self.assertEqual(studio_closures.validate(g,chosen,set()),6)
        g['mate_part_id']='a'
        with self.assertRaises(ValueError):studio_closures.validate(g,chosen,set())

if __name__=='__main__':unittest.main()
