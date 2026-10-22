"""Synthetic report inputs and RED/GREEN tests; no client evidence in Git."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case import catalog_assets as api
from rockpro_cad.core_case.manifest import build_manifest


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


IDENTITY = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
SOURCE_WORLD = [[0, -1, 0, 0], [-1, 0, 0, 0], [0, 0, -1, 0], [558, 1350, -1377, 1]]


def make_fixture():
    original, capture, exported = '1'*64, '2'*64, '3'*64
    source_doc = dict(file_guid='original-guid', modified=False, document_path='private-source.ics', connection='fixture')
    capture_doc = dict(source_doc, file_guid='capture-guid')
    asset_doc = dict(source_doc, file_guid='asset-guid', document_path='private-asset.ics')
    signature = [dict(occurrence_path=[], kind='assembly', name='H7159', matrix_parent_mm=copy.deepcopy(SOURCE_WORLD))]
    rows = [dict(occurrence_path=[], id=1, name='Scene', kind='scene', children=1, errors=[]),
            dict(occurrence_path=[0], id=100, name='H7159', kind='assembly', children=13, errors=[])]
    for index in range(13):
        bbox = [-80.5, -10.35, -53.5, 80.5, 2.4, 53.5] if index == 0 else [-2, -2, -2, 2, 2, 2]
        matrix = copy.deepcopy(IDENTITY)
        if index == 2:
            matrix[0][0] = -1  # An observed, opaque internal mirror is preserved.
        signature.append(dict(occurrence_path=[index], kind='part', name='Synthetic part '+str(index),
             matrix_parent_mm=matrix, local_bounds_mm=bbox, volume_m3=.000001+index*.00000001,
             volume_requested_accuracy=.001, volume_achieved_accuracy=0., faces=6, edges=12, vertices=8, lumps=1))
        rows.append(dict(occurrence_path=[0, index], id=200+index, name='Synthetic part '+str(index), kind='part',
             children=0, errors=[], bounding_box=dict(valid=True, unit='mm', frame='part_local',
             minimum=bbox[:3], maximum=bbox[3:], size=[bbox[i+3]-bbox[i] for i in range(3)])))
    inventory = dict(schema_version=1, scope='assembly_part_hierarchy', partial=False, errors=[], limit_reasons=[],
                     rows=rows, source=dict(sha256_before=original, sha256_after=original, unchanged=True),
                     cad_document=dict(before=source_doc, after=copy.deepcopy(source_doc), disk_equivalence='saved_document'))
    chain = dict(original_hash_before=original, original_hash_after=original, original_live_before=source_doc,
                 original_live_after=copy.deepcopy(source_doc), input_capture_sha256=capture,
                 relation='input capture created by original live-memory SaveAsCopy; original not edited')
    catalog = dict(schema_version=1, passed=True, production_approved=False, source_unchanged=True,
                   asset_sha256=exported, source_body_signature=copy.deepcopy(signature), body_signature=copy.deepcopy(signature),
                   source_binding=dict(schema_version=1, source_sha256=capture, source_guid='capture-guid', node_id=100,
                      node_name='H7159', expected_world_matrix_mm=copy.deepcopy(SOURCE_WORLD)),
                   source=dict(sha256_before=capture, sha256_after=capture, unchanged=True, live_document=capture_doc),
                   stages={k:'PASS' for k in ('source_capture','native_catalog_export_import','rigid_move','body_topology_volume','save_reopen')})
    faces = []
    for face_id, y, reversed_ in ((194, 0., True), (353, 1.2, False)):
        faces.append(dict(face_id=face_id, point_mm=[0., y, 0.], normal=[0., 1., 0.], is_reversed=reversed_,
            vertex_ids=list(range(face_id, face_id+4)), vertices_mm=[[-80.5,y,-53.5],[80.5,y,-53.5],[80.5,y,53.5],[-80.5,y,53.5]]))
    face_evidence = dict(asset_hash=exported, document=asset_doc, asset_signature=copy.deepcopy(signature),
                         planar_faces_parallel_local_xz=faces)
    candidate = dict(schema_version=1, asset_sha256=exported, asset_guid='asset-guid', sku='H7159', mounting_approved=False,
        scope='candidate measured flange datum; no cutout or strength approval', origin_mm=[0.,0.,0.],
        outward=[0.,1.,0.], up=[0.,0.,-1.], source_world_matrix_mm=copy.deepcopy(SOURCE_WORLD))
    for name, face in zip(('contact_face','exterior_face'), faces):
        f=copy.deepcopy(face);f['oriented_normal']=[v*(-1 if f['is_reversed'] else 1) for v in f['normal']]
        f['witness_bounds_mm']=[min(v[i] for v in f['vertices_mm']) for i in range(3)]+[max(v[i] for v in f['vertices_mm']) for i in range(3)]
        candidate[name]=f
    prepared = dict(schema_version=1, native_requested=True, source_sha256='4'*64, asset_sha256=exported,
                    face_evidence_sha256=digest(encode(face_evidence)), catalog_receipt_sha256=digest(encode(catalog)),
                    plans=[dict(id='A-base', plan=dict(datum=copy.deepcopy(candidate)))])
    poc = dict(schema_version=1, passed=True, operation_id='A-base', production_approved=False, mounting_approved=False,
               asset_sha256=exported, asset_document_before=asset_doc, asset_document_after=copy.deepcopy(asset_doc),
               source_sha256_before='4'*64, source_sha256_after='4'*64, source_body_signature=copy.deepcopy(signature),
               fresh_native_asset_datum=[], plan=dict(datum=copy.deepcopy(candidate)),
               before_save=dict(passed=True, physical_parts=37, proxy_parts=11, real_catalog_parts=26, catalog_assemblies=2),
               after_reopen=dict(passed=True, physical_parts=37, proxy_parts=11, real_catalog_parts=26, catalog_assemblies=2))
    bundle = {k:encode(v) for k,v in dict(inventory=inventory, source_chain=chain, catalog_receipt=catalog,
                                       face_evidence=face_evidence, poc_receipt=poc, prepared_plans=prepared).items()}
    trusted = dict(schema_version=1, definition_id='catalog/H7159', definition_revision=1,
        source_inventory_sha256=digest(bundle['inventory']), original_source_sha256=original,
        original_source_guid='original-guid', source_subtree=[0], source_node_id=100,
        captured_source_sha256=capture, captured_source_guid='capture-guid', asset_sha256=exported, asset_guid='asset-guid',
        report_sha256={k:digest(v) for k,v in bundle.items()})
    return bundle, trusted


def case_request(size=None):
    return dict(schema_version=1, units='mm', frame='case.closed', size=[900,600,330] if size is None else size,
                thickness=9., lid_height=80., edge_inset_mm=100., count=2)


class CatalogAssetTests(unittest.TestCase):
    def call(self, function, *args):
        try:
            return function(*args)
        except NotImplementedError as exc:
            self.fail(str(exc))

    def asset(self):
        return self.call(api.import_candidate, *make_fixture())

    def test_deterministic_detached_candidate_and_revision_hash(self):
        bundle, trusted=make_fixture();before=copy.deepcopy((bundle,trusted))
        asset=self.call(api.import_candidate,bundle,trusted)
        self.assertEqual((bundle,trusted),before)
        self.assertEqual(asset,self.call(api.import_candidate,bundle,trusted))
        self.assertEqual(asset['definition_id'],'catalog/H7159');self.assertEqual(asset['definition_revision'],1)
        self.assertEqual(asset['sku'],'H7159');self.assertEqual(asset['geometry_policy'],'rigid')
        self.assertIs(asset['production_approved'],False);self.assertIs(asset['mounting_approved'],False)
        self.assertEqual(asset['stage'],'measured_candidate')
        payload={k:v for k,v in asset.items() if k!='content_sha256'}
        self.assertEqual(asset['content_sha256'],digest(encode(payload)))
        self.assertNotIn('private-source',json.dumps(asset));self.assertNotIn('Synthetic part',json.dumps(asset))
        revised=dict(trusted,definition_revision=2)
        self.assertNotEqual(asset['content_sha256'],self.call(api.import_candidate,bundle,revised)['content_sha256'])

    def test_all_thirteen_components_and_root_pose_separate(self):
        asset=self.asset();signature=asset['geometry_signature']
        self.assertEqual(sum(r['kind']=='part' for r in signature),13)
        self.assertEqual(sum(r['kind']=='assembly' for r in signature),1)
        self.assertNotIn('matrix_parent_mm',signature[0])
        self.assertEqual(asset['root_poses']['captured_source_world_mm'],SOURCE_WORLD)
        self.assertEqual(asset['geometry_signature_sha256'],digest(encode(signature)))
        mirrored=next(r for r in signature if r['occurrence_path']==[2])
        self.assertEqual(mirrored['matrix_parent_mm'][0][0],-1)

    def test_reject_byte_hash_drift_and_missing_trust(self):
        bundle,trusted=make_fixture();bundle['face_evidence']+=b' '
        with self.assertRaises(ValueError):self.call(api.import_candidate,bundle,trusted)
        bundle,trusted=make_fixture();trusted.pop('asset_guid')
        with self.assertRaises(ValueError):self.call(api.import_candidate,bundle,trusted)

    def test_reject_duplicate_json_keys_and_unknown_report_field(self):
        for duplicate in (False,True):
            bundle,trusted=make_fixture()
            bundle['face_evidence']=(bundle['face_evidence'][:-1]+b',"unknown_exec":"x"}' if not duplicate
                                      else bundle['face_evidence'][:-1]+b',"asset_hash":"'+b'3'*64+b'"}')
            trusted['report_sha256']['face_evidence']=digest(bundle['face_evidence'])
            with self.assertRaises(ValueError):self.call(api.import_candidate,bundle,trusted)

    def test_semantic_drift_rejected_even_when_caller_rehashes_changed_report(self):
        for mutation in ('missing_part','duplicate_path','matrix_drift','wrong_guid','changed_inventory_node','wrong_face','approved'):
            bundle,trusted=make_fixture();report=json.loads(bundle['poc_receipt'])
            if mutation=='missing_part':report['source_body_signature'].pop()
            elif mutation=='duplicate_path':report['source_body_signature'][2]['occurrence_path']=[0]
            elif mutation=='matrix_drift':report['source_body_signature'][2]['matrix_parent_mm'][3][0]=30
            elif mutation=='wrong_guid':report['asset_document_before']['file_guid']='other'
            elif mutation=='changed_inventory_node':
                trusted['source_node_id']=999
            elif mutation=='wrong_face':report['plan']['datum']['origin_mm'][0]=1000
            elif mutation=='approved':report['production_approved']=True
            bundle['poc_receipt']=encode(report);trusted['report_sha256']['poc_receipt']=digest(bundle['poc_receipt'])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.call(api.import_candidate,bundle,trusted)

    def test_asset_hash_content_and_flags_fail_closed(self):
        for field,value in (('definition_revision',True),('schema_version',2),('units','m'),('frame','unknown'),('production_approved',True)):
            asset=self.asset();asset[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.call(api.validate_asset,asset)

    def test_part_modeling_features_are_not_assembly_occurrences(self):
        bundle,trusted=make_fixture();inventory=json.loads(bundle['inventory'])
        for row in inventory['rows']:
            if row['kind']=='part':
                row['children']=None;row['children_scope']='not_traversed_modeling_features'
        bundle['inventory']=encode(inventory)
        trusted['report_sha256']['inventory']=trusted['source_inventory_sha256']=digest(bundle['inventory'])
        asset=self.call(api.import_candidate,bundle,trusted)
        self.assertEqual(sum(r['kind']=='part' for r in asset['geometry_signature']),13)

    def test_pair_coordinates_are_independently_derived_and_stable_after_resize(self):
        asset=self.asset();baseline=self.call(api.plan_candidate_pair,asset,case_request())
        baseline_ids=[p['id'] for p in baseline['occurrences']]
        for size in ([900,600,330],[1100,600,330],[900,720,330],[900,600,410],[1100,720,410],[900,600,330]):
            plan=self.call(api.plan_candidate_pair,asset,case_request(size));self.assertEqual(plan['status'],'planned')
            self.assertEqual([p['id'] for p in plan['occurrences']],baseline_ids)
            expected=[[-(size[0]/2-100-80.5),-size[1]/2,(size[2]-80)/2],
                      [size[0]/2-100-80.5,-size[1]/2,(size[2]-80)/2]]
            for row,wanted in zip(plan['occurrences'],expected):
                self.assertEqual(row['anchor_mm'],wanted);self.assertEqual(row['matrix_mm'][:3],[[1,0,0,0],[0,-1,0,0],[0,0,-1,0]])
                self.assertEqual(row['matrix_mm'][3],wanted+[1]);self.assertEqual(row['definition_revision'],1)
            self.assertFalse(plan['production_approved']);self.assertFalse(plan['mounting_approved'])
        self.assertEqual(self.call(api.plan_candidate_pair,asset,case_request()),baseline)

    def test_pair_invalid_inputs_are_blocked_without_changes(self):
        asset=self.asset()
        # This preview covers the hardware wall only, without a product/device.
        for field,value in (('count',1),('count',True),('units','m'),('frame','rear'),('edge_inset_mm',-1),('size',[900,17,330]),('size',[True,600,330]),('size',[900,float('nan'),330])):
            request=case_request();request[field]=value
            result=self.call(api.plan_candidate_pair,asset,request)
            self.assertEqual(result['status'],'blocked');self.assertEqual(result['changes'],[])

    def test_sidecar_only_links_exact_source_root_without_changing_inventory_draft(self):
        bundle,trusted=make_fixture();asset=self.call(api.import_candidate,bundle,trusted)
        inventory=json.loads(bundle['inventory']);manifest=build_manifest(inventory,inventory_sha256=digest(bundle['inventory']))
        selected=next(x['rockpro_id'] for x in manifest['occurrences'] if x['source_ref']['occurrence_path']==[0])
        before=copy.deepcopy(manifest)
        sidecar=self.call(api.build_manifest_sidecar,manifest,asset,[selected])
        self.assertEqual(manifest,before);self.assertEqual(manifest['manifest_stage'],'inventory_draft')
        self.assertFalse(manifest['runtime_template_compatible']);self.assertFalse(sidecar['production_approved'])
        self.assertEqual(sidecar['links'][0]['source_occurrence_id'],selected)
        child=next(x['rockpro_id'] for x in manifest['occurrences'] if x['source_ref']['occurrence_path']==[0,0])
        with self.assertRaises(ValueError):self.call(api.build_manifest_sidecar,manifest,asset,[child])


if __name__=='__main__':unittest.main()
