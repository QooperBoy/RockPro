"""Saved revision acquisition guards; synthetic documents, no CAD imports."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.source_capture import capture_source_revision, select_source_binding
from test_manifest import inventory


class SourceCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.source = self.folder / 'original.ics'
        self.source.write_bytes(b'synthetic saved source')
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.sessions = []
        self.mode = None

    def session(self):
        test = self
        class Session:
            closed = False
            def open_owned(self, path):
                self.path = path
                self.before = dict(document_path=str(path), file_guid='fixture-guid',
                                   modified=False, connection='existing_rot_only')
                if test.mode == 'open_failure':
                    raise RuntimeError('synthetic open failure')
                return copy.deepcopy(self.before)
            def inspect(self):
                data = inventory()
                data['cad_document'] = dict(before=copy.deepcopy(self.before),
                    after=copy.deepcopy(self.before), disk_equivalence='not_proven')
                data['source'] = dict(path=str(self.path), sha256_before=test.digest,
                    sha256_after=test.digest, unchanged=True)
                if test.mode == 'dirty':
                    data['cad_document']['after']['modified'] = True
                if test.mode == 'identity_drift':
                    data['cad_document']['after']['file_guid'] = 'other'
                if test.mode == 'source_drift':
                    test.source.write_bytes(b'external change during capture')
                poses = {'rows': [dict(id=r['id'], name=r['name'], kind=r['kind'],
                    occurrence_path=r['occurrence_path'], matrix_world_mm=copy.deepcopy(
                        [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]), errors=[]) for r in data['rows']],
                    'source':copy.deepcopy(data['source']),
                    'cad_document':copy.deepcopy(data['cad_document'])}
                if test.mode == 'pose_drift':
                    poses['cad_document']['before']['modified'] = True
                return data, poses
            def state(self):
                return copy.deepcopy(self.before)
            def close(self):
                self.closed = True
        session = Session()
        self.sessions.append(session)
        return session

    def capture(self, **kw):
        return capture_source_revision(self.source, self.folder/'new-run',
            expected_sha256=self.digest, node_id=4, occurrence_path=[0,1],
            node_name='17251S_1', session_factory=self.session, **kw)

    def test_one_saved_revision_accounts_every_node_and_closes_owned_input(self):
        result = self.capture()
        self.assertTrue(result['passed'])
        self.assertTrue(self.sessions[0].closed)
        folder=self.folder/'new-run'
        inv=json.loads((folder/'inventory.json').read_text(encoding='utf-8'))
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        binding=json.loads((folder/'selected_binding.json').read_text(encoding='utf-8'))
        self.assertEqual(inv['cad_document']['disk_equivalence'],'saved_document')
        self.assertEqual(len(inv['rows']),len(manifest['occurrences']))
        self.assertEqual(binding['node_id'],4)
        self.assertEqual(binding['source_sha256'],self.digest)
        self.assertEqual(manifest['manifest_stage'],'inventory_draft')
        self.assertFalse(manifest['production_approved'])
        self.assertEqual(self.source.read_bytes(),b'synthetic saved source')

    def test_stale_source_pin_fails_before_any_session_or_output(self):
        self.digest='0'*64
        with self.assertRaisesRegex(ValueError,'SHA256'):
            self.capture()
        self.assertEqual(self.sessions,[])
        self.assertFalse((self.folder/'new-run').exists())

    def test_existing_output_is_never_reused(self):
        (self.folder/'new-run').mkdir()
        marker=self.folder/'new-run'/'keep.txt'; marker.write_text('preserve')
        with self.assertRaises(FileExistsError):self.capture()
        self.assertEqual(marker.read_text(),'preserve')
        self.assertEqual(self.sessions,[])

    def test_dirty_identity_and_pose_drift_cannot_be_marked_saved(self):
        for mode in ('dirty','identity_drift','pose_drift'):
            with self.subTest(mode=mode):
                self.mode=mode
                with self.assertRaises(ValueError):
                    capture_source_revision(self.source,self.folder/mode,
                        expected_sha256=self.digest,node_id=4,occurrence_path=[0,1],
                        node_name='17251S_1',session_factory=self.session)
                self.assertTrue(self.sessions[-1].closed)
                self.assertFalse((self.folder/mode/'manifest.json').exists())

    def test_changed_original_fails_and_records_failure_without_approval(self):
        self.mode='source_drift'
        with self.assertRaises(ValueError):self.capture()
        self.assertTrue(self.sessions[-1].closed)
        result=json.loads((self.folder/'new-run'/'capture_receipt.json').read_text(encoding='utf-8'))
        self.assertFalse(result['passed'])
        self.assertFalse(result['original_unchanged'])
        self.assertFalse((self.folder/'new-run'/'manifest.json').exists())

    def test_wrong_occurrence_id_fails_instead_of_matching_by_name(self):
        with self.assertRaises(ValueError):
            capture_source_revision(self.source,self.folder/'wrong',
                expected_sha256=self.digest,node_id=999,occurrence_path=[0,1],
                node_name='17251S_1',session_factory=self.session)
        self.assertTrue(self.sessions[-1].closed)
        self.assertTrue((self.folder/'wrong'/'raw_inventory.json').is_file())
        self.assertFalse((self.folder/'wrong'/'selected_binding.json').exists())

    def test_inventory_only_does_not_select_a_same_named_catalog_object(self):
        result=capture_source_revision(self.source,self.folder/'inventory-only',
            expected_sha256=self.digest,session_factory=self.session)
        self.assertTrue(result['passed'])
        self.assertFalse((self.folder/'inventory-only'/'selected_binding.json').exists())
        self.assertTrue((self.folder/'inventory-only'/'manifest.json').exists())

    def test_opaque_parent_mirror_is_preserved_only_with_proper_world_frame(self):
        self.capture()
        folder=self.folder/'new-run'
        inv=json.loads((folder/'inventory.json').read_text(encoding='utf-8'))
        poses=json.loads((folder/'poses.json').read_text(encoding='utf-8'))
        row=next(r for r in poses['rows'] if r['id']==4)
        row['matrix_parent_mm_raw']=[[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        row['errors']=[dict(field='matrix_parent_mm',type='ValueError',message='improper ICAPI rotation')]
        original=copy.deepcopy(poses)
        binding=select_source_binding(inv,poses,node_id=4,occurrence_path=[0,1],node_name='17251S_1')
        self.assertEqual(binding['expected_world_matrix_mm'],row['matrix_world_mm'])
        self.assertEqual(poses,original)
        row['matrix_parent_mm_raw'][0][0]=-2
        with self.assertRaises(ValueError):
            select_source_binding(inv,poses,node_id=4,occurrence_path=[0,1],node_name='17251S_1')
        row.update(copy.deepcopy(original['rows'][3]))
        row['matrix_world_mm'][0][0]=-1
        with self.assertRaises(ValueError):
            select_source_binding(inv,poses,node_id=4,occurrence_path=[0,1],node_name='17251S_1')

    def test_open_failure_still_runs_owned_document_cleanup(self):
        self.mode='open_failure'
        with self.assertRaises(RuntimeError):self.capture()
        self.assertTrue(self.sessions[-1].closed)


if __name__=='__main__':unittest.main()
