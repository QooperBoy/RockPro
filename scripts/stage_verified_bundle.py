"""Stage original ZIP members into a new private directory without overwriting work."""
import argparse
import json
from pathlib import Path
import shutil
import zipfile
from survey_model_bundle import sha


def stage(manifest_path, destination):
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    archive=Path(manifest['archive'])
    if sha(archive)!=manifest['archive_sha256']:raise ValueError('Archive revision changed')
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(archive) as package:
        for name,expected in manifest['files'].items():
            relative=Path(name)
            if relative.anchor or '..' in relative.parts:
                raise ValueError('Unsafe member path')
            target=destination/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            with package.open(name) as source,target.open('xb') as out:shutil.copyfileobj(source,out)
            if target.stat().st_size!=expected['bytes'] or sha(target)!=expected['sha256']:
                raise ValueError('Staged bytes differ from original source revision')
    return destination


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();print(stage(a.manifest,a.destination))
