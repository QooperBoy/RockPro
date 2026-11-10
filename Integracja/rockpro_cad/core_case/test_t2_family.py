import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.t2_family import (
    FAMILY, JOINTS, blockers, draft_from_reference, draft_with_source_frames, validate_t2_family)
from rockpro_cad.core_case.contracts import ValidationError


def fixture():
    roles = dict(base=(1, [1]), hood=(2, [2]), front_cap=(3, [3]), rack=(4, [2, 4]))
    components = {role: dict(source_node_id=node, cad_path=path, frame=None,
        motion='fixed' if role == 'base' else 'independent_removable')
        for role, (node, path) in roles.items()}
    joints = {}
    next_id = 100
    for key, (a, b, count) in JOINTS.items():
        pairs = []
        for _ in range(count):
            pairs.append({a: next_id, b: next_id + 1}); next_id += 2
        joints[key] = dict(members=[a, b], kind='removable', frame=None,
                           clearance_mm=None, latch_pairs=pairs)
    return dict(schema_version=1, family_id=FAMILY, source_sha256='a' * 64,
                state='reference_draft', components=components, joints=joints,
                device_fit_confirmed=False)


class T2FamilyTests(unittest.TestCase):
    def test_rack_movement_is_independent_despite_hood_parent(self):
        draft = validate_t2_family(fixture())
        rack = draft['components']['rack']
        self.assertEqual(rack['cad_path'], [2, 4])
        self.assertEqual(rack['motion'], 'independent_removable')
        self.assertTrue(all(j['kind'] == 'removable' for j in draft['joints'].values()))

    def test_unknown_clearance_stays_null_and_blocks_build(self):
        source = fixture(); output = validate_t2_family(source)
        self.assertIsNone(output['joints']['base_hood']['clearance_mm'])
        self.assertIn('joint_clearance_missing:base_hood', blockers(output))
        output['joints']['base_hood']['clearance_mm'] = 0
        self.assertIsNone(source['joints']['base_hood']['clearance_mm'])
        self.assertNotIn('joint_clearance_missing:base_hood', blockers(output))
        self.assertIn('native_recipe_not_implemented', blockers(output))

    def test_no_hinge_or_inherited_rack_motion(self):
        for role in ('rack', 'front_cap', 'hood'):
            draft = fixture(); draft['components'][role]['motion'] = 'hinged'
            with self.assertRaises(ValidationError): validate_t2_family(draft)

    def test_joint_pair_distribution_and_identity(self):
        draft = fixture()
        draft['joints']['hood_front_cap']['latch_pairs'].append(
            draft['joints']['base_hood']['latch_pairs'].pop())
        with self.assertRaises(ValidationError): validate_t2_family(draft)
        draft = fixture()
        draft['joints']['base_hood']['latch_pairs'][1]['base'] = 100
        with self.assertRaises(ValidationError): validate_t2_family(draft)

    def test_identity_reuse_bad_paths_and_unknown_fields_rejected(self):
        mutations = [lambda d: d['components']['rack'].update(source_node_id=2, cad_path=[2]),
                     lambda d: d['components']['rack'].update(cad_path=[2, 4, 2]),
                     lambda d: d.update(production_approved=True),
                     lambda d: d.update(device_fit_confirmed=True),
                     lambda d: d.update(source_sha256='unbound')]
        for mutate in mutations:
            draft = fixture(); mutate(draft)
            with self.assertRaises(ValidationError): validate_t2_family(draft)

    def test_clearance_validation_and_frame_orientation(self):
        for invalid in (True, -1, float('nan'), float('inf'), '2', 100):
            draft = fixture(); draft['joints']['base_hood']['clearance_mm'] = invalid
            with self.assertRaises(ValidationError): validate_t2_family(draft)
        draft = fixture()
        draft['components']['base']['frame'] = dict(origin=[0, 0, 0], u=[1, 0, 0], v=[0, 1, 0], n=[0, 0, -1])
        with self.assertRaises(ValidationError): validate_t2_family(draft)

    def test_reference_import_uses_semantic_roots_not_child_names(self):
        source = fixture()
        names = dict(base='structural_base', hood='removable_hood',
                     front_cap='removable_front_cap', rack='removable_rack')
        parts = [dict(source_id=c['source_node_id'], source_path='root/' + '/'.join(map(str, c['cad_path'])),
                      source_type='Z_ELEMENT_ASSEMBLY', role=names[role])
                 for role, c in source['components'].items()]
        parts.append(dict(source_id=5, source_path='root/2/4/5',
                          source_type='Z_ELEMENT_ASSEMBLY', role='removable_rack'))
        pairs = [dict(upper_owner=a, upper_source_id=p[a], lower_owner=b, lower_source_id=p[b])
                 for key, (a, b, _) in JOINTS.items() for p in source['joints'][key]['latch_pairs']]
        reference = dict(schema='rockpro.reference-analysis/1', state='inventory_draft',
                         family_candidate=FAMILY, source_sha256='a' * 64,
                         executable_template=False, production_approved=False,
                         parts=parts, latch_pairs=pairs)
        before = copy.deepcopy(reference)
        self.assertEqual(draft_from_reference(reference), source)
        self.assertEqual(reference, before)
        reference['parts'].append(dict(source_id=6, source_path='root/6',
            source_type='Z_ELEMENT_ASSEMBLY', role='removable_rack'))
        with self.assertRaises(ValidationError): draft_from_reference(reference)


