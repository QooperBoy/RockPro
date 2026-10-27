"""Isolated local-interop selection tests: no compiler, registry or CAD activation."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_t1_machining_job as runner


class LocalInteropTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rockpro-interop-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.install = self.root / 'install'
        (self.install / 'bin').mkdir(parents=True)
        (self.install / 'bin' / 'ICApiIronCAD.tlb').write_bytes(b'synthetic installed TLB')
        self.sample = self.install / 'ICAPI' / 'Samples' / 'C#' / 'References' / 'interop.ICApiIronCAD.dll'
        self.sample.parent.mkdir(parents=True)
        self.sample.write_bytes(b'stale sample must not be returned')
        self.folder = self.root / 'job'
        self.folder.mkdir()

    def generated_process(self, command, **kwargs):
        if command[0].endswith('csc.exe'):
            Path(next(arg[5:] for arg in command if arg.startswith('/out:'))).write_bytes(b'synthetic helper')
        else:
            self.assertEqual(str(self.install / 'bin' / 'ICApiIronCAD.tlb'), command[1])
            Path(command[2]).write_bytes(b'synthetic generated interop')
        return subprocess.CompletedProcess(command, 0, 'ok', '')

    def test_both_hosts_generate_from_explicit_selected_installation(self):
        for year in (2023, 2027):
            with self.subTest(year=year):
                folder = self.folder / str(year)
                folder.mkdir()
                with patch.object(runner, 'selected_year', return_value=year) as selected, \
                     patch.object(runner, 'installation_dir', return_value=self.install) as installation, \
                     patch.object(runner.subprocess, 'run', side_effect=self.generated_process) as processes:
                    result = runner.current_interop(folder)
                selected.assert_called_once_with()
                installation.assert_called_once_with(year)
                self.assertEqual(2, processes.call_count)
                self.assertEqual(folder / 'interop.ICApiIronCAD.dll', result)
                evidence = json.loads((folder / 'interop-generation.json').read_text(encoding='utf-8'))
                self.assertEqual(year, evidence['host_year'])
                self.assertEqual(runner.sha(result), evidence['interop_sha256'])
                self.assertEqual(runner.sha(self.install / 'bin' / 'ICApiIronCAD.tlb'), evidence['tlb_sha256'])
                self.assertEqual(runner.sha(runner.ROOT / 'scripts/native/GenerateLocalInterop.cs'), evidence['helper_sha256'])
                self.assertEqual(b'stale sample must not be returned', self.sample.read_bytes())

    def test_compiler_failure_does_not_fall_back_to_sample(self):
        failed = subprocess.CompletedProcess([], 1, 'compile failed', '')
        with patch.object(runner, 'selected_year', return_value=2027), \
             patch.object(runner, 'installation_dir', return_value=self.install), \
             patch.object(runner.subprocess, 'run', return_value=failed) as processes:
            with self.assertRaisesRegex(RuntimeError, 'compile failed'):
                runner.current_interop(self.folder)
        self.assertEqual(1, processes.call_count)
        self.assertFalse((self.folder / 'interop.ICApiIronCAD.dll').exists())

    def test_import_failure_keeps_evidence_and_does_not_fall_back(self):
        responses = [subprocess.CompletedProcess([], 0, '', ''),
                     subprocess.CompletedProcess([], 2, 'import failed', 'failure detail')]
        with patch.object(runner, 'selected_year', return_value=2027), \
             patch.object(runner, 'installation_dir', return_value=self.install), \
             patch.object(runner.subprocess, 'run', side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, 'Local interop generation failed'):
                runner.current_interop(self.folder)
        evidence = json.loads((self.folder / 'interop-generation.json').read_text(encoding='utf-8'))
        self.assertEqual(2, evidence['returncode'])
        self.assertEqual(2027, evidence['host_year'])
        self.assertNotIn('interop_sha256', evidence)
        self.assertFalse((self.folder / 'interop.ICApiIronCAD.dll').exists())

    def test_invalid_host_is_rejected_before_install_or_process(self):
        with patch.object(runner, 'selected_year', side_effect=ValueError('Invalid host')), \
             patch.object(runner, 'installation_dir') as installation, \
             patch.object(runner.subprocess, 'run') as process:
            with self.assertRaises(ValueError):
                runner.current_interop(self.folder)
        installation.assert_not_called()
        process.assert_not_called()


if __name__ == '__main__':
    unittest.main()
