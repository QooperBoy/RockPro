"""One desktop CAD writer across checkout, deployment and legacy workers."""
from contextlib import contextmanager, ExitStack
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import threading

MUTEX_NAME = r'Local\RockProCAD.NativeWriter.v1'
_state = threading.local()


def legacy_lock_paths():
    integration = Path(__file__).resolve().parents[1]
    candidates = [integration/'rockpro_cad/mcp/cad.lock',
                  integration.parent.parent/'Integracja/rockpro_cad/mcp/cad.lock',
                  integration.parent/'rockpro-cad/Integracja/rockpro_cad/mcp/cad.lock']
    return sorted({p.resolve() for p in candidates if p.parent.is_dir()}, key=lambda p: str(p).lower())


@contextmanager
def _legacy_lock(path):
    import msvcrt
    with path.open('a+b') as stream:
        try:
            stream.seek(0)
            if not stream.read(1):
                stream.write(b'0')
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError('Another RockPro CAD operation is running') from exc
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


@contextmanager
def cad_writer_lock():
    """Nonblocking, same-thread reentrant; abandoned writers require recovery."""
    if getattr(_state, 'depth', 0):
        _state.depth += 1
        try:
            yield
        finally:
            _state.depth -= 1
        return
    if os.name != 'nt':
        raise RuntimeError('Native CAD execution requires Windows')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.ReleaseMutex.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    acquired = False
    try:
        outcome = kernel.WaitForSingleObject(handle, 0)
        acquired = outcome in (0, 0x80)
        if outcome == 0x80:
            raise RuntimeError('Previous CAD writer stopped unexpectedly; reconcile operation journal before retry')
        if outcome != 0:
            raise RuntimeError('Another RockPro CAD operation is running')
        with ExitStack() as stack:
            for path in legacy_lock_paths():
                stack.enter_context(_legacy_lock(path))
            _state.depth = 1
            try:
                yield
            finally:
                _state.depth = 0
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)
