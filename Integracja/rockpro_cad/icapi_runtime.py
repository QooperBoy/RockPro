"""Explicit host selection; never fall back to the newest installed IronCAD.

Native libraries load lazily. A process must use one host version throughout.
The pinned python-ironcad parser fixes are reused without its auto-discovery.
"""
import importlib.metadata
import importlib.util
import os
from pathlib import Path

SUPPORTED_YEARS = (2023, 2027)
_runtime = None


def selected_year():
    value = os.environ.get("ROCKPRO_IRONCAD_YEAR", "2023")
    if value not in tuple(map(str, SUPPORTED_YEARS)):
        raise ValueError("ROCKPRO_IRONCAD_YEAR must be 2023 or 2027")
    return int(value)


def installation_dir(year=None):
    import winreg
    year = selected_year() if year is None else year
    if year not in SUPPORTED_YEARS:
        raise ValueError("Unsupported IronCAD year")
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                       rf"SOFTWARE\IronCAD\IRONCAD\{year - 1998}.0") as key:
        path = Path(winreg.QueryValueEx(key, "InstallDir")[0])
    if not (path / "bin" / "ICApiIronCAD.tlb").is_file():
        raise FileNotFoundError(f"IronCAD {year} ICAPI not installed at {path}")
    return path


def assert_host(base):
    expected = selected_year() - 1998
    actual = str(base.ApiVersion)
    if actual.split(".", 1)[0] != str(expected):
        raise RuntimeError(f"Wrong CAD host: API {actual}; expected {expected}.x")


def load_runtime():
    global _runtime
    year = selected_year()
    if _runtime is not None:
        if _runtime[0] != year:
            raise RuntimeError("Cannot change IronCAD version inside a running Python process")
        return _runtime[1:]
    install = installation_dir(year)
    import ctypes
    import comtypes.automation
    import comtypes.client
    import comtypes.tools.tlbparser
    parser_path = importlib.metadata.distribution("python-ironcad").locate_file(
        "python_ironcad/modified_tlbparser.py")
    spec = importlib.util.spec_from_file_location("_rockpro_vendor_tlbparser", parser_path)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    comtypes.tools.tlbparser.Parser.make_type = parser.Parser.make_type
    comtypes.automation._vartype_to_ctype[13] = ctypes.c_ulonglong
    api = comtypes.client.GetModule(str(install / "bin" / "ICApiIronCAD.tlb"))
    # Prepare legacy metadata locally; avoid slow remote type-info generation.
    comtypes.client.GetModule(str(install / "bin" / "IronCad.tlb"))
    _runtime = (year, api, str(install))
    return _runtime[1:]


def __getattr__(name):
    if name == "ICAPI":
        return load_runtime()[0]
    if name == "install_dir":
        return load_runtime()[1]
    raise AttributeError(name)
