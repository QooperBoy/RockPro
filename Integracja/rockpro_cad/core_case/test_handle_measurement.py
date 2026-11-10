import copy
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case import handle_measurement as measure
from test_native_changes import four_handles


class HandleMeasurementTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.source=Path(self.temp.name)/'source.ics';self.source.write_bytes(b'synthetic only')
        self.baseline,self.mapping,_=four_handles()
        self.active=SimpleNamespace(Name='untouched-active.ics',Modified=True)
        self.provenance=dict(document_path=str(self.source),modified=False,file_guid=self.baseline['file_guid'])
        self.adapter=SimpleNamespace(base=SimpleNamespace(ActiveDoc=self.active),document=object(),api=object(),provenance=lambda:dict(self.provenance))

    def capture(self):
        return measure.capture_handle_measurement(self.source,self.baseline,self.mapping,adapter_factory=lambda source:self.adapter)

    def test_read_twice_and_preserve_path_guid_dirty_state_and_active_document(self):
        snapshot=copy.deepcopy(self.baseline)
        with patch.object(measure,'capture_selected_poses',return_value=snapshot) as reader:
            result=self.capture()
        self.assertEqual(reader.call_count,2);self.assertTrue(result['native_read_only'])
        self.assertEqual(result['snapshot'],self.baseline);self.assertIs(self.adapter.base.ActiveDoc,self.active)
        self.assertTrue(self.active.Modified);self.assertEqual(self.source.read_bytes(),b'synthetic only')

    def test_mid_read_movement_and_saved_file_change_are_rejected(self):
        changed=copy.deepcopy(self.baseline);changed['members'][-1]['matrix_world_mm'][3][1]+=12
        with patch.object(measure,'capture_selected_poses',side_effect=[self.baseline,changed]):
            with self.assertRaisesRegex(ValueError,'CAD_CHANGED'):self.capture()
        def mutate(*args):self.source.write_bytes(b'concurrent save');return self.baseline
        with patch.object(measure,'capture_selected_poses',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'SOURCE_CHANGED'):self.capture()

    def test_guid_wrong_path_and_active_context_change_never_fall_back_to_another_document(self):
        for change,code in [({'file_guid':'wrong'},'GUID_MISMATCH'),({'document_path':str(self.source.parent/'other.ics')},'PATH_MISMATCH')]:
            before=dict(self.provenance);self.provenance.update(change)
            with patch.object(measure,'capture_selected_poses') as reader:
                with self.assertRaisesRegex(ValueError,code):self.capture()
                reader.assert_not_called()
            self.provenance=before
        def change_context(*args):self.adapter.base.ActiveDoc=None;return self.baseline
        with patch.object(measure,'capture_selected_poses',side_effect=change_context):
            with self.assertRaisesRegex(ValueError,'ACTIVE_CONTEXT_CHANGED'):self.capture()

    def test_fingerprint_ignores_com_noise_and_order_but_not_constructor_changes(self):
        changed=copy.deepcopy(self.baseline);changed['members'].reverse()
        changed['members'][0]['matrix_world_mm'][3][0]+=1e-10
        self.assertEqual(measure.snapshot_fingerprint(changed),measure.snapshot_fingerprint(self.baseline))
        changed['members'][0]['matrix_world_mm'][3][0]+=1
        self.assertNotEqual(measure.snapshot_fingerprint(changed),measure.snapshot_fingerprint(self.baseline))

    def test_closed_document_returns_actionable_error_without_opening_it(self):
        def closed(source):raise RuntimeError('Expected source is not already open in the running object table')
        with patch.object(measure,'capture_selected_poses') as reader:
            with self.assertRaisesRegex(ValueError,'HANDLE_DOCUMENT_NOT_OPEN'):
                measure.capture_handle_measurement(self.source,self.baseline,self.mapping,adapter_factory=closed)
            reader.assert_not_called()


if __name__=='__main__':unittest.main()
