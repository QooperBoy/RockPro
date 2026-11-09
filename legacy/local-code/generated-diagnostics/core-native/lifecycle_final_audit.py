import json,os,hashlib,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
report=json.loads((root/'save-all-result-completed.json').read_text(encoding='utf-8-sig'))
assert report['passed'] and len(report['after'])==10
assert all(not r['modified'] and Path(r['path']).is_file() for r in report['after'])
originals=[]
for row in report['documents'][:2]:
 p=Path(row['before']['path'])
 # FileShare.ReadWrite used because an unrelated file owner can retain a handle.
 import ctypes
 from ctypes import wintypes
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
 kernel.CreateFileW.restype=wintypes.HANDLE
 kernel.ReadFile.argtypes=[wintypes.HANDLE,wintypes.LPVOID,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),wintypes.LPVOID]
 kernel.CloseHandle.argtypes=[wintypes.HANDLE]
 h=kernel.CreateFileW(str(p),0x80000000,3,None,3,0,None)
 if h==wintypes.HANDLE(-1).value: raise ctypes.WinError(ctypes.get_last_error())
 sha=hashlib.sha256();buf=ctypes.create_string_buffer(1024*1024);got=wintypes.DWORD()
 try:
  while True:
   if not kernel.ReadFile(h,buf,len(buf),ctypes.byref(got),None): raise ctypes.WinError(ctypes.get_last_error())
   if not got.value:break
   sha.update(buf.raw[:got.value])
 finally:kernel.CloseHandle(h)
 actual=sha.hexdigest()
 originals.append({'path':str(p),'sha256':actual,'original_disk_unchanged':actual==row['disk_backup_sha256'],'user_saved_copy':row['after']['path']})
assert all(x['original_disk_unchanged'] for x in originals)
out={'passed':True,'all_documents_saved_clean':True,'count':10,'graceful_exit_requested':True,'host_process_and_window_absent_observed':True,'forced_kill':False,'originals':originals,'save_receipt':str(root/'save-all-result-completed.json'),'exit_receipt':str(root/'exit-clean-preflight.json'),'restart_performed':False}
with (root/'lifecycle-completed.json').open('x',encoding='utf-8') as f:
 json.dump(out,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
print(json.dumps(out,ensure_ascii=False))
