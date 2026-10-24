"""Saved-export and fresh datum guards; synthetic inputs only."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.mount_capture import validate_export,prepare_pair_plans
from test_catalog_assets import make_fixture,SOURCE_WORLD
import json

class MountCaptureTests(unittest.TestCase):
    def setUp(self):
        bundle,self.trusted=make_fixture()
        self.face=json.loads(bundle['face_evidence'])
        self.binding=dict(schema_version=1,source_path='synthetic.ics',source_sha256='1'*64,
            source_guid='source-guid',node_id=100,node_name='H7159',expected_world_matrix_mm=SOURCE_WORLD)
        self.receipt=dict(passed=True,production_approved=False,source_unchanged=True,
            source_binding=self.binding,asset_sha256='3'*64,physical_occurrences=13,
            source=dict(disk_equivalence='saved_document',live_document=dict(modified=False,file_guid='source-guid'),
                        sha256_before='1'*64,sha256_after='1'*64),
            stages={k:'PASS' for k in ('source_capture','native_catalog_export_import','rigid_move','body_topology_volume','save_reopen')})
    def test_exact_saved_export_is_detached(self):
        result=validate_export(self.receipt,self.binding,'3'*64)
        result['source_binding']['node_id']=200
        self.assertEqual(self.binding['node_id'],100)
    def test_source_asset_identity_and_approval_drift_are_refused(self):
        for change in ('asset','node','dirty','guid','unproven','incomplete','production'):
            with self.subTest(change=change):
                r=copy.deepcopy(self.receipt)
                if change=='asset':r['asset_sha256']='4'*64
                if change=='node':r['source_binding']['node_id']=200
                if change=='dirty':r['source']['live_document']['modified']=True
                if change=='guid':r['source']['live_document']['file_guid']='other-guid'
                if change=='unproven':r['source']['disk_equivalence']='not_proven'
                if change=='incomplete':r['stages']['save_reopen']='NOT RUN'
                if change=='production':r['production_approved']=True
                with self.assertRaises(ValueError):validate_export(r,self.binding,'3'*64)
    def test_fresh_flange_generates_symmetric_return_without_approval(self):
        before=copy.deepcopy(self.face)
        datum,plans=prepare_pair_plans(self.face,self.binding,'3'*64,'asset-guid')
        self.assertEqual(self.face,before)
        self.assertEqual(plans[0]['plan'],plans[2]['plan'])
        self.assertFalse(datum['mounting_approved'])
        self.assertNotEqual(plans[0]['plan']['handles'],plans[1]['plan']['handles'])
    def test_reversed_exterior_or_wrong_asset_cannot_supply_datum(self):
        for change in ('sign','hash'):
            f=copy.deepcopy(self.face)
            if change=='sign':f['planar_faces_parallel_local_xz'][1]['is_reversed']=True
            else:f['asset_hash']='4'*64
            with self.assertRaises(ValueError):prepare_pair_plans(f,self.binding,'3'*64,'asset-guid')

if __name__=='__main__':unittest.main()
