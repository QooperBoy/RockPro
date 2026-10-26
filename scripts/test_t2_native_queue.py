"""Queue regressions use mocks; never attach to CAD."""
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_t2_parametric as queue


class QueueTests(unittest.TestCase):
    def test_busy_before_dispatch_never_invokes_cad(self):
        lock=Mock();lock.__enter__=Mock(side_effect=queue.CadBusyError('busy'));lock.__exit__=Mock()
        with patch.object(queue,'cad_writer_lock',return_value=lock),patch.object(queue,'run') as run:
            with self.assertRaises(queue.CadBusyError):queue.execute('unused',{'contract':'rockpro-t2-parametric-prototype-v1'},0)
            run.assert_not_called()

    def test_execution_failure_is_not_retried(self):
        lock=Mock();lock.__enter__=Mock();lock.__exit__=Mock()
        with patch.object(queue,'cad_writer_lock',return_value=lock),patch.object(queue,'run',side_effect=RuntimeError('already dispatched')) as run:
            with self.assertRaises(RuntimeError):queue.execute('unused',{'contract':'rockpro-t2-parametric-prototype-v1'},0)
            self.assertEqual(run.call_count,1)
            lock.__exit__.assert_called_once()


if __name__=='__main__':unittest.main()
