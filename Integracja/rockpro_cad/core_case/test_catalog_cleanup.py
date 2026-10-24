"""Catalog operation ownership cleanup on success and failure; no COM."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.catalog_native import close_owned_documents


class Document:
    def __init__(self,modified=False,fail=False,silent_save_failure=False):
        self.Modified=modified;self.fail=fail;self.closed=False;self.recovery=[];self.Name="owned.ics";self.silent_save_failure=silent_save_failure
    def QueryInterface(self,interface):return self
    def Update(self):pass
    def SaveAs(self,path,*args):
        self.recovery.append(path)
        if not self.silent_save_failure:
            Path(path).write_bytes(b'saved owned changes');self.Name=path;self.Modified=False
    def Close(self):
        if self.fail:raise RuntimeError('fixture close failed')
        self.closed=True


class CleanupTests(unittest.TestCase):
    def test_only_owned_documents_close_and_dirty_ones_get_distinct_recovery(self):
        original=Document(True);clean=Document();dirty=Document(True)
        owned=[clean,dirty]
        with tempfile.TemporaryDirectory() as folder:
            close_owned_documents(owned,SimpleNamespace(IZSceneDoc=object(),Z_LINKS_COPY_ALL=0),folder)
            self.assertTrue(Path(dirty.recovery[0]).is_relative_to(folder))
        self.assertFalse(original.closed);self.assertEqual(original.recovery,[])
        self.assertTrue(clean.closed);self.assertTrue(dirty.closed);self.assertEqual(owned,[])

    def test_close_error_does_not_skip_remaining_owned_documents(self):
        first=Document();bad=Document(fail=True);last=Document()
        with self.assertRaisesRegex(RuntimeError,'cleanup failed'):
            close_owned_documents([first,bad,last],SimpleNamespace(),Path('unused'))
        self.assertTrue(first.closed);self.assertTrue(last.closed)

    def test_silent_save_failure_retains_modified_document_and_ownership(self):
        dirty=Document(True,silent_save_failure=True);clean=Document();owned=[clean,dirty]
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError,'Recovery save not confirmed'):
                close_owned_documents(owned,SimpleNamespace(IZSceneDoc=object(),Z_LINKS_COPY_ALL=0),folder)
        self.assertFalse(dirty.closed);self.assertTrue(dirty.Modified)
        self.assertTrue(clean.closed);self.assertEqual(owned,[dirty])
