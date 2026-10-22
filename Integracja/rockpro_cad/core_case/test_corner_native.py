"""Background native boundary checks with no desktop or COM calls."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.corner_native import BackgroundGuard,panel_occurrences,compare_corner_persistence

class BackgroundBoundaryTests(unittest.TestCase):
    def test_only_pinned_native_volume_may_change_by_api_roundoff(self):
        volume=1.68665391586591e-05
        before={'observation':{'occurrences':[{'id':9078,'body_signature':{'volume_m3':volume,'faces':27},'matrix_world_mm':[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[100.,200.,300.,1.]]}]},
          'native_source_mapping':[{'native_id':90,'native_occurrence_path':[10,0]}],'vertices':[[1.,2.,3.]],'unrelated':{'volume_m3':volume}}
        after=copy.deepcopy(before);after['observation']['occurrences'][0]['body_signature']['volume_m3']=1.6866539158659102e-05
        report=compare_corner_persistence(before,after,source_volumes={9078:volume})
        self.assertTrue(report['passed']);self.assertEqual(report['max_volume_delta_m3'],3.3881317890172014e-21)
        for mutation in ('volume','nan','id','path','topology','tiny_matrix','huge_matrix','vertex','unrelated_volume','type'):
            changed=copy.deepcopy(after)
            if mutation=='volume':changed['observation']['occurrences'][0]['body_signature']['volume_m3']+=1e-9
            elif mutation=='nan':changed['observation']['occurrences'][0]['body_signature']['volume_m3']=float('nan')
            elif mutation=='id':changed['native_source_mapping'][0]['native_id']+=1
            elif mutation=='path':changed['native_source_mapping'][0]['native_occurrence_path'][1]+=1
            elif mutation=='topology':changed['observation']['occurrences'][0]['body_signature']['faces']+=1
            elif mutation in ('tiny_matrix','huge_matrix'):changed['observation']['occurrences'][0]['matrix_world_mm'][3][0]+=1e-12 if mutation=='tiny_matrix' else 1000
            elif mutation=='vertex':changed['vertices'][0][0]+=1e-12
            elif mutation=='unrelated_volume':changed['unrelated']['volume_m3']=1.6866539158659102e-05
            elif mutation=='type':changed['native_source_mapping'][0]['native_id']=90.
            with self.subTest(mutation=mutation),self.assertRaises(RuntimeError):compare_corner_persistence(before,changed,source_volumes={9078:volume})
        self.assertTrue(compare_corner_persistence(before['observation']['occurrences'],after['observation']['occurrences'],source_volumes={9078:volume},semantic_occurrences=True)['passed'])

    def test_final_hash_gate_rejects_source_and_asset_drift(self):
        path=Path(__file__).resolve().parents[3]/'scripts'/'accept_corner410429_poc.py'
        spec=importlib.util.spec_from_file_location('corner_acceptance_test',path);runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            source=Path(directory)/'source.ics';asset=Path(directory)/'asset.ics'
            source.write_bytes(b'source');asset.write_bytes(b'asset')
            original=runner.file_sha256(source);pins={str(asset):runner.file_sha256(asset)}
            runner.assert_final_hashes(source,original,pins)
            source.write_bytes(b'changed')
            with self.assertRaises(RuntimeError):runner.assert_final_hashes(source,original,pins)
            source.write_bytes(b'source');asset.write_bytes(b'changed')
            with self.assertRaises(RuntimeError):runner.assert_final_hashes(source,original,pins)

    def test_guard_detects_focus_or_active_document_drift_without_restoring(self):
        for field in ('foreground_hwnd','active_path','active_guid','active_modified'):
            state=dict(foreground_hwnd=1,active_path='user.ics',active_guid='g',active_modified=True)
            events=[];guard=BackgroundGuard(lambda:copy.deepcopy(state),lambda *row:events.append(row))
            def action():state[field]='changed'
            with self.assertRaises(RuntimeError):guard.run('operation',action)
            self.assertEqual(state[field],'changed')
            self.assertEqual([x[1] for x in events],['before','after'])

    def test_guard_records_unknown_native_failure_and_leaves_state_alone(self):
        state=dict(foreground_hwnd=1,active_path='user.ics');events=[]
        guard=BackgroundGuard(lambda:copy.deepcopy(state),lambda *row:events.append(row))
        def fail():raise OSError('native failure')
        with self.assertRaises(OSError):guard.run('operation',fail)
        self.assertEqual([x[1] for x in events],['before','after'])
        self.assertEqual(state,dict(foreground_hwnd=1,active_path='user.ics'))

    def test_ten_panels_are_generated_from_dimensions_not_a_preset(self):
        frame=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[558,896,-1503,1]]
        a=panel_occurrences([914,602,352],frame)
        b=panel_occurrences([1037,683,397],frame)
        self.assertEqual(len(a),10);self.assertEqual(len({p['id'] for p in a}),10)
        self.assertEqual([p['id'] for p in a],[p['id'] for p in b])
        roof=next(p for p in b if p['id']=='panels-roof/1')
        self.assertEqual(roof['local_bounds'],[[0,0,0],[1037,683,9.8]])
        self.assertAlmostEqual(roof['native_matrix_mm'][3][2],-1503+397-9.8)
        self.assertEqual(panel_occurrences([914,602,352],frame),a)
        for size in ([True,602,352],[914,float('nan'),352],[914,602,99]):
            with self.assertRaises(ValueError):panel_occurrences(size,frame)
        for field in ('thickness','lid_height'):
            for value in (True,float('nan'),float('inf'),0,-1):
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):panel_occurrences([914,602,352],frame,**{field:value})

if __name__=='__main__':unittest.main()
