"""Offline CAS, journal and recovery tests. The executor writes synthetic files."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import core_service as service
import layout
import project_store as store
import worker
from rockpro_cad.core_case.test_planner import request
from rockpro_cad.core_case.native import preflight_plan


class CoreServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'source.ics'
        self.source.write_bytes(b'untouched source')
        self.patches = [patch.object(worker, 'ROOT', self.root),
                        patch.object(store, 'DB_PATH', self.root / 'projects.sqlite3')]
        for p in self.patches:
            p.start()
        self.project = store.save_project('Case service probe', source=str(self.source))['project']
        self.project_id = self.project['id']
        self.native_calls = 0

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def fake_execute(self, plan, *, output_dir, source, operation_id):
        self.native_calls += 1
        target = Path(output_dir) / operation_id
        target.mkdir()
        capture = target / 'source_snapshot.ics'
        capture.write_bytes(Path(source).read_bytes())
        output = target / 'case_prototype.ics'
        output.write_text(json.dumps(plan), encoding='utf-8')
        measurements = [dict(occurrence_id=p['id'], cad_node_id=f'fake-node-{i}',
                             matrix_world_mm=p['native_matrix_mm'], bbox_world_mm=p['expected_bbox_world_mm'])
                        for i, p in enumerate(preflight_plan(plan))]
        receipt = dict(schema_version=1, passed=True, operation_id=operation_id,
                       output_path=str(output), output_sha256=service._hash_file(output),
                       source_unchanged=True, production_approved=False,
                       geometry_scope='synthetic_native_block_prototype',
                       source=dict(path=str(source), sha256_before=service._hash_file(source),
                                   sha256_after=service._hash_file(source), unchanged=True,
                                   snapshot_path=str(capture), snapshot_sha256=service._hash_file(capture)),
                       stages={k: 'PASS' for k in ('read', 'copy', 'change_on_copy', 'measurement', 'save_reopen')},
                       measurements=measurements)
        (target / 'native_receipt.json').write_text(json.dumps(receipt), encoding='utf-8')
        return receipt

    def saved_plan(self):
        saved = service.save_case_request(self.project_id, request(), 0, actor='UI', change_source='test')
        self.assertTrue(saved['saved'])
        return service.plan_project_case(self.project_id, saved['revision'])

    def execute(self, plan, operation_id='operation-1'):
        with patch.object(service, '_native_execute', side_effect=self.fake_execute):
            return service.execute_case_plan(self.project_id, plan['plan_id'], operation_id, plan['revision'])

    def assert_code(self, code, action):
        with self.assertRaises(service.CoreServiceError) as caught:
            action()
        self.assertEqual(caught.exception.details['code'], code)

    def test_preview_is_pure_and_saved_request_is_detached(self):
        data = request()
        before = copy.deepcopy(data)
        result = service.preview_case(data)
        self.assertEqual(result['status'], 'planned')
        self.assertEqual(data, before)
        self.assertEqual(service.get_case_request(self.project_id)['revision'], 0)
        saved = service.save_case_request(self.project_id, data, 0)
        saved['request']['spec']['layout']['x'] = 999
        self.assertEqual(service.get_case_request(self.project_id)['request'], before)

    def test_ui_ai_compare_and_swap_and_history(self):
        data = request()
        self.assertEqual(service.save_case_request(self.project_id, data, 0, actor='UI')['revision'], 1)
        self.assert_code('CASE_REVISION_CONFLICT', lambda: service.save_case_request(self.project_id, data, 0, actor='AI'))
        changed = copy.deepcopy(data)
        changed['spec']['layout']['x'] = 420
        self.assertEqual(service.save_case_request(self.project_id, changed, 1, actor='AI')['revision'], 2)
        with store.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM case_request_versions').fetchone()[0], 2)
        self.assertEqual(service.get_case_request(self.project_id)['request'], changed)
        kinds = [row['kind'] for row in store.get_history(self.project_id)['events']]
        self.assertEqual(kinds.count('case_request_saved'), 2)

    def test_blocked_request_never_gets_executable_plan(self):
        data = request()
        data['spec']['units'] = 'm'
        with patch.object(service, '_native_execute') as native:
            result = service.save_case_request(self.project_id, data, 0)
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['saved'])
        self.assertEqual(result['preview']['changes'], [])
        native.assert_not_called()
        self.assert_code('CASE_REQUEST_REQUIRED', lambda: service.plan_project_case(self.project_id, 0))

    def test_registered_operation_is_idempotent_and_archive_is_separate(self):
        plan = self.saved_plan()
        result = self.execute(plan)
        self.assertEqual(result['status'], 'registered', result)
        self.assertEqual(self.native_calls, 1)
        repeated = self.execute(plan)
        self.assertEqual(result, repeated)
        self.assertEqual(self.native_calls, 1)
        archive = Path(result['snapshot_path'])
        working = Path(result['receipt']['output_path'])
        self.assertNotEqual(archive, working)
        working.write_bytes(b'constructor editing working copy')
        snapshots = store.list_snapshots(self.project_id)['snapshots']
        self.assertEqual(snapshots[0]['integrity'], 'verified')
        self.assertEqual(snapshots[0]['validation'], 'prototype')
        self.assertEqual(store.get_project(self.project_id)['project']['source'], str(self.source))
        self.assertEqual(self.source.read_bytes(), b'untouched source')

    def test_same_operation_id_cannot_be_rebound(self):
        first = self.saved_plan()
        self.execute(first)
        second = service.plan_project_case(self.project_id, 1)
        self.assert_code('OPERATION_ID_CONFLICT', lambda: self.execute(second))
        self.assertEqual(self.native_calls, 1)

    def test_changed_request_project_card_source_or_plan_hash_prevents_native_call(self):
        for change in ('request', 'project', 'source', 'plan_hash'):
            with self.subTest(change=change):
                plan = service.plan_project_case(self.project_id, 1) if service.get_case_request(self.project_id)['saved'] else self.saved_plan()
                with store.db() as conn:
                    original_card = dict(conn.execute('SELECT * FROM projects WHERE id=?', (self.project_id,)).fetchone())
                    original_request = dict(conn.execute('SELECT * FROM case_requests WHERE project_id=?', (self.project_id,)).fetchone())
                    if change == 'request':
                        conn.execute('UPDATE case_requests SET revision=2 WHERE project_id=?', (self.project_id,))
                    elif change == 'project':
                        conn.execute('UPDATE projects SET revision=revision+1 WHERE id=?', (self.project_id,))
                    elif change == 'plan_hash':
                        conn.execute("UPDATE case_plans SET plan_json='{}' WHERE id=?", (plan['plan_id'],))
                if change == 'source':
                    self.source.write_bytes(b'changed')
                with patch.object(service, '_native_execute') as native:
                    with self.assertRaises(service.CoreServiceError):
                        service.execute_case_plan(self.project_id, plan['plan_id'], 'invalid-' + change, 1)
                    native.assert_not_called()
                self.source.write_bytes(b'untouched source')
                with store.db() as conn:
                    conn.execute('UPDATE projects SET revision=? WHERE id=?', (original_card['revision'], self.project_id))
                    conn.execute('UPDATE case_requests SET revision=? WHERE project_id=?', (original_request['revision'], self.project_id))

    def test_escaping_operation_id_and_native_output_are_denied(self):
        plan = self.saved_plan()
        self.assert_code('INVALID_ID', lambda: self.execute(plan, '../outside'))
        self.assertEqual(self.native_calls, 0)
        def escaped(*args, **kwargs):
            receipt = self.fake_execute(*args, **kwargs)
            receipt['output_path'] = str(self.source)
            receipt['output_sha256'] = service._hash_file(self.source)
            return receipt
        with patch.object(service, '_native_execute', side_effect=escaped):
            result = service.execute_case_plan(self.project_id, plan['plan_id'], 'bad-output', 1)
        self.assertEqual(result['status'], 'outcome_unknown')
        self.assertEqual(result['diagnostic']['code'], 'OUTPUT_PATH_INVALID')
        self.assertEqual(store.list_snapshots(self.project_id)['snapshots'], [])

    def test_native_failure_has_no_snapshot_and_is_not_retried(self):
        plan = self.saved_plan()
        with patch.object(service, '_native_execute', return_value={'passed': False}) as native:
            result = service.execute_case_plan(self.project_id, plan['plan_id'], 'known-failure', 1)
            again = service.execute_case_plan(self.project_id, plan['plan_id'], 'known-failure', 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result, again)
        self.assertEqual(native.call_count, 1)
        self.assertEqual(store.list_snapshots(self.project_id)['snapshots'], [])

    def test_unknown_outcome_blocks_new_writer_and_recovery_never_reexecutes(self):
        plan = self.saved_plan()
        def crash_after_receipt(*args, **kwargs):
            self.fake_execute(*args, **kwargs)
            raise RuntimeError('simulated executor reply lost after durable receipt')
        with patch.object(service, '_native_execute', side_effect=crash_after_receipt):
            result = service.execute_case_plan(self.project_id, plan['plan_id'], 'lost-reply', 1)
        self.assertEqual(result['status'], 'outcome_unknown')
        self.assert_code('CASE_OPERATION_UNRESOLVED', lambda: self.execute(plan, 'another-operation'))
        repeated = self.execute(plan, 'lost-reply')
        self.assertEqual(repeated['status'], 'outcome_unknown')
        self.assertEqual(self.native_calls, 1)
        with patch.object(service, '_native_execute') as native:
            recovered = service.recover_case_operation(self.project_id, 'lost-reply')
            native.assert_not_called()
        self.assertEqual(recovered['status'], 'registered')
        self.assertEqual(len(store.list_snapshots(self.project_id)['snapshots']), 1)
        self.assertEqual(service.recover_case_operation(self.project_id, 'lost-reply'), recovered)

    def test_crash_after_service_receipt_before_database_commit_can_recover(self):
        plan = self.saved_plan()
        real_event = service._event
        def fail_registration(conn, project_id, kind, payload):
            if kind == 'case_prototype_registered':
                raise RuntimeError('simulated SQLite commit failure')
            return real_event(conn, project_id, kind, payload)
        with patch.object(service, '_event', side_effect=fail_registration):
            result = self.execute(plan, 'registration-crash')
        self.assertEqual(result['status'], 'outcome_unknown')
        self.assertEqual(store.list_snapshots(self.project_id)['snapshots'], [])
        _, target = service._operation_dir(self.project_id, 'registration-crash')
        self.assertTrue((target / 'service_receipt.json').is_file())
        recovered = service.recover_case_operation(self.project_id, 'registration-crash')
        self.assertEqual(recovered['status'], 'registered')
        self.assertEqual(self.native_calls, 1)

    def test_recovery_requires_unchanged_output_and_complete_receipt(self):
        plan = self.saved_plan()
        def crash(*args, **kwargs):
            self.fake_execute(*args, **kwargs)
            raise RuntimeError('lost reply')
        with patch.object(service, '_native_execute', side_effect=crash):
            service.execute_case_plan(self.project_id, plan['plan_id'], 'tampered-output', 1)
        _, target = service._operation_dir(self.project_id, 'tampered-output')
        (target / 'case_prototype.ics').write_bytes(b'tampered')
        self.assert_code('OUTPUT_INTEGRITY', lambda: service.recover_case_operation(self.project_id, 'tampered-output'))
        self.assertEqual(store.list_snapshots(self.project_id)['snapshots'], [])

    def test_missing_receipt_never_reinserts_cad(self):
        plan = self.saved_plan()
        with patch.object(service, '_native_execute', side_effect=RuntimeError('CAD timeout')):
            result = service.execute_case_plan(self.project_id, plan['plan_id'], 'timeout', 1)
        self.assertEqual(result['status'], 'outcome_unknown')
        with patch.object(service, '_native_execute') as native:
            self.assert_code('RECOVERY_EVIDENCE_REQUIRED', lambda: service.recover_case_operation(self.project_id, 'timeout'))
            native.assert_not_called()

    def test_listing_discovers_pending_operation_after_service_restart_and_bounds(self):
        plan = self.saved_plan()
        with patch.object(service, '_native_execute', side_effect=RuntimeError('lost executor')):
            service.execute_case_plan(self.project_id, plan['plan_id'], 'restart-recovery', 1)
        import importlib
        reloaded = importlib.reload(service)
        rows = reloaded.list_case_operations(self.project_id, 1)['operations']
        self.assertEqual(rows[0]['operation_id'], 'restart-recovery')
        self.assertEqual(rows[0]['state'], 'outcome_unknown')
        for limit in (0, 101, True, 1.0):
            with self.subTest(limit=limit):
                self.assert_code('INVALID_LIMIT', lambda: reloaded.list_case_operations(self.project_id, limit))

    def test_registered_archive_corruption_blocks_replay_and_recovery(self):
        plan = self.saved_plan()
        result = self.execute(plan)
        Path(result['snapshot_path']).write_bytes(b'external archive corruption')
        self.assert_code('OUTPUT_INTEGRITY', lambda: self.execute(plan))
        self.assert_code('OUTPUT_INTEGRITY', lambda: service.recover_case_operation(self.project_id, 'operation-1'))
        self.assertEqual(self.native_calls, 1)

    def test_prepared_request_is_bound_to_saved_layout_without_changing_it(self):
        spec = request()['spec']['layout']
        saved_layout = layout.save_layout(self.project_id, spec, 0)
        prepared = service.prepare_case_request(self.project_id, saved_layout['revision'])
        self.assertEqual(prepared['request']['spec']['layout'], spec)
        self.assertEqual(prepared['preview']['status'], 'planned')
        self.assertFalse(prepared['production_approved'])
        changed = dict(spec, x=420)
        layout.save_layout(self.project_id, changed, saved_layout['revision'])
        self.assert_code('LAYOUT_CONFLICT', lambda: service.save_case_request(self.project_id, prepared['request'], 0))
        layout.save_layout(self.project_id, dict(spec, count=1), 2)
        self.assert_code('PROTOTYPE_LAYOUT_UNSUPPORTED', lambda: service.prepare_case_request(self.project_id, 3))


if __name__ == '__main__':
    unittest.main()
