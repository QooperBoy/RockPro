"""Writer exclusion between independent processes, without contacting CAD."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

INTEGRATION = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(INTEGRATION))
from rockpro_cad import cad_lock


class WriterLockTests(unittest.TestCase):
    def test_cross_process_busy_then_released(self):
        name = 'Local\\RockProCAD.Test.' + uuid.uuid4().hex
        code = '''import sys
sys.path.insert(0,sys.argv[1])
from rockpro_cad import cad_lock
cad_lock.MUTEX_NAME=sys.argv[2]
cad_lock.legacy_lock_paths=lambda:[]
try:
    with cad_lock.cad_writer_lock(): pass
except RuntimeError:
    raise SystemExit(3)
'''
        def child():
            return subprocess.run([sys.executable, '-c', code, str(INTEGRATION), name],
                                  capture_output=True, timeout=20)
        with patch.object(cad_lock, 'MUTEX_NAME', name), patch.object(cad_lock, 'legacy_lock_paths', return_value=[]):
            with cad_lock.cad_writer_lock():
                self.assertEqual(child().returncode, 3)
                with cad_lock.cad_writer_lock():
                    self.assertEqual(child().returncode, 3)
            self.assertEqual(child().returncode, 0)

    def test_legacy_file_worker_is_also_excluded(self):
        import msvcrt
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path = Path(folder)/'cad.lock'
            path.write_bytes(b'0')
            with path.open('r+b') as old:
                msvcrt.locking(old.fileno(), msvcrt.LK_NBLCK, 1)
                try:
                    with patch.object(cad_lock, 'MUTEX_NAME', 'Local\\RockProCAD.Test.'+uuid.uuid4().hex), \
                            patch.object(cad_lock, 'legacy_lock_paths', return_value=[path]):
                        with self.assertRaisesRegex(RuntimeError, 'operation is running'):
                            with cad_lock.cad_writer_lock(): pass
                finally:
                    old.seek(0)
                    msvcrt.locking(old.fileno(), msvcrt.LK_UNLCK, 1)

    def test_exception_releases_writer(self):
        with patch.object(cad_lock, 'MUTEX_NAME', 'Local\\RockProCAD.Test.'+uuid.uuid4().hex), \
                patch.object(cad_lock, 'legacy_lock_paths', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'planned failure'):
                with cad_lock.cad_writer_lock():
                    raise ValueError('planned failure')
            with cad_lock.cad_writer_lock():
                self.assertEqual(cad_lock._state.depth, 1)
