"""Read-only ICAPI metadata inventory; never loads an assembly or activates CAD."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


API_MAJOR = {2023: 25, 2027: 29}
# Verified local TLB snapshots, not a general claim about every service pack.
TLB_SNAPSHOTS = {
    2023: '612cdbb9ba69f0b70a0222dd9a2c25b043e97e1595beeeb6a093bfa2ba89ca6f',
    2027: 'a4a07be678226ecbdb3fc217bd21dc34eacaaa3d80676f626cf2147f6420b982',
}
PREFIX = 'interop.ICApiIronCAD.'
MAX_JSON_BYTES = 16 * 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024
# Exact signatures: an unrelated overload or unknown JSON flag cannot satisfy a requirement.
CAPABILITIES = {
    'parameters_transforms': [
        ('IZParameterMgr', 'interop.ICApiIronCAD.ZParameter CreateParameter(interop.ICApiIronCAD.eZParamType, System.String, Double)'),
        ('IZParameter', 'Void set_Expression(System.String)'),
        ('IZSceneElement', 'Void ForceSetupParameterExpression()'),
        ('IZSceneElement', 'Void SetTransformToParent(interop.ICApiIronCAD.ZMathMatrix)'),
        ('IZSceneElement', 'Void set_PositionTransformComponentExpression(interop.ICApiIronCAD.eZTransformComponentType, System.String)'),
    ],
    'subtract': [
        ('IZPartFeatureMgr', 'interop.ICApiIronCAD.ZExtrudeFeature CreateExtrudeFeature(interop.ICApiIronCAD.eZOperationType, Boolean, Double, Double, Double, interop.ICApiIronCAD.IZProfile, interop.ICApiIronCAD.eZFeatureProfileRelType)'),
        ('IZFeature', 'Void set_OperationType(interop.ICApiIronCAD.eZOperationType)'),
    ],
    'drawings': [
        ('IZDrawingDoc', 'interop.ICApiIronCAD.ZTDSheet AddSheet(Boolean, System.String)'),
        ('IZTDSheet', 'interop.ICApiIronCAD.ZTDView CreateStandardTDView(interop.ICApiIronCAD.IZSceneDoc, Int32, interop.ICApiIronCAD.eZTDViewType, System.Object, System.Object)'),
        ('IZTDExportControl', 'Void ExportSheet(interop.ICApiIronCAD.ZTDSheet, System.String, interop.ICApiIronCAD.eZExportDrawingType)'),
    ],
    'bom': [('IZBOMManager', 'Void ExportBOMAsTabDelimText(interop.ICApiIronCAD.ZBOMTableDefinition, System.String)')],
    'pdf': [('IZTDPDFExportManager', 'Void ExportDrawing(System.String)')],
    'animation_playback': [('IZAnimationMgr', 'Void Play(Double ByRef, Double ByRef)')],
    'bulk29': [
        ('IZDrawingDoc', 'interop.ICApiIronCAD.ZTDSheet AddSheetWithLayoutForBulkViewCreation(System.String, System.String, System.String, UInt32, UInt32)'),
        ('IZTDExportControl', 'Void SetExportDxfDwgMarkedViewsOnly(Boolean)'),
    ],
}


class EvidenceError(ValueError):
    pass


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(HASH_CHUNK_BYTES), b''):
            result.update(chunk)
    return result.hexdigest()


def read_json_snapshot(path: Path) -> tuple[dict, str]:
    """Parse and hash the same bounded byte snapshot, never reopen it for either step."""
    with path.open('rb') as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise EvidenceError(f'JSON exceeds {MAX_JSON_BYTES} bytes: {path}')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise EvidenceError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise EvidenceError(f'Expected JSON object: {path}')
    return value, hashlib.sha256(raw).hexdigest()


def read_json(path: Path) -> dict:
    return read_json_snapshot(path)[0]


def verify_digest(path: Path, actual: str, expected: object) -> str:
    if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', expected):
        raise EvidenceError(f'Invalid SHA256 for {path}')
    if actual != expected.lower():
        raise EvidenceError(f'SHA256 mismatch: {path}')
    return actual


def checked_hash(path: Path, expected: object) -> str:
    return verify_digest(path, digest(path), expected)


def evidence_path(evidence: dict, key: str, base: Path) -> Path:
    value = evidence.get(key)
    if not isinstance(value, str) or not value:
        raise EvidenceError(f'Missing path: {key}')
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve(strict=True)


def inspect_host(year: int, metadata_path: Path, evidence_file: Path) -> dict:
    """Verify supplied local bytes and inspect allowlisted signatures, not runtime support."""
    if year not in API_MAJOR:
        raise EvidenceError('Host year must be 2023 or 2027')
    evidence, evidence_hash = read_json_snapshot(evidence_file)
    if type(evidence.get('schema_version')) is not int or evidence['schema_version'] != 1:
        raise EvidenceError('Unsupported evidence schema')
    if type(evidence.get('host_year')) is not int or evidence['host_year'] != year:
        raise EvidenceError('Host year mismatch')
    if type(evidence.get('api_major')) is not int or evidence['api_major'] != API_MAJOR[year]:
        raise EvidenceError('API major mismatch')
    metadata, metadata_hash = read_json_snapshot(metadata_path)
    verify_digest(metadata_path, metadata_hash, evidence.get('metadata_sha256'))
    interop = evidence_path(evidence, 'interop_path', evidence_file.parent)
    tlb = evidence_path(evidence, 'tlb_path', evidence_file.parent)
    interop_hash = checked_hash(interop, evidence.get('interop_sha256'))
    tlb_hash = checked_hash(tlb, evidence.get('tlb_sha256'))
    if tlb_hash != TLB_SNAPSHOTS[year]:
        raise EvidenceError('TLB digest is not the verified snapshot for this host year')
    if not isinstance(metadata.get('sha256'), str) or metadata['sha256'].lower() != interop_hash:
        raise EvidenceError('Metadata does not identify the supplied interop digest')
    if not isinstance(metadata.get('library'), str) or Path(metadata['library']).resolve() != interop:
        raise EvidenceError('Metadata library path mismatch')
    if not isinstance(metadata.get('assembly'), str):
        raise EvidenceError('Missing assembly identity')
    version = re.fullmatch(
        r'interop\.ICApiIronCAD, Version=(\d+)\.0\.0\.0, Culture=neutral, PublicKeyToken=(?:null|[0-9a-fA-F]+)',
        metadata.get('assembly', ''),
    )
    if not version or int(version[1]) != API_MAJOR[year]:
        raise EvidenceError('Assembly version does not match requested host')
    if not isinstance(metadata.get('types'), list):
        raise EvidenceError('Missing types array')
    types = {}
    for item in metadata['types']:
        if not isinstance(item, dict) or not isinstance(item.get('name'), str):
            raise EvidenceError('Malformed type record')
        if item['name'] in types:
            raise EvidenceError('Duplicate type record')
        methods = item.get('methods')
        if not isinstance(methods, list) or any(not isinstance(m, str) for m in methods):
            raise EvidenceError('Malformed methods array')
        types[item['name']] = set(methods)
    rows = {}
    for name, requirements in CAPABILITIES.items():
        found, missing = [], []
        for interface, signature in requirements:
            target = PREFIX + interface
            row = {'interface': target, 'signature': signature}
            if signature in types.get(target, set()):
                found.append(row)
            else:
                row['reason'] = 'interface_not_recorded' if target not in types else 'signature_not_recorded'
                missing.append(row)
        # The saved reflection probe captured interfaces, not enum constants. Do not fabricate Z_SUBTRACT evidence.
        limitations = ['Runtime behavior and adapter integration require a native test.']
        if name == 'subtract':
            limitations.append('Z_SUBTRACT enum value was not captured by this metadata schema; methods alone do not prove subtraction semantics.')
        if name == 'animation_playback':
            limitations.append('Playback signature does not prove creation of animation paths or a valid hinge axis.')
        rows[name] = {
            'metadata_status': 'methods_present' if not missing else 'missing_metadata',
            'found': found, 'missing': missing, 'native_status': 'NOT RUN',
            'runtime_supported': None, 'automatic_fallback': False,
            'limitations': limitations,
        }
    return {
        'host_year': year, 'api_major': API_MAJOR[year], 'assembly': metadata['assembly'],
        'metadata_path': str(metadata_path.resolve()), 'metadata_sha256': metadata_hash,
        'interop_path': str(interop), 'interop_sha256': interop_hash,
        'tlb_path': str(tlb), 'tlb_sha256': tlb_hash,
        'evidence_sha256': evidence_hash, 'native_status': 'NOT RUN',
        'provenance_limit': 'Digests verify supplied bytes; this reader does not re-import TLB, authenticate vendor signatures or prove that the interop was derived from that TLB.',
        'capabilities': rows,
    }


def make_report(host2023: dict, host2027: dict) -> dict:
    if host2023['host_year'] != 2023 or host2027['host_year'] != 2027:
        raise EvidenceError('Comparison requires exactly hosts 2023 and 2027')
    groups = {'common_methods_present': [], 'only_25_recorded': [], 'only_29_recorded': [], 'incomplete_both': []}
    for name in CAPABILITIES:
        a = host2023['capabilities'][name]['metadata_status'] == 'methods_present'
        b = host2027['capabilities'][name]['metadata_status'] == 'methods_present'
        key = 'common_methods_present' if a and b else 'only_25_recorded' if a else 'only_29_recorded' if b else 'incomplete_both'
        groups[key].append(name)
    return {'schema_version': 1, 'kind': 'offline_icapi_metadata_report',
            'hosts': [host2023, host2027], 'comparison': groups,
            'requires_native_test': list(CAPABILITIES), 'native_status': 'NOT RUN',
            'warning': 'Presence in metadata is not runtime support. Absence is missing evidence, not proof of API absence or permission to select a fallback.'}


def markdown(report: dict) -> str:
    lines = ['# ICAPI — zdolności odnotowane w metadanych', '',
             'Raport odczytowy. **Natywnie: NOT RUN.** Obecność metody nie oznacza działającej integracji.', '',
             '| Grupa | 2023 / API 25 | 2027 / API 29 | Próba hosta |', '|---|---|---|---|']
    for name in CAPABILITIES:
        statuses = [host['capabilities'][name]['metadata_status'] for host in report['hosts']]
        lines.append(f'| {name} | {statuses[0]} | {statuses[1]} | NOT RUN |')
    lines += ['', '## Porównanie']
    for key, values in report['comparison'].items():
        lines += ['', f'- {key}: {", ".join(values) or "brak"}']
    lines += ['', '„only” oznacza wyłącznie zarejestrowany komplet sygnatur, nie dowód niedostępności na drugim hoście.',
              'Brak metody nie uruchamia fallbacku. Wszystkie grupy wymagają próby natywnej.',
              'Dla subtract nie zapisano wartości enum Z_SUBTRACT; dla animacji nie potwierdzono kreatora ścieżek.',
              'Skróty sprawdzają integralność dostarczonych plików, nie autentyczność SDK ani pochodzenie interop z TLB.']
    for host in report['hosts']:
        lines += ['', f'## Dowody {host["host_year"]}', '', f'- Assembly: `{host["assembly"]}`']
        for key in ('metadata_sha256', 'interop_sha256', 'tlb_sha256', 'evidence_sha256'):
            lines.append(f'- {key}: `{host[key]}`')
    return '\n'.join(lines) + '\n'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for year in API_MAJOR:
        parser.add_argument(f'--metadata-{year}', type=Path, required=True)
        parser.add_argument(f'--evidence-{year}', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        hosts = [inspect_host(year, getattr(args, f'metadata_{year}'), getattr(args, f'evidence_{year}')) for year in API_MAJOR]
        report = make_report(*hosts)
        # Refuse an existing destination, preserving previous reports and all source evidence.
        args.output_dir.mkdir(parents=True, exist_ok=False)
        (args.output_dir / 'capabilities.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (args.output_dir / 'capabilities.md').write_text(markdown(report), encoding='utf-8')
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f'Capability report refused: {exc}\n')
    print(json.dumps({'output_dir': str(args.output_dir), 'native_status': 'NOT RUN'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
