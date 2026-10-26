"""Stage original ZIP members into a new private directory without overwriting work."""
import argparse
import json
from pathlib import Path
import re
import shutil
import zipfile
from survey_model_bundle import archive_members, safe_member_name, sha


def stage(manifest_path, destination):
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if manifest.get('contract')!='rockpro-model-survey-v1' or manifest.get('archive_matches_extracted') is not True:
        raise ValueError('Verified bundle manifest required')
    archive=Path(manifest['archive'])
    if sha(archive)!=manifest['archive_sha256']:raise ValueError('Archive revision changed')
    destination=Path(destination)
    with zipfile.ZipFile(archive) as package:
        members=archive_members(package)
        if not isinstance(manifest.get('files'),dict) or not members or members.keys()!=manifest['files'].keys():
            raise ValueError('Manifest must account for every archive member')
        for name,expected in manifest['files'].items():
            safe_member_name(name)
            if (not isinstance(expected,dict) or type(expected.get('bytes')) is not int or
                    expected['bytes']<0 or expected['bytes']!=members[name].file_size or
                    not isinstance(expected.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',expected['sha256'])):
                raise ValueError('Exact member size and SHA256 required')
        destination.mkdir(parents=True,exist_ok=False)
        for name,expected in manifest['files'].items():
            relative=Path(name)
            if relative.anchor or '..' in relative.parts:
                raise ValueError('Unsafe member path')
            target=destination/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            with package.open(members[name]) as source,target.open('xb') as out:shutil.copyfileobj(source,out)
            if target.stat().st_size!=expected['bytes'] or sha(target)!=expected['sha256']:
                raise ValueError('Staged bytes differ from original source revision')
    if sha(archive)!=manifest['archive_sha256']:raise ValueError('Archive revision changed during staging')
    return destination


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();print(stage(a.manifest,a.destination))
