"""Real stdio planning protocol; never connects to IronCAD."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

import server
import worker
from rockpro_cad.core_case.manifest import build_manifest
from rockpro_cad.core_case.test_manifest import inventory

ROOT = Path(__file__).resolve().parents[3]


class CoreMcpTests(unittest.TestCase):
    def test_core_tool_schemas_and_unknown_argument_boundary(self):
        names = {row['name'] for row in server.SCHEMAS}
        self.assertTrue({'preview_case','prepare_case_request','save_case_request',
                         'get_case_request','plan_project_case','execute_case_plan',
                         'recover_case_operation','get_case_operation','list_case_operations'} <= names)
        with self.assertRaisesRegex(ValueError, 'argument'):
            worker.dispatch('preview_case', {'request':{}, 'shell':'not executable'})

    def test_real_stdio_preview_and_draft_refusal(self):
        fixture = json.loads((ROOT/'tests/core_design/cases.json').read_text(encoding='utf-8'))
        recipe = json.loads((ROOT/'Integracja/rockpro_cad/core_case/templates/prototype-v1.json').read_text(encoding='utf-8'))
        request = {'spec':fixture['cases'][0]['spec'], 'manifest':fixture['manifest'],
                   'template_recipe':recipe, 'scenario':{'operation':'plan'}}
        draft = copy.deepcopy(request)
        # Use a structurally complete source inventory: malformed input must
        # remain MANIFEST_INVALID, while an accounted draft is NOT_READY.
        draft['manifest'] = build_manifest(inventory())
        calls = [{'id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
                 {'id':2,'method':'tools/call','params':{'name':'preview_case','arguments':{'request':request}}},
                 {'id':3,'method':'tools/call','params':{'name':'preview_case','arguments':{'request':draft}}}]
        run = subprocess.run([sys.executable, str(Path(__file__).with_name('server.py'))],
                             input='\n'.join(json.dumps(r) for r in calls)+'\n',
                             encoding='utf-8',capture_output=True,timeout=40,check=True)
        replies = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual(len(replies),3)
        planned = json.loads(replies[1]['result']['content'][0]['text'])
        self.assertEqual(planned['status'],'planned')
        self.assertFalse(planned['production_approved'])
        self.assertTrue(planned['synthetic'])
        self.assertEqual(len(planned['groups']),37)
        self.assertEqual(len(planned['occurrences']),67)
        refused = replies[2]['result']
        if refused.get('isError'):
            self.assertIn('MANIFEST_NOT_READY', refused['content'][0]['text'])
        else:
            data = json.loads(refused['content'][0]['text'])
            self.assertEqual(data['status'],'blocked')
            self.assertIn('MANIFEST_NOT_READY',{d['code'] for d in data['diagnostics']})
