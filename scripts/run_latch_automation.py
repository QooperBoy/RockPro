"""Explicit /Automation launch for the latch POC; never sets Visible/Activate.

The vendor's StartIronCAD sample creates IronCAD.Application, then separately
sets Visible=true. This runner omits that setter. A trial/license dialog can
still require HUMAN confirmation and can time out COM activation. Never bypass
it. The original host is preserved. A new hidden host is owned by this runner.

After factory and API getters, pause BEFORE opening any scene: create the
reported continue.txt containing CONTINUE_A_B to proceed, or cancel.txt to stop.
Metadata compatibility is a separate, explicit experiment; not applied here.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Integracja'))
from rockpro_cad.core_case.latch_native import execute_latch_showcase, foreground
from rockpro_cad.core_case.corner_native import exclusive_copy
from rockpro_cad.core_case.native import write_receipt_once


def window_pid(hwnd):
    user = ctypes.WinDLL('user32')
    user.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    value = ctypes.c_ulong()
    user.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(value))
    return value.value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ('source', 'corner-receipt', 'corner-assets', 'output'):
        parser.add_argument('--'+argument, type=Path, required=True)
    parser.add_argument('--context', type=Path, help='Exact open context if factory returns original host')
    parser.add_argument('--gate-timeout', type=int, default=300)
    args = parser.parse_args()
    folder = args.output.resolve()
    if folder.exists() or not folder.is_relative_to(ROOT/'artifacts'):
        parser.error('New folder under checkout artifacts/ required')
    if not 30 <= args.gate_timeout <= 900:
        parser.error('Gate timeout must be 30..900 seconds')
    # No creation/activation is hidden in imports or existing-context attachment.
    import comtypes.client
    from python_ironcad import ICAPI
    folder.mkdir()
    original = comtypes.client.GetActiveObject('IronCAD.Application', dynamic=True)
    original_hwnd = int(original.HWnd)
    original_pid = window_pid(original_hwnd)
    initial = {'foreground_hwnd': foreground(), 'original_pid': original_pid,
               'original_hwnd': original_hwnd, 'original_visible': bool(original.Visible)}
    write_receipt_once(folder/'before_factory.json', initial)
    app = base = seed = None
    new_host = False
    outcome = {'native_passed': False, 'visible_setter_used': False, 'activation_used': False}
    try:
        # Official SDK sample activation path; no normal EXE / visible startup.
        app = comtypes.client.CreateObject('IronCAD.Application', dynamic=True)
        hwnd = int(app.HWnd)
        pid = window_pid(hwnd)
        visible = bool(app.Visible)
        new_host = bool(pid and pid != original_pid)
        outcome.update(factory_pid=pid, factory_hwnd=hwnd, factory_visible=visible,
                       own_new_host=new_host, foreground_after_factory=foreground())
        write_receipt_once(folder/'factory_returned.json', outcome)
        # A human may explicitly confirm the vendor Trial dialog during launch.
        # No scene call occurs until the separate continuation gate below.
        if new_host and visible:
            raise RuntimeError('New automation host is visible; no scene operations')
        base = app.ZIronCADApp.QueryInterface(ICAPI.IZBaseApp)
        outcome['api_version'] = str(base.ApiVersion)
        outcome['baseapp_passed'] = True
        if new_host and int(base.GetOpenDocsCount()) != 0:
            raise RuntimeError('New automation host contains unknown documents; preserving them')
        gate = folder/'continue.txt'
        write_receipt_once(folder/'ready_for_gate.json', {'passed': True,
            'pid': pid, 'visible': visible, 'foreground_unchanged': foreground() == initial['foreground_hwnd'],
            'continue_file': str(gate), 'required_text': 'CONTINUE_A_B',
            'native_documents_opened': 0})
        print('API_READY_WAITING_FOR_GATE '+str(gate), flush=True)
        deadline = time.monotonic()+args.gate_timeout
        while not gate.is_file():
            if (folder/'cancel.txt').exists() or time.monotonic() > deadline:
                raise RuntimeError('Cancelled/timed out before scene operations')
            time.sleep(.25)
        if gate.read_text(encoding='utf-8').strip() != 'CONTINUE_A_B':
            raise RuntimeError('Invalid continuation gate')
        # The human confirmation is complete. Establish the new read-only
        # foreground baseline; never restore or set foreground ourselves.
        initial['foreground_hwnd'] = foreground()
        write_receipt_once(folder/'after_manual_gate_state.json', {'foreground_hwnd': initial['foreground_hwnd']})
        receipt = json.loads(args.corner_receipt.read_text(encoding='utf-8'))
        if receipt.get('passed') is not True:
            raise RuntimeError('Accepted corner receipt required')
        if new_host:
            seed_path = folder/'context_seed.ics'
            exclusive_copy(receipt['output_path'], seed_path)
            already, seed = base.OpenFile2(str(seed_path), True, False)
            if already or str(seed.Name).casefold() != str(seed_path).casefold():
                raise RuntimeError('Own hidden seed ownership/path guard')
            context = seed_path
        else:
            if args.context is None:
                raise RuntimeError('Existing host requires explicit already-open context')
            context = args.context.resolve(strict=True)
        result = execute_latch_showcase(context=context, source=args.source,
            corner_receipt=receipt,
            corner_assets=json.loads(args.corner_assets.read_text(encoding='utf-8')),
            output=folder/'models')
        outcome['native_passed'] = result['passed']
        outcome['outputs'] = [case['output_path'] for case in result['cases']]
    except Exception as error:
        outcome['error'] = str(error)
        print(type(error).__name__+': '+str(error), flush=True)
    finally:
        try:
            if seed is not None:
                if seed.Modified:
                    backup = folder/('preserved_seed_'+uuid.uuid4().hex+'.ics')
                    seed.QueryInterface(ICAPI.IZSceneDoc).SaveAs(str(backup), ICAPI.Z_LINKS_COPY_ALL, False)
                    outcome['seed_backup'] = str(backup)
                if seed.Modified:
                    raise RuntimeError('Owned seed remains modified; preserving without force close')
                seed.Close()
                outcome['own_seed_closed'] = True
            if new_host:
                # Scalar counter only; never use failing ICAPI GetAllOpenDocs.
                count = int(base.GetOpenDocsCount()) if base is not None else int(app.Pages.Count)
                outcome['remaining_new_host_documents'] = count
                if count == 0:
                    app.Quit()
                    outcome['own_new_host_quit'] = True
                else:
                    outcome['cleanup_error'] = 'Documents remain; no forced Quit'
        except Exception as error:
            outcome['cleanup_error'] = str(error)
        outcome['foreground_final'] = foreground()
        outcome['foreground_unchanged'] = outcome['foreground_final'] == initial['foreground_hwnd']
        outcome['original_host_closed'] = False
        write_receipt_once(folder/'automation_result.json', outcome)
    if not outcome.get('native_passed') or outcome.get('cleanup_error'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
