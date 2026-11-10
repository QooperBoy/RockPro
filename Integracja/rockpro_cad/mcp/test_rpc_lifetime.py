"""Real subprocess timeout probe, with a dummy writer; never connects to CAD."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest


class RpcLifetimeTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'WinForms process lifetime is Windows-specific')
    def test_timeout_keeps_writer_and_child_alive_until_result(self):
        source = Path(__file__).resolve().parents[1] / 'addin/RpcProcessSession.cs'
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            fixture = folder / 'writer.py'
            fixture.write_text('''import pathlib, subprocess, sys, time, msvcrt
folder=pathlib.Path(__file__).parent
with (folder/'writer.lock').open('w+b') as lock:
 lock.write(b'0'); lock.flush(); lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 print('ready',flush=True)
 subprocess.run([sys.executable,'-c',"import time; time.sleep(0.8)"])
 (folder/'completed').write_text('durable receipt')
 print('result',flush=True)
 sys.stdin.read()
''', encoding='utf-8')
            probe = folder / 'Probe.cs'
            probe.write_text('''using System; using System.Diagnostics; using System.IO;
using System.Threading; using RockPro.CAD;
class Probe {
 static int Main(string[] args) {
  var info=new ProcessStartInfo(args[0], "\\\""+args[1]+"\\\"");
  info.UseShellExecute=false; info.CreateNoWindow=true;
  info.RedirectStandardInput=true;info.RedirectStandardOutput=true;info.RedirectStandardError=true;
  using(var session=new RpcProcessSession(info)) {
   if(session.Read(5000)!="ready") return 1;
   try {session.Read(30);return 2;} catch(TimeoutException) {}
  }
  // Disposing the observer must not release the writer's file lock.
  using(var f=new FileStream(Path.Combine(args[2],"writer.lock"),FileMode.Open,FileAccess.ReadWrite,FileShare.ReadWrite)) {
   try {f.Lock(0,1); f.Unlock(0,1); return 3;} catch(IOException) {}
  }
  var until=DateTime.UtcNow.AddSeconds(8);
  while(!File.Exists(Path.Combine(args[2],"completed")) && DateTime.UtcNow<until) Thread.Sleep(20);
  if(!File.Exists(Path.Combine(args[2],"completed"))) return 4;
  Thread.Sleep(250); return 0;
 }
}''', encoding='utf-8')
            compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
            exe = folder/'Probe.exe'
            built = subprocess.run([str(compiler), '/nologo', '/out:'+str(exe), str(source), str(probe)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
            run = subprocess.run([str(exe), sys.executable, str(fixture), str(folder)], capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr)
