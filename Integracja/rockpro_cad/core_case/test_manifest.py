"""Synthetic ROC-42 accounting, identity and refusal regressions; no CAD."""
import copy
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rockpro_cad.core_case.manifest import (
    build_manifest, validate_manifest, write_manifest_exclusive, read_manifest, main,
)


def inventory():
    rows = []
    for path, name, kind, children in [([], '', 'scene', 2),
            ([0], 'góra', 'assembly', 3), ([0, 0], '2643', 'assembly', 0),
            ([0, 1], '17251S_1', 'assembly', 1), ([0, 1, 0], 'half', 'part', None),
            ([0, 2], 'Część2648', 'part', None),
            ([1], 'dół', 'assembly', 2), ([1, 0], '17251S', 'part', None),
            ([1, 1], 'koła', 'assembly', 1), ([1, 1, 0], 'wheel', 'part', None)]:
        row = dict(occurrence_path=path, name=name, kind=kind, children=children,
                   id=len(rows)+1, material_cad_raw='Aluminium', errors=[])
        if kind == 'part':
            row.update(bounding_box=dict(valid=True, unit='mm', frame='part_local',
                minimum=[0, 0, 0], maximum=[10, 20, 30], size=[10, 20, 30]))
        rows.append(row)
    return dict(schema_version=1, scope='assembly_part_hierarchy', rows=rows,
        limit_reasons=[], partial=False, read_only=True, source=dict(path='synthetic.ics',
        sha256_before='a'*64, sha256_after='a'*64, unchanged=True),
        cad_document=dict(before=dict(file_guid='synthetic', modified=False),
                          after=dict(file_guid='synthetic', modified=False), disk_equivalence='proven'))


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.inventory = inventory()
        self.manifest = build_manifest(self.inventory)

    def codes(self, manifest=None, **kw):
        return {d.code for d in validate_manifest(manifest or self.manifest, **kw).diagnostics}

    def test_every_node_accounted_but_no_purchase_quantity(self):
        self.assertEqual(len(self.manifest['occurrences']), len(self.inventory['rows']))
        result = validate_manifest(self.manifest, self.inventory)
        self.assertTrue(result.valid, result.as_dict())
        self.assertFalse(result.production_ready)
        empty = next(o for o in self.manifest['occurrences'] if o['source_ref']['occurrence_path'] == [0, 0])
        self.assertEqual(empty['classification'], 'empty')
        self.assertFalse(empty['physical_quantity_approved'])
        self.assertEqual(empty['policy'], 'exclude_explicit')
        self.assertIn('UNRESOLVED_PART', self.codes())
        self.assertIn('SYMMETRY_PENDING', self.codes())
        self.assertIn('PAIRING_PENDING', self.codes())

    def test_ids_reused_only_from_persisted_source_bound_map(self):
        repeated = build_manifest(self.inventory, identity_map=self.manifest['identity_map'])
        self.assertEqual(repeated, self.manifest)
        fresh = build_manifest(self.inventory)
        self.assertNotEqual(fresh['occurrences'][0]['rockpro_id'], self.manifest['occurrences'][0]['rockpro_id'])
        changed = copy.deepcopy(self.inventory)
        changed['rows'][0]['id'] = 555
        with self.assertRaises(ValueError):
            build_manifest(changed, identity_map=self.manifest['identity_map'])
        incomplete = copy.deepcopy(self.manifest['identity_map'])
        incomplete['ids'].pop('occurrence:root')
        with self.assertRaises(ValueError):
            build_manifest(self.inventory, identity_map=incomplete)

    def test_invalid_bbox_is_not_validated_geometry(self):
        self.inventory['rows'][4]['bounding_box']['valid'] = False
        manifest = build_manifest(self.inventory)
        self.assertIn('INVALID_BOUNDING_BOX', self.codes(manifest))
        self.inventory['rows'][4]['bounding_box']['valid'] = True
        self.inventory['rows'][4]['bounding_box']['size'] = [0, 20, 30]
        manifest = build_manifest(self.inventory)
        self.assertIn('INVALID_BOUNDING_BOX', self.codes(manifest))

    def test_duplicate_node_and_ids_refused(self):
        self.inventory['rows'].append(copy.deepcopy(self.inventory['rows'][0]))
        with self.assertRaises(ValueError):
            build_manifest(self.inventory)
        self.manifest['occurrences'][1]['rockpro_id'] = self.manifest['occurrences'][0]['rockpro_id']
        self.assertIn('DUPLICATE_ID', self.codes())

    def test_missing_node_and_empty_manifest_refused(self):
        self.manifest['occurrences'].pop()
        self.assertIn('INVENTORY_COVERAGE', self.codes(inventory=self.inventory))
        self.assertFalse(validate_manifest({}).valid)

    def test_missing_group_or_membership_refused(self):
        original = copy.deepcopy(self.manifest)
        self.manifest['symmetry_groups'].pop()
        self.assertIn('SYMMETRY_GROUP_MISSING', self.codes())
        self.manifest = original
        self.manifest['symmetry_groups'][0]['members'] = []
        self.assertIn('GROUP_MEMBERSHIP', self.codes())

    def test_pair_group_missing_and_approval_tampering_refused(self):
        self.manifest['pairings'][0]['group_ids'].append('missing')
        self.assertIn('PAIRING_MEMBER_MISSING', self.codes())
        self.manifest['production_approved'] = True
        self.assertIn('FALSE_PRODUCTION_APPROVAL', self.codes())

    def test_geometry_and_purchase_material_do_not_follow_name_or_cad_material(self):
        self.assertTrue(all(d['purchase_material'] is None for d in self.manifest['definitions']))
        self.assertTrue(all(d['approved_for_automatic_placement'] is False for d in self.manifest['definitions']))
        self.assertTrue(all(o['world_transform']['status'] == 'not_available' for o in self.manifest['occurrences']))

    def test_unknown_and_wheel_import_remain_blockers(self):
        self.assertIn('WHEEL_SKU_UNRESOLVED', self.codes())
        self.assertTrue(any(o['semantic_role'] == 'unresolved_custom' for o in self.manifest['occurrences']))

    def test_io_is_exclusive_and_roundtrips(self):
        artifact_root = Path(__file__).resolve().parents[3]/'artifacts'
        artifact_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=artifact_root) as directory:
            target = Path(directory)/'manifest.json'
            write_manifest_exclusive(target, self.manifest)
            self.assertEqual(read_manifest(target), self.manifest)
            with self.assertRaises(FileExistsError):
                write_manifest_exclusive(target, self.manifest)

    def test_child_components_are_not_independent_purchase_items(self):
        component = next(o for o in self.manifest['occurrences'] if o['source_ref']['occurrence_path'] == [0, 1, 0])
        owner = next(o for o in self.manifest['occurrences'] if o['source_ref']['occurrence_path'] == [0, 1])
        self.assertEqual(component['source_group_owner_id'], owner['rockpro_id'])
        self.assertEqual(component['inventory_function'], 'geometry_component')
        self.assertIsNone(component['purchase_quantity'])

    def test_cli_manifest_reloads_against_unmodified_inventory(self):
        artifact_root = Path(__file__).resolve().parents[3]/'artifacts'
        artifact_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=artifact_root) as directory:
            source, target = Path(directory)/'inventory.json', Path(directory)/'manifest.json'
            source.write_text(json.dumps(self.inventory, ensure_ascii=False, indent=2), encoding='utf-8')
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(['--inventory', str(source), '--output', str(target)])
            self.assertEqual(result, 2)
            reported = json.loads(stdout.getvalue())
            loaded = read_manifest(target)
            raw = source.read_bytes()
            revalidated = validate_manifest(loaded, json.loads(raw.decode('utf-8')))
            self.assertEqual(reported, revalidated.as_dict())
            self.assertTrue(revalidated.valid, revalidated.as_dict())
            self.assertEqual(loaded['inventory_file_sha256'], hashlib.sha256(raw).hexdigest())

    def test_parent_graph_and_child_counts_are_checked(self):
        self.manifest['occurrences'][4]['parent_id'] = self.manifest['occurrences'][0]['rockpro_id']
        self.assertIn('PARENT_GRAPH_INVALID', self.codes())
        self.manifest['occurrences'][3]['source_ref']['children'] = 999
        self.assertIn('CHILD_COUNT_MISMATCH', self.codes())

    def test_source_partial_modified_and_binding_mismatch_block(self):
        self.inventory['partial'] = True
        self.inventory['cad_document']['before']['modified'] = True
        candidate = build_manifest(self.inventory)
        self.assertIn('SOURCE_INVENTORY_PARTIAL', self.codes(candidate))
        self.assertIn('SOURCE_DOCUMENT_MODIFIED', self.codes(candidate))
        changed = copy.deepcopy(self.inventory)
        changed['source']['sha256_before'] = 'b'*64
        self.assertIn('SOURCE_BINDING_MISMATCH', self.codes(candidate, inventory=changed))

    def test_malformed_nested_data_returns_diagnostic_without_crash(self):
        for field, value in [('source_ref', None), ('rockpro_id', []), ('world_transform', 5)]:
            candidate = copy.deepcopy(self.manifest)
            candidate['occurrences'][0][field] = value
            self.assertFalse(validate_manifest(candidate).valid)

    def test_identity_tampering_and_approval_stage_fail_closed(self):
        self.manifest['occurrences'][0]['rockpro_id'] = 'index-0'
        self.assertIn('IDENTITY_MAP_MISMATCH', self.codes())
        self.assertIn('MOUNTING_EVIDENCE_NOT_IMPLEMENTED', self.codes())

    def test_source_provenance_cannot_be_changed_even_if_map_is_copied(self):
        self.manifest['source_binding']['source']['sha256_before'] = 'b'*64
        self.manifest['source_binding']['source']['sha256_after'] = 'b'*64
        self.manifest['identity_map']['source_binding'] = copy.deepcopy(self.manifest['source_binding'])
        self.assertIn('SOURCE_BINDING_MISMATCH', self.codes(inventory=self.inventory))

    def test_classification_cannot_exclude_physical_source_or_count_assembly(self):
        self.manifest['occurrences'][4].update(classification='empty', policy='exclude_explicit')
        self.assertIn('INVALID_SOURCE_CLASSIFICATION', self.codes())
        self.manifest['occurrences'][1].update(classification='physical', policy='rigid_move')
        self.assertIn('INVALID_SOURCE_CLASSIFICATION', self.codes())

    def test_pairing_set_roles_and_extra_definition_fail(self):
        for field, value in [('group_ids', []), ('required_roles', ['invented'])]:
            candidate = copy.deepcopy(self.manifest)
            candidate['pairings'][0][field] = value
            self.assertIn('PAIRING_MEMBERSHIP', self.codes(candidate))
        self.manifest['definitions'].append(dict(definition_id='unreferenced'))
        self.assertIn('DEFINITION_MEMBERSHIP', self.codes())

    def test_schema_must_be_integer_and_frame_cannot_claim_approval(self):
        for version in (True, 1.0):
            candidate = copy.deepcopy(self.manifest)
            candidate['schema_version'] = version
            self.assertFalse(validate_manifest(candidate).valid)
        self.manifest['frames'][0].update(status='approved', rotation=[[-1,0,0],[0,1,0],[0,0,1]])
        self.assertIn('UNSUPPORTED_FRAME_CLAIM', self.codes())


if __name__ == '__main__':
    unittest.main()
