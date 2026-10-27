import copy
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from rockpro_cad import configurator, studio_cad
from rockpro_cad.reference_studio import make_handler
from rockpro_cad.mcp import project_store
from rockpro_cad.mcp.test_configurator import concept


def handled():
    draft = concept()
    draft['hardware'] = [dict(part_id='H7159', revision=1)]
    draft['placements'] = [dict(id='carry', part_id='H7159', revision=1,
        section_id='body', face='left', u=.5, v=.5, rotation_deg=0,
        pattern='symmetric', count_per_wall=2, handles_per_wall=2,
        opposite_wall=True, spread=.5)]
    return draft


class StudioCadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        patcher = patch.object(project_store, 'DB_PATH', self.root/'test.sqlite3')
        patcher.start(); self.addCleanup(patcher.stop)

    def test_every_selected_instance_and_recipe_is_accounted_without_inventing_fit(self):
        original = handled(); before = copy.deepcopy(original)
        saved = configurator.save_draft(original)
        plan = studio_cad.prepare(saved['id'], saved['revision'])
        self.assertEqual(original, before)
        self.assertEqual(len(plan['occurrences']), 4)
        self.assertEqual(len(plan['selected_parts'][0]['instance_ids']), 4)
        self.assertEqual(len(plan['machining_intents']), 8)
        self.assertEqual({i['owner_mount'] for i in plan['machining_intents']},
                         {i['id'] for i in plan['occurrences']})
        self.assertTrue(all(i['target_part'] is None for i in plan['machining_intents']))
        self.assertEqual(plan['expected_api_major'], 29)
        self.assertEqual(plan['target_year'], 2027)
        self.assertFalse(plan['executable']); self.assertFalse(plan['production_approved'])
        self.assertIn('NATIVE_ASSET_BINDING_REQUIRED', {b['code'] for b in plan['blockers']})
        self.assertTrue(studio_cad.verify_plan(plan))

    def test_selected_but_unplaced_part_is_never_omitted(self):
        draft = concept(); draft['hardware'] = [dict(part_id='H2026', revision=1)]
        saved = configurator.save_draft(draft)
        plan = studio_cad.prepare(saved['id'], 1)
        self.assertEqual(plan['selected_parts'][0]['part_id'], 'H2026')
        self.assertIn('SELECTED_PART_UNPLACED', {b['code'] for b in plan['blockers']})
        self.assertIn('MACHINING_KNOWLEDGE_REQUIRED', {b['code'] for b in plan['blockers']})

    def test_structural_and_transport_choices_are_not_lost_in_handoff(self):
        from rockpro_cad.mcp.test_studio_structure import complete
        saved = configurator.save_draft(complete())
        plan = studio_cad.prepare(saved['id'], 1)
        by_id = {r['part_id']:r for r in plan['selected_parts']}
        self.assertEqual(len(by_id['source-caster-epson']['instance_ids']), 4)
        self.assertEqual(len(by_id['W0968Z']['instance_ids']), 4)
        self.assertTrue(by_id['EG-0113']['instance_ids'])
        self.assertTrue(plan['construction_parameters']['stacking'])
        self.assertEqual(plan['project_summary']['unplaced_selection'], [])
        self.assertTrue(all(i['stage_id']=='wheels' for i in plan['occurrences']
                            if i.get('family_id') in ('wheels','stacking_sockets','wheel_pads')))
        self.assertTrue(studio_cad.verify_plan(plan))

    def test_joint_bound_hinges_interrupt_profiles_like_closure_rows(self):
        from rockpro_cad import studio_structure
        from rockpro_cad.mcp.test_studio_structure import complete
        draft = complete(); preview = configurator.preview(draft)
        placement = copy.deepcopy(preview['placement'])
        for item in placement['items']:
            if item['part_id'] == '270836':
                self.assertTrue(item.pop('seam_id'))
                item['joint_id'] = 'synthetic-same-measured-seam'
        checked = studio_structure.preview(draft, preview['sections'], placement)
        self.assertEqual(checked['items'], preview['construction']['items'])

    def test_forged_rehashed_plan_does_not_gain_native_permission(self):
        saved = configurator.save_draft(handled()); plan = studio_cad.prepare(saved['id'], 1)
        plan.update(executable=True, blockers=[], adapter_id='pretend')
        plan['plan_sha256'] = studio_cad.fingerprint({k:v for k,v in plan.items() if k != 'plan_sha256'})
        with self.assertRaises(studio_cad.PlanConflict): studio_cad.verify_plan(plan)

    def test_revision_change_and_compiler_change_invalidate_plan(self):
        saved = configurator.save_draft(concept()); plan = studio_cad.prepare(saved['id'], 1)
        with patch.object(studio_cad, 'compiler_revision', return_value='f'*64):
            with self.assertRaises(studio_cad.PlanConflict): studio_cad.verify_plan(plan)
        changed = copy.deepcopy(saved['draft']); changed['internal_mm'][0] += 10
        configurator.save_draft(changed, saved['id'], 1)
        with self.assertRaises(studio_cad.PlanConflict): studio_cad.read_plan(plan['plan_id'], plan['plan_sha256'])
        with self.assertRaises(studio_cad.PlanConflict): studio_cad.prepare(saved['id'], 1)

    def test_plan_is_durable_without_changing_the_saved_draft(self):
        saved = configurator.save_draft(handled()); plan = studio_cad.prepare(saved['id'], 1)
        self.assertEqual(studio_cad.read_plan(plan['plan_id'], plan['plan_sha256']), plan)
        self.assertEqual(configurator.read_draft(saved['id']), saved)
        with self.assertRaises(studio_cad.PlanConflict): studio_cad.read_plan(plan['plan_id'], '0'*64)

    def test_unknown_revision_and_client_fields_are_rejected(self):
        for rev in (True, 0, -1, '1'):
            with self.assertRaises(ValueError): studio_cad.prepare('a'*32, rev)
        with self.assertRaises(ValueError): studio_cad.prepare('../private', 1)
        saved = configurator.save_draft(concept()); plan = studio_cad.prepare(saved['id'], 1)
        plan['ignored_field'] = 'must not be ignored'
        with self.assertRaises(studio_cad.PlanConflict): studio_cad.verify_plan(plan)

    def test_http_plan_blocked_build_and_origin_use_the_same_backend(self):
        saved = configurator.save_draft(handled())
        server = ThreadingHTTPServer(('127.0.0.1',0), make_handler({}, {}, 's'*24))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        prefix = '/'+'s'*24+'/'
        def post(endpoint, value, origin=True):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            headers = {'Content-Type':'application/json', 'X-RockPro-Session':'s'*24,
                       'Origin': 'http://127.0.0.1:'+str(server.server_port) if origin else 'https://other.example'}
            try:
                connection.request('POST', prefix+endpoint, json.dumps(value), headers)
                result = connection.getresponse(); return result.status, json.loads(result.read())
            finally: connection.close()
        code, plan = post('wizard/native-plan', dict(draft_id=saved['id'], expected_revision=1))
        self.assertEqual(code, 200)
        code, body = post('wizard/native-build', dict(plan_id=plan['plan_id'], plan_sha256=plan['plan_sha256'], operation_id='b'*32))
        self.assertEqual(code, 409); self.assertEqual(body['details']['code'], 'CAD_PLAN_BLOCKED')
        self.assertEqual(post('wizard/native-plan', dict(draft_id=saved['id'], expected_revision=1), False)[0],403)
        self.assertEqual(post('wizard/native-plan', dict(draft_id=saved['id'], expected_revision=1, command='shell'))[0],400)


if __name__ == '__main__': unittest.main()
