"""Experimental, reversible SDK29 metadata compatibility for ATL12 holders.

Does not patch installed files, replace SDK interfaces, launch CAD or register
classes. Creates private TYPELIB-resource copies changing ONLY the top-level
version, then maps selected new HKCU TypeLib c.0 keys to those copies. The installed
SDK was independently observed to request 12.0 in its ATL type-info holders.
This is a narrow POC workaround, not general ABI/production approval.
"""
import argparse
import ctypes as ct
from ctypes import wintypes as wt
import hashlib
import json
import os
from pathlib import Path
import struct
import winreg

from comtypes import typeinfo

COMPONENTS = {
    'base': ('3iICApiBase.dll', '{6EE9ED93-0C2B-4808-B138-F294D9A71B0A}',
             'c14b5301db1b32d3ba5f5c4b19264a510ffe918ffbbc1be97af3b032598d7bd2'),
    'app': ('3iICApiIronCADApp.dll', '{D8E3895D-8CA1-46CF-85F9-800B9A649F82}',
            '35191dab8b1dc6acabae21da464af6e55e4dd41d506e7c462ec396fec077fd96'),
    'core': ('3iICApiCore.dll', '{DED8A8EE-1604-46A9-AEB3-043A3FEFB216}',
             'd8275888fe6abab8651f8c689487ad2c8140cfbf47e667de4fd8383a23424e92'),
    'drawing': ('3iICApiDrawing.dll', '{9BA7DFE4-33F0-477A-82F9-B9496B993C95}',
                '533b2cf9d0fd7fd1d96b19c86315734a8128ac8783af101e0308dfaf8de1cd8c'),
}
BIN = Path(r'C:\Program Files\IronCAD\2027\bin')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_once(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())


def resource(path):
    # DATAFILE + IMAGE_RESOURCE: no DllMain execution.
    kernel = ct.WinDLL('kernel32', use_last_error=True)
    kernel.LoadLibraryExW.argtypes = [wt.LPCWSTR, wt.HANDLE, wt.DWORD]
    kernel.LoadLibraryExW.restype = wt.HMODULE
    kernel.FindResourceW.argtypes = [wt.HMODULE, ct.c_void_p, ct.c_void_p]
    kernel.FindResourceW.restype = wt.HANDLE
    kernel.SizeofResource.argtypes = [wt.HMODULE, wt.HANDLE]
    kernel.SizeofResource.restype = wt.DWORD
    kernel.LoadResource.argtypes = [wt.HMODULE, wt.HANDLE]
    kernel.LoadResource.restype = wt.HANDLE
    kernel.LockResource.argtypes = [wt.HANDLE]
    kernel.LockResource.restype = ct.c_void_p
    kernel.FreeLibrary.argtypes = [wt.HMODULE]
    module = kernel.LoadLibraryExW(str(path), None, 0x22)
    if not module:
        raise ct.WinError(ct.get_last_error())
    try:
        name = ct.create_unicode_buffer('TYPELIB')
        found = kernel.FindResourceW(module, ct.c_void_p(1), ct.cast(name, ct.c_void_p))
        if not found:
            raise RuntimeError('Pinned TYPELIB resource 1 absent')
        length = kernel.SizeofResource(module, found)
        pointer = kernel.LockResource(kernel.LoadResource(module, found))
        if not pointer or length < 64:
            raise RuntimeError('Invalid TYPELIB resource')
        return ct.string_at(pointer, length)
    finally:
        kernel.FreeLibrary(module)


def metadata(path):
    lib = typeinfo.LoadTypeLibEx(str(path), typeinfo.REGKIND_NONE)
    attr = lib.GetLibAttr()
    types = []
    for i in range(lib.GetTypeInfoCount()):
        info = lib.GetTypeInfo(i)
        item = info.GetTypeAttr()
        types.append([info.GetDocumentation(-1)[0], str(item.guid), int(item.typekind),
                      int(item.cFuncs), int(item.cVars), int(item.cImplTypes),
                      int(item.wTypeFlags), int(item.wMajorVerNum), int(item.wMinorVerNum)])
    return {'guid': str(attr.guid), 'major': int(attr.wMajorVerNum),
            'minor': int(attr.wMinorVerNum), 'syskind': int(attr.syskind),
            'lcid': int(attr.lcid), 'type_count': len(types), 'types': types}


def tree(path):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                             winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
    except FileNotFoundError:
        return None
    with key:
        count, values, _ = winreg.QueryInfoKey(key)
        result = {'values': {}, 'children': {}}
        for i in range(values):
            name, value, kind = winreg.EnumValue(key, i)
            result['values'][name] = [kind, value]
        names = [winreg.EnumKey(key, i) for i in range(count)]
    for name in names:
        result['children'][name] = tree(path+'\\'+name)
    return result


