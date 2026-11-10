import copy
import unittest
from family_recommendation import recommend_case_families,benchmark_case_recommendations


def family(identity='small'):
    return dict(id=identity,name='Test family',device_ranges_mm=[[100,500],[100,400],[50,200]],
        count_range=[1,2],equipment=['wheels'],reference_device_mm=[440,339,136],reference_count=1,
        source_revision=dict(project_id='synthetic',revision_id='fixture-v1',sha256='a'*64),
        limitations=['Synthetic test fixture; no real historical acceptance'])


class FamilyRecommendationTests(unittest.TestCase):
    def setUp(self):self.query=dict(dimensions_mm=[440,339,136],device_count=1,equipment=['wheels'])
    def test_candidates_explain_bounds_and_do_not_select_or_approve(self):
        result=recommend_case_families(self.query,[family()])
        self.assertEqual(result['candidates'][0]['score'],0)
        self.assertEqual(len(result['candidates'][0]['reasons']),3)
        self.assertTrue(result['candidates'][0]['limitations'])
        self.assertFalse(result['automatic_selection']);self.assertFalse(result['production_approved'])
    def test_missing_family_or_capability_routes_to_manual_design(self):
        for query in [dict(self.query,dimensions_mm=[501,339,136]),dict(self.query,device_count=3),dict(self.query,equipment=['unknown'])]:
            result=recommend_case_families(query,[family()])
            self.assertEqual(result['status'],'manual_design_required');self.assertTrue(result['rejected'][0]['reasons'])
        self.assertEqual(recommend_case_families(self.query,[])['status'],'manual_design_required')
    def test_ranking_is_deterministic_and_does_not_modify_inputs(self):
        far=family('far');far['reference_device_mm']=[200,200,100]
        families=[far,family('near')];preserved=copy.deepcopy(families)
        self.assertEqual(recommend_case_families(self.query,families)['candidates'][0]['family_id'],'near')
        self.assertEqual(families,preserved)
    def test_unresolved_dimensions_and_duplicate_ids_refuse(self):
        with self.assertRaises(ValueError):recommend_case_families(dict(self.query,dimensions_mm=[None,339,136]),[family()])
        with self.assertRaises(ValueError):recommend_case_families(self.query,[family(),family()])
    def test_closed_labeled_benchmark_records_hits_and_misses(self):
        cases=[dict(id='match',query=self.query,expected_family_id='small',source_sha256='a'*64),
               dict(id='manual',query=dict(self.query,device_count=3),expected_family_id=None,source_sha256='b'*64),
               dict(id='wrong-label',query=self.query,expected_family_id=None,source_sha256='c'*64)]
        result=benchmark_case_recommendations([family()],cases)
        self.assertEqual(result['correct'],2);self.assertAlmostEqual(result['top1_accuracy'],2/3)
        self.assertTrue(result['labeling_is_caller_supplied'])
        with self.assertRaises(ValueError):benchmark_case_recommendations([family()],[])
