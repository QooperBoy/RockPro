"""Attach to an already open ICS via ROT and read without CAD mutations."""

from contextlib import redirect_stdout
import hashlib
import ntpath
from pathlib import Path
import sys

from .reader import read_parts


class SourceMismatchError(RuntimeError):
    pass


def same_document_path(actual, expected):
    """Reject basename-only evidence; compare canonical absolute Windows paths."""
    actual = str(actual)
    expected = str(expected)
    if not ntpath.isabs(actual) or not ntpath.isabs(expected):
        return False
    return ntpath.normcase(ntpath.normpath(actual)) == ntpath.normcase(ntpath.normpath(expected))


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class NativePartsAdapter:
    """Only getters and interface queries. No launch/open/save/close/activation."""

    def __init__(self, legacy, base, document, api, source):
        self.legacy, self.base, self.document, self.api = legacy, base, document, api
        self.source = str(source)
        self._known_element_types = frozenset(
            value for name, value in vars(api).items()
            if name.startswith("Z_ELEMENT_") and isinstance(value, int)
        ) if api is not None else frozenset()

    @classmethod
    def attach(cls, source):
        # python_ironcad prints environment info on import; keep stdout JSON-only.
        with redirect_stdout(sys.stderr):
            import ctypes as ct
            import comtypes.client
            from comtypes import HRESULT
            from comtypes.automation import IDispatch
            from python_ironcad import ICAPI

        source = Path(source).resolve(strict=True)
        ole = ct.OleDLL("ole32")
        rot = ct.POINTER(ICAPI.IRunningObjectTable)()
        context = ct.POINTER(ICAPI.IBindCtx)()
        ole.GetRunningObjectTable.argtypes = [ct.c_ulong, ct.POINTER(type(rot))]
        ole.GetRunningObjectTable.restype = HRESULT
        ole.CreateBindCtx.argtypes = [ct.c_ulong, ct.POINTER(type(context))]
        ole.CreateBindCtx.restype = HRESULT
        ole.GetRunningObjectTable(0, ct.byref(rot))
        ole.CreateBindCtx(0, ct.byref(context))
        enumeration = rot.EnumRunning()
        while True:
            moniker, count = enumeration.RemoteNext(1)
            if not count:
                break
            try:
                name = moniker.GetDisplayName(context, None)
            except Exception:
                continue  # An unrelated ROT entry may disappear during enumeration.
            if not same_document_path(name, source):
                continue
            legacy = comtypes.client.GetBestInterface(rot.GetObject(moniker).QueryInterface(IDispatch))
            base = legacy.Application.ZIronCADApp.QueryInterface(ICAPI.IZBaseApp)
            document = base.GetOpenDocByName(str(source))
            # IZDoc.Name is the full saved filename in this API. A basename alone
            # cannot authorize a read of a similarly named document elsewhere.
            if not same_document_path(document.Name, source):
                raise SourceMismatchError("Open CAD document does not match the complete expected source path")
            return cls(legacy, base, document, ICAPI, source)
        raise RuntimeError("Expected source is not already open in the running object table")

    def provenance(self):
        name = str(self.document.Name)
        if not same_document_path(name, self.source):
            raise SourceMismatchError("CAD document identity changed during inventory")
        return {"document_path": name, "modified": bool(self.document.Modified),
                "file_guid": str(self.document.FileGUID), "connection": "existing_rot_only"}

    def root(self):
        return self.document.QueryInterface(self.api.IZSceneDoc).GetTopElement()

    def _element(self, node):
        return node.QueryInterface(self.api.IZElement)

    def identity(self, node):
        element = self._element(node)
        result = {"_read_errors": []}
        for field, attr in (("id", "Id"), ("name", "Name"), ("type", "Type")):
            try:
                result[field] = getattr(element, attr)
            except Exception as exc:
                result["_read_errors"].append({"field": field, "message": str(exc)})
        kind = result.get("type")
        result["kind"] = ("assembly" if kind == self.api.Z_ELEMENT_ASSEMBLY else
                          "part" if kind in (self.api.Z_ELEMENT_PART,
                                              self.api.Z_ELEMENT_SHEETMETAL_PART,
                                              self.api.Z_ELEMENT_FACET_PART,
                                              self.api.Z_ELEMENT_WIRE_PART,
                                              self.api.Z_ELEMENT_PROFILE_PART) else
                          "scene" if kind == self.api.Z_ELEMENT_UNKNOWN else
                          "feature" if kind in self._known_element_types else "unknown")
        return result

    def child_count(self, node):
        return self._element(node).GetChildrenCount()

    def child_at(self, node, index):
        return self._element(node).GetChildrenZArray().Get(index)

    def material_name(self, node):
        return self._element(node).GetMaterialNameProperty()

    def part_properties(self, node):
        part = node.QueryInterface(self.api.IZPart)
        result = {"_read_errors": []}
        fields = {"bom_number": lambda: part.BOMPartNumber,
                  "bom_description": lambda: part.BOMDescription,
                  "included": lambda: bool(part.IncludedInBOM),
                  "hidden": lambda: bool(part.IsHidden),
                  "bbox_raw": lambda: list(part.GetBoundingBox(True))}
        for field, read in fields.items():
            try:
                result[field] = read()
            except Exception as exc:
                result["_read_errors"].append({"field": field, "message": str(exc)})
        return result


