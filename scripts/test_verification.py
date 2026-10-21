import sys
import tempfile
import unittest
from pathlib import Path
from verify import run_check


class VerificationExitTests(unittest.TestCase):
    def test_nonzero_exit_cannot_be_pass_even_with_success_text(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            folder=Path(directory);steps=[]
            ok=run_check('intentional-failure',[sys.executable,'-c',"print('PASS');raise SystemExit(7)"],folder,steps)
            self.assertFalse(ok);self.assertEqual(steps[0]['exit_code'],7)
            self.assertEqual(steps[0]['status'],'FAIL')
    def test_missing_executable_is_failure(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            steps=[]
            self.assertFalse(run_check('missing',[str(Path(directory)/'absent.exe')],Path(directory),steps))
            self.assertEqual(steps[0]['status'],'FAIL')


if __name__=='__main__':unittest.main()
