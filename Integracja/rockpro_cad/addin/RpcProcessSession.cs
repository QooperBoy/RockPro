using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading.Tasks;

namespace RockPro.CAD {
// A UI timeout detaches the observer, never terminates a CAD writer. Keep pipes
// drained and the process alive until its pending operation has returned.
internal sealed class RpcProcessSession : IDisposable {
 readonly Process process;
 readonly Task<string> errors;
 Task<string> pending;
 bool detached, disposed;
 internal readonly StreamWriter Input;
 internal RpcProcessSession(ProcessStartInfo info) {
  process=Process.Start(info);
  errors=process.StandardError.ReadToEndAsync();
  Input=new StreamWriter(process.StandardInput.BaseStream,new UTF8Encoding(false));
  Input.AutoFlush=true;
 }
 internal string Read(int timeoutMilliseconds=180000) {
  pending=process.StandardOutput.ReadLineAsync();
  if(!pending.Wait(timeoutMilliseconds)) {
   detached=true;
   Task.Run(async delegate {
    try { await pending.ConfigureAwait(false); }
    catch { /* Operation journal, not the detached observer, owns its outcome. */ }
    await Finish().ConfigureAwait(false);
   });
   throw new TimeoutException("Przekroczono czas oczekiwania. Operacja moĹĽe nadal trwaÄ‡; wykonawca nie zostaĹ‚ przerwany. SprawdĹş historiÄ™/status przed kolejnÄ… prĂłbÄ….");
  }
  string reply=pending.Result; pending=null;
  if(reply==null) throw new EndOfStreamException("MCP zamknÄ™Ĺ‚o poĹ‚Ä…czenie bez odpowiedzi; sprawdĹş stan operacji.");
  return reply;
 }
 async Task Finish() {
  try {
   try { Input.Close(); } catch(IOException) {} catch(ObjectDisposedException) {}
   await process.StandardOutput.ReadToEndAsync().ConfigureAwait(false);
   await errors.ConfigureAwait(false);
   process.WaitForExit();
  } finally { process.Dispose(); }
 }
 public void Dispose() {
  if(disposed) return;
  disposed=true;
  if(!detached) Task.Run(async delegate { await Finish().ConfigureAwait(false); });
 }
}
}
