"""Private, provenance-pinned survey. Does not create executable CAD templates."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_member_name(name):
    """Reject paths that alias other files or streams on the Windows CAD host."""
    if not isinstance(name,str) or not name or '\\' in name:
        raise ValueError('Unsafe member path')
    for part in name.split('/'):
        if (part in ('','.','..') or part.rstrip(' .')!=part or
                any(ord(c)<32 or c in '<>:"|?*' for c in part) or
                re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?',part,re.I)):
            raise ValueError('Unsafe member path')
    return name


def archive_members(package):
    """Validate the whole archive before any member can be staged."""
    members={};seen=set()
    for entry in package.infolist():
        name=safe_member_name(entry.filename.rstrip('/') if entry.is_dir() else entry.filename)
        if stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Symlink archive member refused')
        if entry.is_dir():continue
        if name.casefold() in seen:raise ValueError('Duplicate or aliased archive member')
        seen.add(name.casefold());members[name]=entry
    for name in seen:
        pieces=name.split('/')
        if any('/'.join(pieces[:i]) in seen for i in range(1,len(pieces))):
            raise ValueError('Archive member is also a parent directory')
    return members


def prepare(folder, archive, output):
    folder, archive, output = map(Path, (folder, archive, output))
    files = sorted(folder.rglob('*'), key=lambda p: str(p).casefold())
    files = [p for p in files if p.is_file()]
    if not files or any(p.is_symlink() for p in files):
        raise ValueError('Expected regular extracted source files')
    archive_sha256=sha(archive)
    models = []
    extracted = {}
    for p in files:
        relative = safe_member_name(p.relative_to(folder).as_posix())
        extracted[relative] = {'bytes': p.stat().st_size, 'sha256': sha(p)}
        if p.suffix.casefold() == '.ics':
            models.append({'key': f'M{len(models)+1:02d}', 'source': str(p.resolve()),
                           'sha256': extracted[relative]['sha256'], 'name': p.name})
    zipped = {}
    with zipfile.ZipFile(archive) as package:
        for entry in archive_members(package).values():
            with package.open(entry) as stream:
                zipped[entry.filename] = {'bytes': entry.file_size,
                    'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
    if zipped != extracted:
        raise ValueError('Archive and extracted files do not match exactly')
    if sha(archive)!=archive_sha256:raise ValueError('Archive revision changed during survey')
    if not models:raise ValueError('Expected at least one ICS model')
    manifest = {'contract': 'rockpro-model-survey-v1', 'archive': str(archive.resolve()),
                'archive_sha256': archive_sha256, 'archive_matches_extracted': True,
                'files': extracted, 'models': models, 'production_approved': False}
    output.mkdir(parents=True, exist_ok=False)
    (output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = prepare(args.folder, args.archive, args.output)
    print(json.dumps({'models': len(result['models']), 'archive_matches_extracted': True}))
