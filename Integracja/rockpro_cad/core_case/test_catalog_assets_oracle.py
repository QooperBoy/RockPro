"""Adversarial offline catalog boundary checks, independent of planner goldens.

The shared builder supplies synthetic input reports only. Expected transforms,
hashes, refusal cases and preservation checks are derived here independently.
No user CAD evidence or native adapters are loaded.
"""
import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case import catalog_assets as api
from rockpro_cad.core_case.manifest import build_manifest
from rockpro_cad.core_case.test_catalog_assets import make_fixture


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def request(size=(900, 600, 330)):
    return dict(schema_version=1, units='mm', frame='case.closed', size=list(size),
                thickness=9, lid_height=80, edge_inset_mm=100, count=2)


def reseal(asset):
    asset['content_sha256'] = digest(encoded({k: v for k, v in asset.items()
                                             if k != 'content_sha256'}))
    return asset


def changed_reports(mutator):
    """Rebind caller-supplied hashes so tests reach semantic validation."""
    bundle, trust = make_fixture()
    reports = {k: json.loads(v) for k, v in bundle.items()}
    mutator(reports)
    for name in ('face_evidence', 'catalog_receipt'):
        reports['prepared_plans'][name + '_sha256'] = digest(encoded(reports[name]))
    bundle = {k: encoded(v) for k, v in reports.items()}
    trust['report_sha256'] = {k: digest(v) for k, v in bundle.items()}
    trust['source_inventory_sha256'] = digest(bundle['inventory'])
    return bundle, trust


def signatures(reports):
    return [reports['catalog_receipt']['source_body_signature'],
            reports['catalog_receipt']['body_signature'],
            reports['face_evidence']['asset_signature'],
            reports['poc_receipt']['source_body_signature']]


