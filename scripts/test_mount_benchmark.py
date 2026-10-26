import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark_working_mounts import benchmark
from rockpro_cad.core_case.test_working_mounts import fixture,build,inventory_bytes


class MountBenchmarkTests(unittest.TestCase):
    def inputs(self,folder):
        data=fixture();inventory=folder/'inventory.json';standard=folder/'standard.json'
        inventory.write_bytes(inventory_bytes(data));standard.write_text(json.dumps(build(data)),encoding='utf-8')
        return inventory,standard

    def test_mismatched_inventory_is_rejected_before_timing_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inventory,standard=self.inputs(root)
            inventory.write_bytes(inventory.read_bytes()+b' ')
            with mock.patch('benchmark_working_mounts.time.perf_counter',side_effect=AssertionError('Timing began')):
                with self.assertRaisesRegex(ValueError,'Inventory revision'):
                    benchmark(inventory,standard,root/'result','root/2',[0,0,1])
            self.assertFalse((root/'result').exists())
            inventory,standard=self.inputs(root)
            changed=json.loads(standard.read_text(encoding='utf-8'));changed['schema']='rockpro.working-mount-standard/99'
            standard.write_text(json.dumps(changed),encoding='utf-8')
            with mock.patch('benchmark_working_mounts.time.perf_counter',side_effect=AssertionError('Timing began')):
                with self.assertRaisesRegex(ValueError,'working standard'):
                    benchmark(inventory,standard,root/'result','root/2',[0,0,1])
            self.assertFalse((root/'result').exists())

    def test_repeat_bounds_checked_before_reading_files(self):
        for count in (0,21,True,1.5):
            with self.subTest(repeats=count),self.assertRaisesRegex(ValueError,'repeats'):
                benchmark('missing','missing','missing','root/2',[0,0,1],repeats=count)
        for count in (-1,6,False):
            with self.subTest(warmup=count),self.assertRaisesRegex(ValueError,'warmup'):
                benchmark('missing','missing','missing','root/2',[0,0,1],warmup=count)

    def test_timings_are_separate_repeatable_and_inputs_and_outputs_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inventory,standard=self.inputs(root)
            before=(inventory.read_bytes(),standard.read_bytes())
            report=benchmark(inventory,standard,root/'result','root/2',[0,0,300],repeats=2,warmup=1)
            self.assertEqual((inventory.read_bytes(),standard.read_bytes()),before)
            self.assertEqual(report['nodes'],4);self.assertEqual(report['physical_parts'],2)
            self.assertEqual(report['inputs']['inventory_sha256'],hashlib.sha256(before[0]).hexdigest())
            self.assertEqual(report['native_cad'],'NOT RUN');self.assertFalse(report['source_ics_read'])
            self.assertTrue(report['deterministic_outputs']);self.assertTrue(report['standard_unchanged'])
            for phase,count in (('warmup',1),('measured',2)):
                self.assertEqual(len(report['measurements'][phase]),3)
                for measurements in report['measurements'][phase].values():
                    self.assertEqual(len(measurements['samples']),count)
                    for sample in measurements['samples']:
                        self.assertTrue(all(math.isfinite(value) and value>=0 for value in sample.values()))
                    for stats in measurements['statistics'].values():
                        self.assertLessEqual(stats['min'],stats['median']);self.assertLessEqual(stats['median'],stats['max'])
            path=root/'result/benchmark.json';output_before=path.read_bytes()
            with self.assertRaises(FileExistsError):benchmark(inventory,standard,root/'result','root/2',[0,0,300])
            self.assertEqual(path.read_bytes(),output_before)


if __name__=='__main__':unittest.main()
