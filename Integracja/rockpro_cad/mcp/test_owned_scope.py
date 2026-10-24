"""Exercise the actual bridge cleanup helper without COM or IronCAD."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


class OwnedScopeTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', '.NET Framework')
    def test_failed_recovery_preserves_document_and_continues_cleanup(self):
        source=Path(__file__).resolve().parents[1]/'core_case/OwnedDocumentScope.cs'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); probe=root/'Probe.cs'; exe=root/'Probe.exe'
            probe.write_text('''using System; using System.IO;
class Probe {
 static int Main(string[] args) {
  var scope=new OwnedDocumentScope();
  bool saved=false,closed=false,failedClosed=false,releasedClosed=false;
  var released=new object();
  scope.Add(released,()=>false,p=>{},()=>{releasedClosed=true;});scope.Release(released);
  scope.Add(new object(),()=>true,p=>{File.WriteAllText(p,"modified work");saved=true;},()=>{if(!saved)throw new Exception();closed=true;});
  scope.Add(new object(),()=>true,p=>{throw new IOException("disk full");},()=>{failedClosed=true;});
  var errors=scope.Cleanup(args[0]);
  if(errors.Length!=1 || !saved || !closed || failedClosed || releasedClosed) return 1;
  if(Directory.GetFiles(args[0],"owned_recovery_*.ics").Length!=1) return 2;
  return 0;
 }
}''')
            compiler=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
            built=subprocess.run([str(compiler),'/nologo','/out:'+str(exe),str(source),str(probe)],capture_output=True)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            run=subprocess.run([str(exe),str(root)],capture_output=True,timeout=10)
            self.assertEqual(run.returncode,0,run.stderr)
