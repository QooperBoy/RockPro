import copy
import unittest
from rockpro_cad import studio_examples,studio_review


class StudioReviewTests(unittest.TestCase):
    def setUp(self):self.d=copy.deepcopy(studio_examples.catalog()['items'][0]['draft'])
    def test_complete_concepts_are_not_claimed_production_approved(self):
        for example in studio_examples.catalog()['items']:
            r=studio_review.review(example['draft'])
            self.assertEqual(r['counts']['error'],0);self.assertEqual(r['counts']['warning'],0)
            self.assertFalse(r['production_approved']);self.assertEqual(r['issues'][0]['code'],'native_check_pending')
    def test_skipped_work_is_detected_from_content(self):
        self.d['hardware']=[];self.d['placements']=[];self.d.pop('construction')
        r=studio_review.review(self.d);codes={i['code'] for i in r['issues']}
        self.assertTrue({'missing_parts','missing_handles','missing_hinge','missing_latch','missing_construction'}<=codes)
        self.assertEqual({s['step'] for s in r['steps'] if s['status']=='attention'},{4,5,6,7})
    def test_overlap_has_both_group_targets_and_correct_step(self):
        g=copy.deepcopy(self.d['placements'][0]);g['id']='overlapping-handles';self.d['placements'].append(g)
        r=studio_review.review(self.d);issues=[i for i in r['issues'] if i['code']=='overlap']
        self.assertTrue(issues);self.assertTrue(all(i['severity']=='error' and i['step']==5 and i['other_group_id'] for i in issues))
    def test_edge_and_impossible_closure_rows(self):
        self.d['placements'][0]['v']=0;self.d['placements'][1]['count']=16
        r=studio_review.review(self.d);by={i['code']:i for i in r['issues']}
        self.assertEqual(by['edge_clearance']['step'],5);self.assertEqual(by['closure_no_space']['step'],6)
    def test_invalid_dimensions_unknown_revision_and_malformed_input(self):
        self.d['internal_mm'][0]=None;r=studio_review.review(self.d)
        self.assertFalse(r['data_valid']);self.assertEqual(r['issues'][0]['step'],3)
        self.d['internal_mm'][0]=600;self.d['hardware'][0]['revision']=999
        self.assertEqual(studio_review.review(self.d)['issues'][0]['step'],4)
        for bad in (None,[],{'type':{}},True):self.assertFalse(studio_review.review(bad)['data_valid'])
    def test_unplaced_selection_is_not_a_finished_stage(self):
        self.d['hardware'].append(dict(part_id='H2026',revision=1))
        r=studio_review.review(self.d)
        issue=next(i for i in r['issues'] if i['code']=='part_not_placed')
        self.assertEqual(issue['part_id'],'H2026');self.assertEqual(issue['step'],5)
    def test_legacy_wall_latch_goes_to_its_actual_editor(self):
        g=copy.deepcopy(self.d['placements'][0]);g.update(id='wall-latch',part_id='17251S',pattern='single',face='front',count_per_wall=1,opposite_wall=False,v=0);g.pop('handles_per_wall')
        self.d['placements'].append(g)
        issues=[i for i in studio_review.review(self.d)['issues'] if i.get('group_id')=='wall-latch']
        self.assertTrue(issues);self.assertTrue(all(i['step']==5 for i in issues))


if __name__=='__main__':unittest.main()
