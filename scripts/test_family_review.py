"""Review packets bind evidence without turning proposed roles into approval."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from prepare_family_review import prepare


def fixture(root):
    source = root/'source.ics'; source.write_bytes(b'synthetic test source')
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    matrix = [[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]]
    rows = [dict(id=1, path='root', name='', type='Z_ELEMENT_UNKNOWN', world_mm=matrix, parent_mm=matrix),
            dict(id=2, path='root/2', name='<svg onload="x">', type='Z_ELEMENT_ASSEMBLY', world_mm=matrix, parent_mm=matrix),
            dict(id=3, path='root/2/3', name='płyta', type='Z_ELEMENT_PART', world_mm=matrix, parent_mm=matrix,
                 bounds_local_m=[0,0,0,.01,.2,.3])]
    inventory = root/'M01-inventory.json'
    inventory.write_text(json.dumps(dict(source_sha256=sha, api_version='29.test', rows=rows, errors=[])), encoding='utf-8')
    manifest = root/'manifest.json'
    manifest.write_text(json.dumps(dict(contract='rockpro-model-survey-v1',
        files={'source.ics':dict(bytes=source.stat().st_size,sha256=sha)},
        models=[dict(key='M01',name=source.name,source=str(source),sha256=sha)])), encoding='utf-8')
    drafts = root/'drafts.json'
    drafts.write_text(json.dumps([dict(model='M01',source_sha256=sha,
        inventory_sha256=hashlib.sha256(inventory.read_bytes()).hexdigest(),status='reference_draft',
        executable_template=False,production_approved=False,family_candidate='Rodzina testowa',
        component_candidates=[dict(id=2,role='<script>test</script>',confirmed=False)])]), encoding='utf-8')
    questions = root/'questions.md'
    questions.write_text('[ ] Q01. Wspólne pytanie?\n[ ] Q08. Pytanie <o> model?\n', encoding='utf-8')
    config = root/'config.json'
    config.write_text(json.dumps(dict(schema_version=1,common_questions=['Q01'],
        models=[dict(key='M01',questions=['Q08'])])), encoding='utf-8')
    return [manifest,drafts,root,questions,config,root/'output']


def edit(path, callback):
    data = json.loads(path.read_text(encoding='utf-8'))
    callback(data)
    path.write_text(json.dumps(data), encoding='utf-8')


class FamilyReviewTests(unittest.TestCase):
    def test_source_revision_mismatch_creates_no_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = fixture(Path(tmp)); (Path(tmp)/'source.ics').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Source revision mismatch'):
                prepare(*args)
            self.assertFalse(args[-1].exists())

    def test_inventory_revision_mismatch_creates_no_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = fixture(Path(tmp))
            with (Path(tmp)/'M01-inventory.json').open('ab') as stream: stream.write(b' ')
            with self.assertRaisesRegex(ValueError, 'Inventory revision changed'):
                prepare(*args)
            self.assertFalse(args[-1].exists())

    def test_unknown_component_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = fixture(Path(tmp))
            edit(args[1], lambda data: data[0]['component_candidates'][0].update(id=999))
            with self.assertRaisesRegex(ValueError, 'candidate component ID'):
                prepare(*args)

    def test_empty_candidates_keep_unknown_mapping_and_no_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = fixture(Path(tmp))
            edit(args[1], lambda data: data[0].update(component_candidates=[]))
            packet = prepare(*args); model = packet['models'][0]
            self.assertEqual(model['semantic_mapping_status'], 'no_candidates')
            self.assertEqual(model['component_candidates'], [])
            self.assertEqual(model['cad_physical_part_count'], 1)
            self.assertEqual(model['dimensions_parametric_status'], 'NOT RUN')
            self.assertEqual(model['machining_knowledge'], 'unknown')
            self.assertFalse(model['production_approved'])
            self.assertFalse(model['purchasing_bom'])
            self.assertIn('Brak kandydatów', (args[-1]/'index.html').read_text(encoding='utf-8'))

    def test_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = fixture(Path(tmp)); args[-1].mkdir()
            marker = args[-1]/'keep'; marker.write_text('unchanged')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                prepare(*args)
            self.assertEqual(marker.read_text(), 'unchanged')
            self.assertFalse((args[-1]/'packet.json').exists())

    def test_real_path_subtree_counts_questions_and_html_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = fixture(Path(tmp)); packet = prepare(*args)
            model = packet['models'][0]; candidate = model['component_candidates'][0]
            self.assertEqual(candidate['source_path'], 'root/2')
            self.assertEqual(candidate['subtree_node_count'], 2)
            self.assertEqual(candidate['subtree_cad_part_count'], 1)
            self.assertFalse(candidate['confirmed'])
            self.assertEqual(candidate['role_status'], 'proposal_to_confirm')
            self.assertEqual([q['id'] for q in model['questions']], ['Q01','Q08'])
            page = (args[-1]/'index.html').read_text(encoding='utf-8')
            self.assertIn('&lt;script&gt;test&lt;/script&gt;', page)
            self.assertIn('&lt;svg onload=&quot;x&quot;&gt;', page)
            self.assertNotIn('<script>', page)
            self.assertEqual(json.loads((args[-1]/'packet.json').read_text(encoding='utf-8')), packet)

    def test_approval_and_unknown_questions_are_not_imported_silently(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = fixture(Path(tmp))
            edit(args[1], lambda data: data[0]['component_candidates'][0].update(confirmed=True))
            with self.assertRaisesRegex(ValueError, 'unconfirmed role'):
                prepare(*args)
            edit(args[1], lambda data: data[0]['component_candidates'][0].update(confirmed=False))
            edit(args[4], lambda data: data['models'][0].update(questions=['Q99']))
            with self.assertRaisesRegex(ValueError, 'Unknown or repeated model question'):
                prepare(*args)


if __name__ == '__main__':
    unittest.main()
