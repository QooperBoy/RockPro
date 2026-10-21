"""Offline ROC-43 runner. Deliberate RED remains separate from regression GREEN."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests/core_design'), str(ROOT/'Integracja'),
                str(ROOT/'Integracja/rockpro_cad/mcp')]


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({'test': test.id(), 'status': 'PASS'})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({'test': test.id(), 'status': 'FAIL', 'reason': str(err[1])})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({'test': test.id(), 'status': 'ERROR', 'reason': str(err[1])})

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err:
            self.records.append({'test': subtest.id(), 'status': 'FAIL', 'reason': str(err[1])})


def main():
    if not __debug__:
        raise SystemExit('Run without -O: geometry oracle assertions must remain enabled')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['green', 'red', 'all'], default='green')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    names = []
    if args.mode in ('green', 'all'):
        names += ['test_layout_regression', 'test_oracle']
    if args.mode in ('red', 'all'):
        names += ['test_planner_red']
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(suite)
    passed = (result.wasSuccessful() and result.testsRun > 0 and not result.skipped
              and not result.expectedFailures and not result.unexpectedSuccesses)
    report = {'schema_version': 1, 'issue': 'ROC-43', 'mode': args.mode,
              'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'status': 'PASS' if passed else 'FAIL',
              'tests_run': result.testsRun, 'records': result.records,
              'native_ics': 'NOT RUN',
              'production_generator': 'NOT EXERCISED' if args.mode == 'green' else 'see requirement results',
              'catalog': 'synthetic only; not approved for physical installation',
              'skipped': len(result.skipped), 'expected_failures': len(result.expectedFailures)}
    files = [Path(__file__), *sorted((ROOT/'tests/core_design').glob('*.py')),
             *sorted((ROOT/'tests/core_design').glob('*.json'))]
    report['source_sha256'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in files}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')
        print('Evidence: ' + str(args.output.resolve()))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