def inspect_source(source, limits=None, event_sink=None, *, adapter_factory=None):
    """Hash before/after every attempted native read, even a failed attachment.

    Disk integrity is separate from the live document. Modified=true or a
    changed flag makes the result partial; unchanged hashes do not certify
    equivalence between disk bytes and in-memory geometry.
    """
    source = Path(source).resolve(strict=True)
    if not source.is_file() or source.suffix.lower() != ".ics":
        raise ValueError("source must be an existing ICS file")
    before = file_sha256(source)
    result = {"schema_version": 1, "operation": "parts.inspect", "read_only": True,
              "rows": [], "errors": [], "partial": True}
    integrity_failed = False
    try:
        adapter = (adapter_factory or NativePartsAdapter.attach)(source)
        provenance_before = adapter.provenance()
        result = read_parts(adapter, limits, event_sink)
        result["cad_document"] = {"before": provenance_before, "after": None,
                                  "disk_equivalence": "not_proven"}
        provenance_after = adapter.provenance()
        result["cad_document"] = {"before": provenance_before, "after": provenance_after,
                                  "disk_equivalence": "not_proven"}
        if (provenance_before.get("document_path") != provenance_after.get("document_path")
                or provenance_before.get("file_guid") != provenance_after.get("file_guid")):
            integrity_failed = True
            raise SourceMismatchError("CAD document path or GUID changed during inventory")
        if (provenance_before.get("modified") or provenance_after.get("modified")
                or provenance_before != provenance_after):
            result["partial"] = True
            result["errors"].append({"field": "cad_document", "type": "UnsavedOrChangedDocument",
                                     "message": "Live document has unsaved changes or changed metadata"})
    except Exception as exc:
        integrity_failed = True
        result["partial"] = True
        result["errors"].append({"field": "native_read", "type": type(exc).__name__, "message": str(exc)[:1000]})
    finally:
        try:
            after = file_sha256(source)
        except OSError as exc:
            after = None
            result["errors"].append({"field": "source_after", "type": type(exc).__name__, "message": str(exc)[:1000]})
        result["source"] = {"path": str(source), "sha256_before": before,
                            "sha256_after": after, "unchanged": before == after}
        if before != after:
            integrity_failed = True
            result["partial"] = True
            result["errors"].append({"field": "source", "type": "SourceChangedError",
                                     "message": "Source bytes changed during the read"})
    result["status"] = ("failed" if integrity_failed or not result["rows"] else
                        "partial" if result["partial"] else "complete")
    result["scope"] = "assembly_part_hierarchy"
    if "summary" in result:
        result["summary"]["error_count"] = len(result["errors"])
    return result
