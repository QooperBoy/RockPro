"""Compile/run one fixed getter-only legacy triFunction addon; no UI/launch.

The small DLL runs inside the EXISTING application through documented AddOns.
It contains no document mutations and no arbitrary command/path execution API.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Integracja'))
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.core_case.latch_native import foreground, SOURCE_SHA
from rockpro_cad.parts.native import file_sha256

TOOLS = Path(r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64')


def build(folder, managed_name=None):
    from comtypes import typeinfo, GUID
    sdk = Path(r'C:\Program Files\IronCAD\2027\bin\ICApiIronCAD.tlb')
    if file_sha256(sdk) != 'a4a07be678226ecbdb3fc217bd21dc34eacaaa3d80676f626cf2147f6420b982':
        raise RuntimeError('Pinned SDK metadata changed')
    info = typeinfo.LoadTypeLibEx(str(sdk), typeinfo.REGKIND_NONE).GetTypeInfoOfGuid(
        GUID('{A5B9AF7D-228B-4ED1-BA42-D51318F7EA20}'))
    slots = [info.GetFuncDesc(i).oVft for i in range(info.GetTypeAttr().cFuncs)
             if info.GetNames(info.GetFuncDesc(i).memid)[0] == 'ApiVersion']
    if slots != [136]:
        raise RuntimeError('ApiVersion ABI offset differs from pinned official SDK')
    libraries = []
    for dll, exports in [('kernel32', ['GetModuleHandleExW', 'GetModuleFileNameW',
            'GetCurrentProcessId', 'LoadLibraryW', 'GetProcAddress', 'CreateFileW', 'WriteFile', 'FlushFileBuffers', 'CloseHandle']),
            ('oleaut32', ['GetActiveObject', 'RegisterActiveObject', 'RevokeActiveObject', 'LoadRegTypeLib', 'QueryPathOfRegTypeLib', 'SysFreeString']),
            ('user32', ['GetForegroundWindow', 'GetWindowThreadProcessId'])]:
        definition = folder/(dll+'.def')
        definition.write_text('LIBRARY '+dll+'.dll\nEXPORTS\n'+'\n'.join(exports)+'\n', encoding='ascii')
        lib = folder/(dll+'.lib')
        result = subprocess.run([str(TOOLS/'lib.exe'), '/nologo', '/machine:x64',
            '/def:'+str(definition), '/out:'+str(lib)], capture_output=True, text=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError('Import-library build failed: '+result.stdout+result.stderr)
        libraries.append(str(lib))
    source = ROOT/'Integracja/rockpro_cad/addin/LatchApiProbe.cpp'
    output = folder/'LatchApiProbe.dll'
    defines=[] if managed_name is None else ['/DROCKPRO_MANAGED_ASSEMBLY=L"'+managed_name+'"']
    result = subprocess.run([str(TOOLS/'cl.exe'), '/nologo', '/LD', '/O2', '/GS-', '/GR-',
        '/Zl', '/EHsc-']+defines+['/Fo:'+str(folder/'LatchApiProbe.obj'), '/Fe:'+str(output), str(source),
        '/link', '/NOENTRY', '/NODEFAULTLIB', '/MACHINE:X64']+libraries,
        capture_output=True, text=True, cwd=folder,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    write_receipt_once(folder/'compile.json', {'exit_code': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr, 'sdk_sha256': file_sha256(sdk),
        'source_sha256': file_sha256(source), 'ApiVersion_oVft': 136})
    if result.returncode:
        raise RuntimeError('Fixed getter addon compilation failed: '+result.stdout+result.stderr)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--context', type=Path)
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--expected-pid', type=int)
    args = parser.parse_args()
    folder = args.output.resolve()
    if folder.exists() or not folder.is_relative_to(ROOT/'artifacts'):
        parser.error('New folder inside checkout artifacts/ required')
    if args.native and (args.source is None or args.context is None or not args.expected_pid):
        parser.error('--native requires explicit source/context/expected-pid')
    folder.mkdir()
    dll = build(folder)
    print('COMPILE PASS '+str(dll), flush=True)
    if not args.native:
        return
    expected_dll_sha = file_sha256(dll)
    import comtypes.client
    from comtypes.automation import IDispatch
    from comtypes.gen import IronCAD
    source = args.source.resolve(strict=True)
    if file_sha256(source) != SOURCE_SHA:
        raise RuntimeError('Pinned source SHA changed')
    app = comtypes.client.GetActiveObject('IronCAD.Application', dynamic=True)
    user = ctypes.WinDLL('user32')
    user.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    def state():
        page = app.ActivePage
        hwnd = int(app.HWnd)
        pid = ctypes.c_ulong()
        user.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
        return {'hwnd': hwnd, 'pid': pid.value, 'foreground': foreground(),
                'active_page': str(page.FullName), 'saved': bool(page.Saved)}
    before = state()
    if before['active_page'].casefold() != str(args.context.resolve(strict=True)).casefold():
        raise RuntimeError('Existing active context identity mismatch')
    if before['pid'] != args.expected_pid or not before['saved']:
        raise RuntimeError('Expected existing host and saved source context required')
    write_receipt_once(folder/'before.json', before)
    backup = folder/'original_disk_backup.ics'
    with source.open('rb') as src, backup.open('xb') as dst:
        import shutil
        shutil.copyfileobj(src, dst)
        dst.flush()
        os.fsync(dst.fileno())
    if file_sha256(backup) != SOURCE_SHA:
        raise RuntimeError('Source byte backup differs')
    collection = app.AddOns
    def dispatch(value):
        return value._comobj if hasattr(value, '_comobj') else value.QueryInterface(IDispatch)
    count = int(collection.Count)
    addon = None
    owner_uuid = 'RockProProbe_'+uuid.uuid4().hex
    captured_identity = None
    outcome = {}
    try:
        # Some legacy no-argument DISPMETHODs are eagerly invoked by the
        # dynamic wrapper on attribute access. Invoke the documented DISPIDs
        # explicitly so creation/ownership is captured exactly once.
        addon = dispatch(collection)._invoke(3, 1, 0)
        from comtypes import IUnknown
        a = dispatch(addon)
        captured_identity = int(ctypes.cast(a.QueryInterface(IUnknown), ctypes.c_void_p).value)
        write_receipt_once(folder/'ownership_captured.json', {'owner_uuid': owner_uuid,
            'canonical_iunknown_this_session': captured_identity, 'returned_by_own_Add_DISPID3': True,
            'pid': before['pid'], 'dll': str(dll), 'dll_sha256': file_sha256(dll)})
        a._invoke(7, 4, 0, int(IronCAD.triFunction))
        a._invoke(3, 4, 0, owner_uuid)
        a._invoke(13, 4, 0, str(dll))
        a._invoke(12, 4, 0, 'RockProLatchProbe')
        configured = {'owner_uuid': a._invoke(3, 2, 0), 'dll': a._invoke(13, 2, 0),
                      'function': a._invoke(12, 2, 0), 'index': a._invoke(10, 2, 0)}
        if configured['owner_uuid'] != owner_uuid or str(configured['dll']).casefold() != str(dll).casefold() or configured['function'] != 'RockProLatchProbe':
            raise RuntimeError('Own addon configuration readback mismatch')
        write_receipt_once(folder/'ownership_configured.json', configured)
        if file_sha256(dll) != expected_dll_sha:
            raise RuntimeError('Pinned diagnostic DLL changed before execution')
        outcome['execute_result'] = int(dispatch(addon)._invoke(11, 1, 0))
        report = json.loads((folder/'inprocess_probe.json').read_text(encoding='utf-8'))
        outcome['probe'] = report
        if (report['process_id'] != args.expected_pid or report['legacy_app_pid'] != args.expected_pid
                or report['foreground_before'] != before['foreground']
                or report['foreground_after'] != before['foreground']):
            raise RuntimeError('In-process identity/foreground report differs')
        outcome['api_passed'] = report['base_qi_hr'] == '0x00000000' and report['api_version_hr'] == '0x00000000'
    finally:
        try:
            if addon is not None:
                a = dispatch(addon)
                current_identity = int(ctypes.cast(a.QueryInterface(IUnknown), ctypes.c_void_p).value)
                index = int(a._invoke(10, 2, 0))
                if (current_identity != captured_identity or a._invoke(3, 2, 0) != owner_uuid
                        or str(a._invoke(13, 2, 0)).casefold() != str(dll).casefold()
                        or a._invoke(12, 2, 0) != 'RockProLatchProbe'):
                    raise RuntimeError('Own temporary addon identity changed; preserving collection')
                # Legacy Item is empirically zero-based while Index is one-based.
                # Remove's convention is unproven: never guess, touch UNKNOWN,
                # or claim the entry was removed. Preserve only our marked entry.
                matches=[]
                for position in range(int(collection.Count)):
                    candidate=dispatch(dispatch(collection)._invoke(5,1,0,position))
                    if candidate._invoke(3,2,0)==owner_uuid:
                        matches.append({'owner_uuid':owner_uuid,'dll':candidate._invoke(13,2,0),
                                        'function':candidate._invoke(12,2,0)})
                if len(matches)!=1 or str(matches[0]['dll']).casefold()!=str(dll).casefold() or matches[0]['function']!='RockProLatchProbe':
                    raise RuntimeError('Exact own marked entry missing/ambiguous; collection preserved')
                outcome['own_entry_preserved']=True
                outcome['preserved_entry']=matches[0]
                outcome['preservation_reason']='Remove index convention unproven; UNKNOWN remains untouched'
        except Exception as error:
            outcome['cleanup_error'] = str(error)
        finally:
            try:
                after = state()
                source_after = file_sha256(source)
                outcome.update(before=before, after=after, guards_unchanged=before == after,
                    source_sha256_after=source_after, source_unchanged=source_after == SOURCE_SHA,
                    addon_count_before=count, addon_count_after=int(collection.Count))
            except Exception as error:
                outcome.update(after_error=str(error), guards_unchanged=False, source_unchanged=False)
            finally:
                write_receipt_once(folder/'probe_receipt.json', outcome)
    if not outcome.get('api_passed') or outcome.get('cleanup_error') or not outcome['guards_unchanged'] or not outcome['source_unchanged'] or outcome['addon_count_after'] != count+1 or outcome.get('own_entry_preserved') is not True:
        raise RuntimeError('In-process getter did not pass; inspect local raw receipt')
    print('INPROCESS BASEAPP GETTER PASS; own marked metadata entry preserved', flush=True)


if __name__ == '__main__':
    main()
