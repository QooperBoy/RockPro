"""Series persistence safety and cross-size concept checks, using an isolated DB."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import prepare_studio_review_series as series
from rockpro_cad import configurator
from rockpro_cad.mcp import project_store


class ReviewSeriesTests(unittest.TestCase):
    def test_examples_and_parametric_sections(self):
        rows=list(series.examples())
        self.assertEqual(len(rows),8)
        self.assertEqual({d['type'] for _,d in rows},{'case','cabinet','three_piece'})
        for slug,d in rows:
            with self.subTest(example=slug):
                p=configurator.preview(d)
                self.assertFalse(p['cad_ready'])
                self.assertEqual(p['placement']['unresolved_groups'],[])
                self.assertEqual({w['code'] for w in p['placement']['warnings']},{'closure_reference'})
                self.assertEqual(series.native_spec(d)['formula_check'],'PASS')
                if d['type']=='three_piece':
                    sections={s['id']:s for s in p['sections']}
                    self.assertAlmostEqual(sections['front']['size_mm'][2],
                        sections['top']['position_mm'][2]+sections['top']['size_mm'][2])

    def test_repeat_does_not_duplicate_or_overwrite_user_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(project_store,'DB_PATH',root/'isolated.sqlite3'):
                initial=series.prepare(root/'series')
                repeated=series.prepare(root/'series')
                self.assertEqual(initial,repeated)
                self.assertEqual(len(configurator.list_drafts()),8)
                owned=configurator.read_draft(initial[0]['id'])
                owned['draft']['internal_mm'][0]+=1
                modified=configurator.save_draft(owned['draft'],owned['id'],owned['revision'])
                with self.assertRaisesRegex(ValueError,'ownership changed'):
                    series.prepare(root/'series')
                self.assertEqual(configurator.read_draft(owned['id']),modified)


if __name__=='__main__':
    unittest.main()
