import json
from pathlib import Path
import tempfile
import unittest

from prepare_catalog_questions import build_report, generate, render_html


def manifest():
    def item(identifier, status):
        return dict(id=identifier, code="WSPÓLNY KOD", name="Nazwa <script>",
            manufacturer=None, status=status, source_url="javascript:alert(1)",
            asset_files=["PRIVATE/part.step"], price=999, stock=888)
    return dict(schema="rockpro.company-cad-assets/1", assets=[
        dict(file="PRIVATE/part.step", configuration="OTHER-K", price=123)], items=[
        item("a", "supplier_or_model_not_identified"),
        item("b", "other_supplier_requires_lookup"),
        item("c", "downloaded_candidate_catalog_code_conflict"),
        item("d", "configuration_needs_review"),
        item("e", "downloaded_candidate"),
        item("f", "no_public_3d_link_found")])


class CatalogQuestionChecks(unittest.TestCase):
    def test_only_actionable_groups_keep_distinct_ids_and_variant(self):
        report = build_report(manifest(), "sha", "2026-10-31")
        self.assertEqual(report['counts'], dict(identification=2, variants=2))
        self.assertEqual([x['id'] for x in report['groups']['identification']], ['a', 'b'])
        self.assertEqual(report['groups']['variants'][0]['candidate_configurations'], ['OTHER-K'])
        self.assertTrue(all(x['decision'] == 'DO POTWIERDZENIA'
            for group in report['groups'].values() for x in group))

    def test_no_financial_or_internal_paths_exported(self):
        raw = json.dumps(build_report(manifest(), "sha", "2026-10-31"))
        for secret in ('PRIVATE/', '999', '888', '"price"', '"stock"'):
            self.assertNotIn(secret, raw)

    def test_html_escapes_fields_and_rejects_active_url(self):
        html = render_html(build_report(manifest(), "sha", "2026-10-31"))
        self.assertNotIn('<script>', html)
        self.assertNotIn('javascript:', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertEqual(html.count('data-record-id='), 4)

    def test_duplicate_ids_rejected(self):
        data = manifest()
        data['items'][1]['id'] = 'a'
        with self.assertRaises(ValueError):
            build_report(data, "sha", "2026-10-31")

    def test_schema_rejected(self):
        with self.assertRaises(ValueError):
            build_report(dict(schema="different"), "sha", "2026-10-31")

    def test_preserves_source_and_refuses_existing_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root/'source.json', root/'out'
            before = json.dumps(manifest(), ensure_ascii=False).encode('utf-8')
            source.write_bytes(before)
            generate(source, output, '2026-10-31')
            self.assertEqual(source.read_bytes(), before)
            first = (output/'PYTANIA_DO_TOMKA.html').read_bytes()
            with self.assertRaises(FileExistsError):
                generate(source, output, '2026-10-31')
            self.assertEqual((output/'PYTANIA_DO_TOMKA.html').read_bytes(), first)


if __name__ == '__main__':
    unittest.main()