def remove_tree(path):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                         winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
        children = [winreg.EnumKey(key, i) for i in range(winreg.QueryInfoKey(key)[0])]
    for child in children:
        remove_tree(path+'\\'+child)
    winreg.DeleteKeyEx(winreg.HKEY_CURRENT_USER, path, winreg.KEY_WOW64_64KEY, 0)


def rollback(receipt):
    records = json.loads(Path(receipt).read_text(encoding='utf-8'))['records']
    allowed = {'Software\\Classes\\TypeLib\\'+item[1]+'\\c.0' for item in COMPONENTS.values()}
    for record in records:
        if record['key'] not in allowed or record['before'] is not None:
            raise RuntimeError('Rollback scope mismatch')
        current = tree(record['key'])
        if current is not None and current != record['after']:
            raise RuntimeError('Concurrent registry change; refusing rollback')
    for record in reversed(records):
        if tree(record['key']) is not None:
            remove_tree(record['key'])
    print('ROLLBACK PASS: removed only this repair\'s new HKCU c.0 keys')


def apply(folder, components):
    folder = Path(folder).resolve()
    artifacts = Path(__file__).resolve().parents[3]/'artifacts'
    if folder.exists() or not folder.is_relative_to(artifacts):
        raise ValueError('New folder under checkout artifacts/ required')
    folder.mkdir()
    records = []
    for component in components:
        filename, guid, expected_sha = COMPONENTS[component]
        source = BIN/filename
        if sha(source) != expected_sha:
            raise RuntimeError('Installed SDK hash changed: '+filename)
        key = 'Software\\Classes\\TypeLib\\'+guid+'\\c.0'
        if tree(key) is not None:
            raise RuntimeError('Existing c.0 registration; refusing overwrite')
        raw = resource(source)
        if raw[:4] != b'MSFT' or struct.unpack_from('<HH', raw, 24) != (29, 0):
            raise RuntimeError('Expected MSFT TYPELIB29.0 header')
        original = folder/(component+'_original29.tlb')
        original.write_bytes(raw)
        before = metadata(original)
        if before['guid'] != guid or before['syskind'] != 3:
            raise RuntimeError('Resource identity/platform mismatch')
        patched = bytearray(raw)
        struct.pack_into('<H', patched, 24, 12)
        compat = folder/(component+'_compat12.tlb')
        with compat.open('xb') as stream:
            stream.write(patched)
            stream.flush()
            os.fsync(stream.fileno())
        if raw[:24] != patched[:24] or raw[26:] != patched[26:]:
            raise RuntimeError('Bytes outside top-level version changed')
        after = metadata(compat)
        expected = dict(before, major=12)
        if after != expected:
            raise RuntimeError('Type identity/count/signatures changed')
        records.append({'component': component, 'key': key, 'before': None,
            'source': str(source), 'source_sha256': expected_sha, 'resource_sha256': sha(original),
            'compat_path': str(compat), 'compat_sha256': sha(compat),
            'changed_byte_offsets': [i for i, (a, b) in enumerate(zip(raw, patched)) if a != b],
            'metadata_before': before, 'metadata_after': after})
    write_once(folder/'before_backup.json', {'records': records})
    created = []
    try:
        for record in records:
            created.append(record)
            for suffix, value in [('', 'Experimental ICAPI ATL12 metadata compatibility'),
                                   ('0\\win64', record['compat_path']), ('FLAGS', '0'),
                                   ('HELPDIR', str(folder))]:
                path = record['key']+('\\'+suffix if suffix else '')
                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0,
                        winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY) as key:
                    winreg.SetValueEx(key, '', 0, winreg.REG_SZ, value)
            record['after'] = tree(record['key'])
        write_once(folder/'repair_receipt.json', {'experimental': True, 'records': records,
            'scope': 'Only private metadata copies and new HKCU TypeLib c.0 keys; SDK/Interface29/HKLM untouched'})
        print(str(folder/'repair_receipt.json'))
    except Exception:
        for record in reversed(created):
            if tree(record['key']) is not None:
                remove_tree(record['key'])
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rollback', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--components', nargs='+', choices=list(COMPONENTS), default=['base', 'app'])
    args = parser.parse_args()
    if args.rollback:
        rollback(args.rollback)
    elif args.output:
        apply(args.output, args.components)
    else:
        parser.error('--output or --rollback required')


if __name__ == '__main__':
    main()
