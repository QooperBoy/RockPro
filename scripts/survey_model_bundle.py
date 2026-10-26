"""Private, provenance-pinned survey. Does not create executable CAD templates."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare(folder, archive, output):
    folder, archive, output = map(Path, (folder, archive, output))
    files = sorted(folder.rglob('*'), key=lambda p: str(p).casefold())
    files = [p for p in files if p.is_file()]
    if not files or any(p.is_symlink() for p in files):
        raise ValueError('Expected regular extracted source files')
    output.mkdir(parents=True, exist_ok=False)
    models = []
    extracted = {}
    for p in files:
        relative = p.relative_to(folder).as_posix()
        extracted[relative] = {'bytes': p.stat().st_size, 'sha256': sha(p)}
        if p.suffix.casefold() == '.ics':
            models.append({'key': f'M{len(models)+1:02d}', 'source': str(p.resolve()),
                           'sha256': extracted[relative]['sha256'], 'name': p.name})
    zipped = {}
    with zipfile.ZipFile(archive) as package:
        for entry in package.infolist():
            if entry.is_dir():
                continue
            if entry.filename in zipped:
                raise ValueError('Duplicate archive member')
            with package.open(entry) as stream:
                zipped[entry.filename] = {'bytes': entry.file_size,
                    'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
    if zipped != extracted:
        raise ValueError('Archive and extracted files do not match exactly')
    manifest = {'contract': 'rockpro-model-survey-v1', 'archive': str(archive.resolve()),
                'archive_sha256': sha(archive), 'archive_matches_extracted': True,
                'files': extracted, 'models': models, 'production_approved': False}
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
