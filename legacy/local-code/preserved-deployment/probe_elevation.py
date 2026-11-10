import ctypes as c
from ctypes import wintypes as w
k=c.WinDLL('kernel32',use_last_error=True);a=c.WinDLL('advapi32',use_last_error=True)
k.OpenProcess.restype=w.HANDLE
for pid in [11996,k.GetCurrentProcessId()]:
 p=k.OpenProcess(0x1000,False,pid);t=w.HANDLE();a.OpenProcessToken(w.HANDLE(p),8,c.byref(t));v=w.DWORD();sz=w.DWORD()
 ok=a.GetTokenInformation(t,20,c.byref(v),4,c.byref(sz));print(pid,'elevated',v.value,'ok',ok)
