"""Configured Studio planning integration, synthetic sources only; no CAD worker."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rockpro_cad import configurator, studio_cad, studio_native, studio_parts, studio_placement
from rockpro_cad.mcp import project_store
from rockpro_cad.mcp.test_studio_native_t1 import manifest
from rockpro_cad.mcp.test_studio_structure import complete


class StudioNativeIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='rockpro-studio-native-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for patcher in (
            patch.object(project_store, 'DB_PATH', self.root / 'isolated.sqlite3'),
            patch.object(studio_native, '_configured', None),
            patch.dict(studio_placement.FOOTPRINTS, {'270836': [127., 174.5]}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        worker = patch.object(studio_native.subprocess, 'run',
                              side_effect=AssertionError('Native worker forbidden in offline integration tests'))
        self.worker = worker.start()
        self.addCleanup(worker.stop)
        assets = manifest()
        assets['schema'] = 'rockpro.roc46.asset-discovery/1'
        self.sources = {}
        for key in assets['sources']:
            source = self.root / ('private-source-' + key + '.ics')
            source.write_bytes(('Synthetic CAD placeholder: ' + key).encode())
            assets['sources'][key] = dict(path=str(source), sha256=studio_native.sha(source))
            self.sources[key] = source
        self.manifest = self.root / 'private-assets.json'
        self.manifest.write_text(json.dumps(assets), encoding='utf-8')
        self.adapter = studio_native.configure(self.manifest, self.root / 'native-output', 12345)
        self.addCleanup(self.worker.assert_not_called)

    def prepare(self, draft=None):
        record = configurator.save_draft(complete() if draft is None else draft)
        return record, studio_cad.prepare(record['id'], record['revision'])

    def assert_private_paths_absent(self, value):
        serialized = json.dumps(value, ensure_ascii=False)
        for source in list(self.sources.values()) + [self.manifest, self.root]:
            # Compare the JSON representation too, since Windows separators are escaped.
            self.assertNotIn(json.dumps(str(source))[1:-1], serialized)
            self.assertNotIn(source.as_posix(), serialized)

    def test_configured_supported_plan_is_executable_but_not_native_proof(self):
        record, plan = self.prepare()
        self.assertIs(self.adapter, studio_native.configured())
        self.assertTrue(plan['executable'])
        self.assertEqual('t1-source-bound-v1', plan['adapter_id'])
        self.assertEqual([], plan['blockers'])
        self.assertEqual('NOT RUN', plan['native_status'])
        self.assertEqual('NOT RUN', plan['native_spec']['native_validation'])
        self.assertFalse(plan['production_approved'])
        self.assertEqual([12, 60, 48], [len(plan['native_spec'][k]) for k in ('panels', 'parts', 'cuts')])
        self.assertTrue(all(r['native_binding_status'] == 'source_pinned' for r in plan['selected_parts']))
        self.assertEqual(studio_native.sha(self.manifest), plan['native_spec']['asset_manifest_sha256'])
        self.assertTrue(all('path' not in s for s in plan['native_spec']['sources']))
        self.assert_private_paths_absent(plan)
        self.assertTrue(studio_cad.verify_plan(plan))
        self.assertEqual(plan, studio_cad.read_plan(plan['plan_id'], plan['plan_sha256']))
        self.assertEqual(record, configurator.read_draft(record['id']))
        self.assertFalse((self.root / 'native-output').exists())

    def test_unsupported_selected_unplaced_wheel_never_becomes_executable(self):
        catalog = studio_parts.catalog()
        wheel = copy.deepcopy(next(r for r in catalog['items'] if r['id'] == 'source-caster-epson'))
        wheel.update(id='unit-unsupported-wheel', name='Synthetic unmapped wheel', sku='unit-wheel')
        wheel['definition_sha256'] = studio_cad.fingerprint(wheel)
        catalog['items'].append(wheel)
        catalog['revision'] = studio_cad.fingerprint(catalog['items'])
        draft = complete()
        draft['hardware'].append(dict(part_id=wheel['id'], revision=wheel['revision']))
        with patch.object(studio_parts, 'catalog', return_value=catalog):
            _, plan = self.prepare(draft)
            self.assertFalse(plan['executable'])
            self.assertIsNone(plan['adapter_id'])
            self.assertNotIn('native_spec', plan)
            selected = next(r for r in plan['selected_parts'] if r['part_id'] == wheel['id'])
            self.assertEqual([], selected['instance_ids'])
            self.assertEqual('wheels', selected['family_id'])
            blockers = {b['code'] for b in plan['blockers']}
            self.assertIn('SELECTED_PART_UNPLACED', blockers)
            self.assertIn('NATIVE_T1_CONTRACT_REQUIRED', blockers)
            self.assertTrue(studio_cad.verify_plan(plan))

    def test_changed_source_blocks_compile_and_invalidates_prepared_plan(self):
        record, plan = self.prepare()
        self.sources['baseline'].write_bytes(b'Changed source revision')
        with self.assertRaisesRegex(ValueError, 'Źródło CAD'):
            self.adapter.compile(record)
        analyzed = studio_cad.analyze(record)
        self.assertFalse(analyzed['executable'])
        self.assertIn('NATIVE_T1_CONTRACT_REQUIRED', {b['code'] for b in analyzed['blockers']})
        self.assert_private_paths_absent(analyzed)
        with self.assertRaises(studio_cad.PlanConflict):
            studio_cad.read_plan(plan['plan_id'], plan['plan_sha256'])

    def test_changed_manifest_requires_reconfiguration_and_old_plan_stays_invalid(self):
        record, plan = self.prepare()
        self.manifest.write_bytes(self.manifest.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'Manifest CAD'):
            self.adapter.compile(record)
        with self.assertRaises(studio_cad.PlanConflict):
            studio_cad.verify_plan(plan)
        replacement = studio_native.configure(self.manifest, self.root / 'other-output', 12345)
        self.assertNotEqual(replacement.manifest_sha, self.adapter.manifest_sha)
        self.assertTrue(studio_cad.analyze(record)['executable'])
        with self.assertRaises(studio_cad.PlanConflict):
            studio_cad.verify_plan(plan)

    def test_revision_is_bound_in_plan_and_native_spec(self):
        record, plan = self.prepare()
        for data in (plan, plan['native_spec']):
            self.assertEqual(record['id'], data['draft_id'])
            self.assertEqual(record['revision'], data['draft_revision'])
            self.assertEqual(studio_cad.fingerprint(record['draft']), data['draft_sha256'])
        changed = copy.deepcopy(record['draft'])
        changed['internal_mm'][0] += 20
        updated = configurator.save_draft(changed, record['id'], record['revision'])
        with self.assertRaises(studio_cad.PlanConflict):
            studio_cad.prepare(record['id'], record['revision'])
        with self.assertRaises(studio_cad.PlanConflict):
            studio_cad.verify_plan(plan)
        new_plan = studio_cad.prepare(updated['id'], updated['revision'])
        self.assertTrue(new_plan['executable'])
        self.assertEqual(2, new_plan['native_spec']['draft_revision'])
        self.assertNotEqual(plan['plan_sha256'], new_plan['plan_sha256'])
        self.assertNotEqual(plan['native_spec']['parameters'], new_plan['native_spec']['parameters'])

    def test_forged_native_spec_with_recomputed_plan_hash_is_rejected(self):
        _, plan = self.prepare()
        plan['native_spec']['sources'][0]['sha256'] = '0' * 64
        plan['plan_sha256'] = studio_cad.fingerprint({k: v for k, v in plan.items() if k != 'plan_sha256'})
        with self.assertRaises(studio_cad.PlanConflict):
            studio_cad.verify_plan(plan)

    def test_missing_source_error_is_publicly_sanitized(self):
        record, _ = self.prepare()
        self.sources['templates'].unlink()
        with self.assertRaises(OSError):
            self.adapter.compile(record)
        plan = studio_cad.analyze(record)
        self.assertFalse(plan['executable'])
        blocker = next(b for b in plan['blockers'] if b['code'] == 'NATIVE_T1_CONTRACT_REQUIRED')
        self.assertEqual('Brak kompletnego źródła CAD dla tego układu.', blocker['message'])
        self.assert_private_paths_absent(plan)

    def test_without_configured_adapter_same_saved_draft_is_blocked(self):
        record, _ = self.prepare()
        with patch.object(studio_native, '_configured', None):
            plan = studio_cad.analyze(record)
            self.assertFalse(plan['executable'])
            self.assertIn('NATIVE_ADAPTER_PENDING', {b['code'] for b in plan['blockers']})
        self.assertIs(self.adapter, studio_native.configured())


if __name__ == '__main__':
    unittest.main()
