"""Queue regressions use mocks; never attach to CAD."""
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_t2_parametric as queue
from run_t1_machining_job import cleanup_owned_addon


class QueueTests(unittest.TestCase):
    def test_cooperative_cancel_never_starts_native_job(self):
        with TemporaryDirectory() as d:
            folder=Path(d)/'native';Path(str(folder)+'.cancel').touch()
            with patch.object(queue,'run') as run:
                with self.assertRaisesRegex(RuntimeError,'cancelled'):queue.execute(folder,{'contract':'rockpro-t2-parametric-prototype-v1'},0)
                run.assert_not_called()
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

    def test_cleanup_uses_actual_sole_collection_position(self):
        class Addon:
            def _invoke(self,dispid,*args):
                return 'owned' if dispid==3 else 1  # misleading one-based Index
        class Collection:
            Count=1
            @property
            def _comobj(self):return self
            def _invoke(self,dispid,*args):
                if dispid==5:
                    self.assert_index=args[-1]
                    return Addon()
                if dispid==4 and args[-1]==0:self.Count=0
        collection=Collection()
        self.assertTrue(cleanup_owned_addon(collection,'owned',0)['removed'])
        self.assertEqual(collection.Count,0)

    def test_cleanup_preserves_unowned_addon(self):
        collection=Mock();collection.Count=2
        self.assertFalse(cleanup_owned_addon(collection,'owned',0)['removed'])
        collection._comobj._invoke.assert_not_called()


if __name__=='__main__':unittest.main()