class CatalogAssetsOracleTests(unittest.TestCase):
    def asset(self):
        return api.import_candidate(*make_fixture())

    def assert_refused(self, function, *args):
        before = copy.deepcopy(args)
        with self.assertRaises(ValueError):
            function(*args)
        self.assertEqual(args, before, 'refusal mutated caller-owned evidence')

    def test_roundtrip_detachment_and_canonical_content_hash(self):
        bundle, trust = make_fixture()
        before = copy.deepcopy((bundle, trust))
        first = api.import_candidate(bundle, trust)
        self.assertEqual(first, api.import_candidate(bundle, trust))
        self.assertEqual(first, api.validate_asset(json.loads(encoded(first))))
        self.assertEqual(first['content_sha256'], digest(encoded(
            {k: v for k, v in first.items() if k != 'content_sha256'})))
        first['geometry_signature'][1]['local_bounds_mm'][0] -= 9
        self.assertEqual((bundle, trust), before)
        self.assertNotEqual(first, api.import_candidate(bundle, trust))

    def test_module_import_does_not_require_native_or_com_modules(self):
        script = """
import builtins, sys
sys.path.insert(0, sys.argv[1])
original = builtins.__import__
def guarded(name, *args, **kwargs):
    forbidden = ('comtypes', 'pythoncom', 'win32com', 'ironcad',
                 'rockpro_cad.core_case.native', 'rockpro_cad.parts.native')
    if name.split('.')[-1] in ('native', 'native_reader', 'hardware_poc_native', 'catalog_native') or any(
           name == p or name.startswith(p + '.') or
           (p.endswith('.native') and name.startswith(p + '_')) for p in forbidden):
        raise AssertionError('native dependency imported: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from rockpro_cad.core_case import catalog_assets
"""
        result = subprocess.run([sys.executable, '-B', '-c', script,
                                 str(Path(__file__).resolve().parents[2])],
                                capture_output=True, text=True, timeout=15,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_every_report_is_bound_independently(self):
        for name in make_fixture()[0]:
            with self.subTest(report=name):
                bundle, trust = make_fixture()
                bundle[name] += b' '
                self.assert_refused(api.import_candidate, bundle, trust)

    def test_trust_numeric_and_identity_fields_do_not_coerce(self):
        mutations = [('schema_version', True), ('definition_revision', True),
                     ('source_node_id', True), ('source_subtree', [False]),
                     ('asset_guid', 'another-guid'), ('original_source_guid', 'another-guid'),
                     ('captured_source_guid', 'another-guid'), ('asset_sha256', 'A' * 64),
                     ('definition_revision', 0)]
        for name, value in mutations:
            with self.subTest(field=name, value=value):
                bundle, trust = make_fixture()
                trust[name] = value
                self.assert_refused(api.import_candidate, bundle, trust)

    def test_consistently_missing_duplicate_or_orphan_body_is_not_valid_asset(self):
        for mode in ('missing', 'duplicate', 'orphan'):
            def mutate(reports):
                for signature in signatures(reports):
                    if mode == 'missing':
                        signature.pop()
                    elif mode == 'duplicate':
                        signature[-1]['occurrence_path'] = [0]
                    else:
                        signature[-1]['occurrence_path'] = [99, 0]
            with self.subTest(mode=mode):
                self.assert_refused(api.import_candidate, *changed_reports(mutate))

    def test_nonpositive_geometry_and_nonrigid_internal_matrix_rejected(self):
        for field, value in [('volume_m3', 0), ('volume_m3', -1), ('faces', True),
                             ('edges', -1), ('vertices', 0), ('lumps', 0),
                             ('local_bounds_mm', [1, 0, 0, 1, 2, 3])]:
            def mutate(reports):
                for signature in signatures(reports):
                    signature[1][field] = value
            with self.subTest(field=field, value=value):
                self.assert_refused(api.import_candidate, *changed_reports(mutate))
        def scale(reports):
            for signature in signatures(reports):
                signature[2]['matrix_parent_mm'][0][0] = 1.01
        self.assert_refused(api.import_candidate, *changed_reports(scale))

    def test_internal_source_reflection_preserved_but_new_roots_are_proper(self):
        asset = self.asset()
        mirrored = next(r for r in asset['geometry_signature'] if r['occurrence_path'] == [2])
        self.assertEqual(mirrored['matrix_parent_mm'][0][0], -1)
        plan = api.plan_candidate_pair(asset, request())
        for row in plan['occurrences']:
            m = row['matrix_mm']
            det = sum(m[0][i] * (m[1][(i+1)%3] * m[2][(i+2)%3]
                                - m[1][(i+2)%3] * m[2][(i+1)%3]) for i in range(3))
            self.assertAlmostEqual(det, 1)

    def test_resealed_contract_cannot_self_promote_or_change_frame(self):
        for name, value in [('production_approved', True), ('mounting_approved', True),
                            ('stage', 'approved'), ('units', 'm'), ('frame', 'world'),
                            ('geometry_policy', 'scale'), ('schema_version', True)]:
            asset = self.asset()
            asset[name] = value
            with self.subTest(field=name):
                self.assert_refused(api.validate_asset, reseal(asset))

    def test_resealed_candidate_datum_contradictions_fail(self):
        for name, value in [('origin_mm', [123, 0, 0]), ('up', [0, 0, 1]),
                            ('outward', [0, -1, 0]), ('mounting_approved', True)]:
            asset = self.asset()
            asset['mounting_candidate'][name] = value
            with self.subTest(field=name):
                self.assert_refused(api.validate_asset, reseal(asset))

    def test_mounting_component_binding_and_body_containment_are_explicit(self):
        for name, value in [('component_path', [1]), ('component_id', 'catalog/H7159/component/1'),
                            ('component_binding', 'guessed_from_name')]:
            asset = self.asset()
            asset['mounting_candidate'][name] = value
            with self.subTest(field=name):
                self.assert_refused(api.validate_asset, reseal(asset))
        asset = self.asset()
        body = next(r for r in asset['geometry_signature'] if r['occurrence_path'] == [0])
        body['local_bounds_mm'] = [-1, -1, -1, 1, 1, 1]
        asset['geometry_signature_sha256'] = digest(encoded(asset['geometry_signature']))
        self.assert_refused(api.validate_asset, reseal(asset))

    def test_part_local_face_datum_cannot_silently_be_treated_as_root_local(self):
        def moved_datum_body(reports):
            for rows in signatures(reports):
                rows[1]['matrix_parent_mm'][3][0] = 10
        self.assert_refused(api.import_candidate, *changed_reports(moved_datum_body))

    def test_success_and_failure_never_open_report_path_hints(self):
        bundle, trust = make_fixture()
        with patch('builtins.open', side_effect=AssertionError('unexpected file I/O')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('unexpected read')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('unexpected read')):
            asset = api.import_candidate(bundle, trust)
            api.validate_asset(asset)
            self.assertEqual(api.plan_candidate_pair(asset, request())['status'], 'planned')
            trust['asset_guid'] = 'does-not-exist'
            with self.assertRaises(ValueError):
                api.import_candidate(bundle, trust)

    def test_raw_face_witnesses_are_required_not_just_expected_metadata(self):
        for mode in ('noncoplanar', 'collinear', 'duplicate_vertex', 'reversed'):
            def mutate(reports):
                face = reports['face_evidence']['planar_faces_parallel_local_xz'][0]
                if mode == 'noncoplanar':
                    face['vertices_mm'][1][1] = 0.5
                elif mode == 'collinear':
                    face['vertices_mm'] = [[i, 0, i] for i in range(4)]
                elif mode == 'duplicate_vertex':
                    face['vertex_ids'][1] = face['vertex_ids'][0]
                else:
                    face['is_reversed'] = False
            with self.subTest(mode=mode):
                self.assert_refused(api.import_candidate, *changed_reports(mutate))

    def test_malformed_nested_reports_fail_with_contract_error(self):
        for report, key, value in [('catalog_receipt', 'stages', []),
                                   ('face_evidence', 'planar_faces_parallel_local_xz', [0])]:
            def malformed(reports):
                reports[report][key] = value
            with self.subTest(report=report, key=key):
                self.assert_refused(api.import_candidate, *changed_reports(malformed))

    def test_dirty_original_memory_never_becomes_inventory_sidecar_proof(self):
        def dirty(reports):
            for key in ('before', 'after'):
                reports['inventory']['cad_document'][key]['modified'] = True
            for key in ('original_live_before', 'original_live_after'):
                reports['source_chain'][key]['modified'] = True
            reports['inventory']['cad_document']['disk_equivalence'] = 'unproven'
        bundle, trust = changed_reports(dirty)
        asset = api.import_candidate(bundle, trust)
        self.assertIs(asset['production_approved'], False)
        manifest = build_manifest(json.loads(bundle['inventory']),
                                  inventory_sha256=digest(bundle['inventory']))
        selected = next(r['rockpro_id'] for r in manifest['occurrences']
                        if r['source_ref']['occurrence_path'] == [0])
        self.assert_refused(api.build_manifest_sidecar, manifest, asset, [selected])

    def test_clean_original_does_not_hide_dirty_capture(self):
        def dirty_capture(reports):
            reports['catalog_receipt']['source']['live_document']['modified'] = True
        bundle, trust = changed_reports(dirty_capture)
        asset = api.import_candidate(bundle, trust)
        manifest = build_manifest(json.loads(bundle['inventory']),
                                  inventory_sha256=digest(bundle['inventory']))
        selected = next(r['rockpro_id'] for r in manifest['occurrences']
                        if r['source_ref']['occurrence_path'] == [0])
        self.assert_refused(api.build_manifest_sidecar, manifest, asset, [selected])

    def test_dirty_asset_memory_cannot_claim_exported_file_binding(self):
        def dirty_asset(reports):
            reports['face_evidence']['document']['modified'] = True
            for key in ('asset_document_before', 'asset_document_after'):
                reports['poc_receipt'][key]['modified'] = True
        self.assert_refused(api.import_candidate, *changed_reports(dirty_asset))

    def test_cli_only_reads_explicit_inputs_and_refuses_existing_output(self):
        cli = runpy.run_path(str(Path(__file__).resolve().parents[3] /
                                'scripts/import_catalog_asset.py'))['main']
        with tempfile.TemporaryDirectory(prefix='.catalog-oracle-',
                                         dir=Path(__file__).resolve().parents[3]) as directory:
            root = Path(directory)
            trap = root / 'do-not-open-source.ics'
            trap.write_bytes(b'sentinel CAD bytes must never be read or changed')
            def hints(reports):
                reports['source_chain']['original_path'] = str(trap)
                reports['source_chain']['input_capture_path'] = str(trap)
                reports['face_evidence']['asset_path'] = str(trap)
            bundle, trust = changed_reports(hints)
            arguments = []
            allowed_reads = set()
            for name, data in bundle.items():
                path = root / (name + '.json')
                path.write_bytes(data)
                allowed_reads.add(path.resolve())
                arguments += ['--' + name.replace('_', '-'), str(path)]
            binding_path = root / 'bindings.json'
            binding_path.write_bytes(encoded(trust))
            allowed_reads.add(binding_path.resolve())
            output = root / 'new-output'
            arguments += ['--trusted-bindings', str(binding_path), '--output-dir', str(output)]
            original_open = Path.open
            observed = set()
            def guarded_open(path, mode='r', *args, **kwargs):
                if 'r' in mode:
                    resolved = path.resolve()
                    self.assertIn(resolved, allowed_reads, 'CLI followed an untrusted report path')
                    observed.add(resolved)
                return original_open(path, mode, *args, **kwargs)
            with patch.object(Path, 'open', guarded_open), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli(arguments), 0)
            self.assertEqual(observed, allowed_reads)
            outputs = {p.name: p.read_bytes() for p in output.iterdir()}
            self.assertEqual(set(outputs), {'asset.json', 'preview-A.json', 'preview-B.json',
                                            'preview-C.json', 'import_report.json'})
            self.assertEqual(json.loads(outputs['preview-A.json']), json.loads(outputs['preview-C.json']))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli(arguments), 2)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, outputs)
            self.assertEqual(trap.read_bytes(), b'sentinel CAD bytes must never be read or changed')
            trust['asset_guid'] = 'contradiction'
            binding_path.write_bytes(encoded(trust))
            invalid_output = root / 'invalid-output'
            invalid_args = arguments[:-1] + [str(invalid_output)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli(invalid_args), 2)
            self.assertFalse(invalid_output.exists(), 'invalid import reserved or wrote an output directory')

    def test_pair_grid_independent_positions_ids_and_return(self):
        asset = self.asset()
        original = api.plan_candidate_pair(asset, request())
        ids = [r['id'] for r in original['occurrences']]
        self.assertEqual(len(set(ids)), 2)
        for w, d, h in [(901, 601, 331), (1200, 800, 450), (1100, 600, 330),
                        (900, 720, 330), (900, 600, 410), (900, 600, 330)]:
            plan = api.plan_candidate_pair(asset, request((w, d, h)))
            self.assertEqual(plan['status'], 'planned')
            self.assertEqual([r['id'] for r in plan['occurrences']], ids)
            for sign, row in zip((-1, 1), plan['occurrences']):
                expected = [sign * (w / 2 - 180.5), -d / 2, (h - 80) / 2]
                self.assertEqual(row['anchor_mm'], expected)
                self.assertEqual(row['matrix_mm'], [[1, 0, 0, 0], [0, -1, 0, 0],
                                                    [0, 0, -1, 0], expected + [1]])
        self.assertEqual(api.plan_candidate_pair(asset, request()), original)
        reordered = dict(reversed(list(request().items())))
        self.assertEqual(api.plan_candidate_pair(asset, reordered), original)

    def test_malformed_pair_request_never_yields_partial_occurrences(self):
        asset = self.asset()
        for name, value in [('count', 3), ('count', True), ('schema_version', True),
                            ('size', [900, 600]), ('size', [900, 600, float('inf')]),
                            ('size', [500, 600, 330]), ('size', [900, 17, 330]),
                            ('size', [900, 600, 190]), ('units', 'inch'),
                            ('thickness', 0), ('edge_inset_mm', -100),
                            ('exec', 'os.system("unexpected")')]:
            with self.subTest(field=name, value=value):
                data = request()
                data[name] = value
                result = api.plan_candidate_pair(asset, data)
                self.assertEqual(result['status'], 'blocked')
                self.assertEqual(result['changes'], [])
                self.assertFalse(result.get('occurrences'))
                self.assertTrue(result['diagnostics'])

    def test_same_name_unproven_root_and_descendants_cannot_be_sidecar_selected(self):
        def duplicate_root(reports):
            inventory = reports['inventory']
            inventory['rows'][0]['children'] = 2
            for row in list(inventory['rows'][1:]):
                other = copy.deepcopy(row)
                other['occurrence_path'][0] = 1
                other['id'] += 1000
                inventory['rows'].append(other)
        bundle, trust = changed_reports(duplicate_root)
        asset = api.import_candidate(bundle, trust)
        manifest = build_manifest(json.loads(bundle['inventory']),
                                  inventory_sha256=digest(bundle['inventory']))
        before = copy.deepcopy(manifest)
        ids = {tuple(r['source_ref']['occurrence_path']): r['rockpro_id']
               for r in manifest['occurrences']}
        sidecar = api.build_manifest_sidecar(manifest, asset, [ids[(0,)]])
        self.assertEqual(sidecar['links'][0]['source_occurrence_id'], ids[(0,)])
        for selected in ([ids[(1,)]], [ids[(0, 0)]], [ids[(0,)], ids[(1,)]],
                         [ids[(0,)], ids[(0,)]], []):
            with self.subTest(selected=selected):
                self.assert_refused(api.build_manifest_sidecar, manifest, asset, selected)
        self.assertEqual(manifest, before)
        self.assertEqual(manifest['manifest_stage'], 'inventory_draft')
        self.assertIs(manifest['runtime_template_compatible'], False)


if __name__ == '__main__':
    unittest.main()