class T2MeasuredFrameTests(unittest.TestCase):
    def setUp(self):
        draft = fixture()
        roles = dict(base='structural_base', hood='removable_hood',
                     front_cap='removable_front_cap', rack='removable_rack')
        parts, rows = [], []
        for role, component in draft['components'].items():
            node = component['source_node_id']
            path = 'root/' + '/'.join(map(str, component['cad_path']))
            parts.append(dict(source_id=node, source_path=path,
                              source_type='Z_ELEMENT_ASSEMBLY', role=roles[role]))
            # Row-vector rotation + translation: translation must not be transposed.
            rows.append(dict(id=node, path=path, type='Z_ELEMENT_ASSEMBLY',
                world_mm=[[0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 1, 0], [10, 20, 30, 1]]))
        pairs = [dict(upper_owner=a, upper_source_id=p[a], lower_owner=b, lower_source_id=p[b])
                 for key, (a, b, _) in JOINTS.items() for p in draft['joints'][key]['latch_pairs']]
        self.reference = dict(schema='rockpro.reference-analysis/1', state='inventory_draft',
            family_candidate=FAMILY, source_sha256='a' * 64, executable_template=False,
            production_approved=False, parts=parts, latch_pairs=pairs)
        self.inventory = dict(source_sha256='a' * 64, rows=rows)

    def encoded(self):
        raw = json.dumps(self.inventory).encode('utf-8')
        self.reference['inventory_sha256'] = hashlib.sha256(raw).hexdigest()
        return raw

    def test_measured_row_vector_frame_keeps_joint_unknown(self):
        raw = self.encoded(); original = copy.deepcopy(self.reference)
        draft = draft_with_source_frames(self.reference, raw)['draft']
        self.assertEqual(draft['components']['rack']['frame'],
                         dict(origin=[10, 20, 30], u=[0, 1, 0], v=[-1, 0, 0], n=[0, 0, 1]))
        self.assertEqual(draft['components']['rack']['cad_path'], [2, 4])
        self.assertFalse(any(b.startswith('component_frame_missing:') for b in blockers(draft)))
        self.assertIn('joint_frame_missing:base_hood', blockers(draft))
        self.assertIn('joint_clearance_missing:base_hood', blockers(draft))
        self.assertEqual(self.reference, original)

    def test_tampered_bytes_or_different_model_revision_rejected(self):
        raw = self.encoded()
        with self.assertRaises(ValidationError): draft_with_source_frames(self.reference, raw + b' ')
        self.inventory['source_sha256'] = 'b' * 64
        with self.assertRaises(ValidationError): draft_with_source_frames(self.reference, self.encoded())

    def test_path_id_duplicates_and_non_assembly_are_rejected(self):
        for key, value in (('id', 99), ('path', 'root/99'), ('type', 'Z_ELEMENT_PART')):
            old = self.inventory['rows'][0][key]
            self.inventory['rows'][0][key] = value
            with self.assertRaises(ValidationError): draft_with_source_frames(self.reference, self.encoded())
            self.inventory['rows'][0][key] = old
        self.inventory['rows'].append(copy.deepcopy(self.inventory['rows'][0]))
        with self.assertRaises(ValidationError): draft_with_source_frames(self.reference, self.encoded())

    def test_no_invented_identity_or_normalization_of_bad_frame(self):
        row = self.inventory['rows'][0]
        for matrix in (None,
                       [[2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]):
            row['world_mm'] = matrix
            with self.assertRaises(ValidationError): draft_with_source_frames(self.reference, self.encoded())
        del row['world_mm']
        with self.assertRaises(ValidationError): draft_with_source_frames(self.reference, self.encoded())

    def test_mirrored_source_stays_raw_and_does_not_become_mounting_frame(self):
        matrix = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 0], [10, 20, 30, 1]]
        self.inventory['rows'][0]['world_mm'] = matrix
        result = draft_with_source_frames(self.reference, self.encoded())
        self.assertIsNone(result['draft']['components']['base']['frame'])
        self.assertEqual(result['source_frames']['base']['world_mm'], matrix)
        self.assertIn('component_frame_missing:base', blockers(result['draft']))
        self.assertTrue(result['source_frames']['base']['status'].startswith('mirrored_'))


if __name__ == '__main__': unittest.main()
