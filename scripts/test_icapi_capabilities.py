"""Isolated tests: synthetic metadata and bytes, no installed SDK or CAD needed."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import report_icapi_capabilities as cap


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rockpro-capabilities-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sources = {}
        snapshots = {}
        for year, major in cap.API_MAJOR.items():
            folder = self.root / str(year)
            folder.mkdir()
            interop = folder / 'interop.dll'
            tlb = folder / 'source.tlb'
            interop.write_bytes(f'SYNTHETIC INTEROP {year}'.encode())
            tlb.write_bytes(f'SYNTHETIC TLB {year}'.encode())
            snapshots[year] = cap.digest(tlb)
            types = {}
            for name, requirements in cap.CAPABILITIES.items():
                if year == 2023 and name == 'bulk29':
                    continue
                for interface, signature in requirements:
                    types.setdefault(cap.PREFIX + interface, set()).add(signature)
            metadata = {
                'assembly': f'interop.ICApiIronCAD, Version={major}.0.0.0, Culture=neutral, PublicKeyToken=null',
                'sha256': cap.digest(interop), 'library': str(interop),
                'types': [{'name': name, 'methods': sorted(methods)} for name, methods in types.items()],
            }
            meta = folder / 'metadata.json'
            self.write(meta, metadata)
            evidence = {'schema_version': 1, 'host_year': year, 'api_major': major,
                        'metadata_sha256': cap.digest(meta), 'interop_path': str(interop),
                        'interop_sha256': cap.digest(interop), 'tlb_path': str(tlb), 'tlb_sha256': cap.digest(tlb)}
            ev = folder / 'evidence.json'
            self.write(ev, evidence)
            self.sources[year] = (meta, ev)
        # Tests explicitly replace captured real TLB digests with synthetic fixture digests.
        self.addCleanup(patch.stopall)
        patch.object(cap, 'TLB_SNAPSHOTS', snapshots).start()

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def change_metadata(self, callback, year=2023):
        meta, ev = self.sources[year]
        value = cap.read_json(meta)
        callback(value)
        self.write(meta, value)
        evidence = cap.read_json(ev)
        evidence['metadata_sha256'] = cap.digest(meta)
        self.write(ev, evidence)

    def change_evidence(self, callback, year=2023):
        _, ev = self.sources[year]
        value = cap.read_json(ev)
        callback(value)
        self.write(ev, value)

    def inspect(self, year=2023):
        return cap.inspect_host(year, *self.sources[year])

    def test_common_and_29_only_are_not_runtime_pass(self):
        report = cap.make_report(self.inspect(), self.inspect(2027))
        self.assertIn('parameters_transforms', report['comparison']['common_methods_present'])
        self.assertEqual(['bulk29'], report['comparison']['only_29_recorded'])
        self.assertEqual('NOT RUN', report['native_status'])
        for host in report['hosts']:
            for row in host['capabilities'].values():
                self.assertIsNone(row['runtime_supported'])
                self.assertFalse(row['automatic_fallback'])
        self.assertIn('Z_SUBTRACT', cap.markdown(report))

    def test_unknown_field_cannot_claim_support(self):
        def mutate(value):
            value['types'] = []
            value['supported'] = True
            value['native_status'] = 'PASS'
            value['capabilities'] = {'bulk29': {'supported': True}}
        self.change_metadata(mutate)
        result = self.inspect()
        self.assertTrue(all(x['metadata_status'] == 'missing_metadata' for x in result['capabilities'].values()))
        self.assertEqual('NOT RUN', result['native_status'])

    def test_other_overload_does_not_count(self):
        def mutate(value):
            for row in value['types']:
                row['methods'] = [m.replace('Play(Double ByRef, Double ByRef)', 'Play(System.String)') for m in row['methods']]
        self.change_metadata(mutate)
        self.assertEqual('missing_metadata', self.inspect()['capabilities']['animation_playback']['metadata_status'])

    def test_year_mismatch_refused(self):
        self.change_evidence(lambda v: v.update(host_year=2027))
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_api_major_mismatch_refused(self):
        self.change_evidence(lambda v: v.update(api_major=29))
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_sample_wrapper_27_cannot_claim_2027(self):
        self.change_metadata(lambda v: v.update(assembly=v['assembly'].replace('29.0', '27.0')), 2027)
        with self.assertRaises(cap.EvidenceError): self.inspect(2027)

    def test_modified_metadata_refused(self):
        meta, _ = self.sources[2023]
        meta.write_text(meta.read_text() + ' ', encoding='utf-8')
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_modified_interop_refused(self):
        (self.root / '2023' / 'interop.dll').write_bytes(b'changed')
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_swapped_tlb_even_with_matching_digest_refused(self):
        other = cap.read_json(self.sources[2027][1])
        self.change_evidence(lambda v: v.update(tlb_path=other['tlb_path'], tlb_sha256=other['tlb_sha256']))
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_library_path_mismatch_refused(self):
        self.change_metadata(lambda v: v.update(library=str(self.root / 'other.dll')))
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_metadata_interop_digest_mismatch_refused(self):
        self.change_metadata(lambda v: v.update(sha256='0' * 64))
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_malformed_digest_and_missing_methods_refused(self):
        self.change_metadata(lambda v: v.update(sha256=None))
        with self.assertRaises(cap.EvidenceError): self.inspect()
        self.change_metadata(lambda v: v.update(sha256=cap.digest(self.root / '2023' / 'interop.dll')))
        self.change_metadata(lambda v: v['types'][0].update(methods={'supported': True}))
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_malformed_evidence_digest_refused(self):
        self.change_evidence(lambda v: v.update(tlb_sha256='not-a-sha256'))
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_duplicate_type_refused(self):
        self.change_metadata(lambda v: v['types'].append(copy.deepcopy(v['types'][0])))
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_duplicate_json_key_refused(self):
        _, ev = self.sources[2023]
        ev.write_text('{"host_year":2023,"host_year":2027}', encoding='utf-8')
        with self.assertRaises(cap.EvidenceError): self.inspect()

    def test_missing_method_does_not_select_fallback(self):
        row = self.inspect()['capabilities']['bulk29']
        self.assertEqual('missing_metadata', row['metadata_status'])
        self.assertFalse(row['automatic_fallback'])
        self.assertTrue(row['missing'])

    def test_replacement_after_json_capture_keeps_original_content_and_digests(self):
        meta, evidence = self.sources[2023]
        before_metadata = cap.digest(meta)
        before_evidence = cap.digest(evidence)
        original_checked_hash = cap.checked_hash
        replaced = False

        def replace_during_binary_hash(path, expected):
            nonlocal replaced
            if not replaced:
                # This occurs after JSON capture but before capability evaluation/report creation.
                replacement = cap.read_json(meta)
                replacement['types'] = []
                self.write(meta, replacement)
                self.write(evidence, {'schema_version': 1, 'host_year': 9999})
                replaced = True
            return original_checked_hash(path, expected)

        with patch.object(cap, 'checked_hash', side_effect=replace_during_binary_hash):
            report = self.inspect()
        self.assertTrue(replaced)
        self.assertEqual(before_metadata, report['metadata_sha256'])
        self.assertEqual(before_evidence, report['evidence_sha256'])
        self.assertNotEqual(cap.digest(meta), report['metadata_sha256'])
        self.assertNotEqual(cap.digest(evidence), report['evidence_sha256'])
        self.assertEqual('methods_present', report['capabilities']['parameters_transforms']['metadata_status'])

    def test_json_limit_rejects_metadata_and_evidence_before_output(self):
        output = self.root / 'oversized-output'
        args = []
        for year, (meta, evidence) in self.sources.items():
            args += [f'--metadata-{year}', str(meta), f'--evidence-{year}', str(evidence)]
        args += ['--output-dir', str(output)]
        for oversized in self.sources[2023]:
            original = oversized.read_bytes()
            oversized.write_bytes(b' ' * 4097)
            with patch.object(cap, 'MAX_JSON_BYTES', 4096):
                with self.assertRaises(SystemExit) as exc:
                    cap.main(args)
            self.assertEqual(2, exc.exception.code)
            self.assertFalse(output.exists())
            oversized.write_bytes(original)

    def test_binary_hash_streams_without_read_bytes(self):
        binary = self.root / 'binary-test.dll'
        content = b'abcdefghijk' * 37
        binary.write_bytes(content)
        import hashlib
        with patch.object(cap, 'HASH_CHUNK_BYTES', 13), patch.object(Path, 'read_bytes', side_effect=AssertionError('whole-file read forbidden')):
            self.assertEqual(hashlib.sha256(content).hexdigest(), cap.digest(binary))

    def test_cli_writes_only_new_output_and_preserves_inputs(self):
        before = {p: cap.digest(p) for paths in self.sources.values() for p in paths}
        output = self.root / 'output'
        args = []
        for year, (meta, ev) in self.sources.items():
            args += [f'--metadata-{year}', str(meta), f'--evidence-{year}', str(ev)]
        args += ['--output-dir', str(output)]
        self.assertEqual(0, cap.main(args))
        self.assertTrue((output / 'capabilities.json').is_file())
        self.assertIn('NOT RUN', (output / 'capabilities.md').read_text(encoding='utf-8'))
        with self.assertRaises(SystemExit) as exc: cap.main(args)
        self.assertEqual(2, exc.exception.code)
        self.assertEqual(before, {p: cap.digest(p) for p in before})


if __name__ == '__main__':
    unittest.main()
