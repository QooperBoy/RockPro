"""Serialize the read-only bundle survey in an explicitly selected existing host."""
import argparse
import json
import os
from pathlib import Path
from run_t1_machining_job import ROOT, run
from rockpro_cad.cad_lock import cad_writer_lock


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--context',type=Path)
    p.add_argument('--pid',type=int,required=True)
    p.add_argument('--year',type=int,choices=(2023,2027),required=True)
    p.add_argument('--preview-only',action='store_true')
    p.add_argument('--only',action='append',help='One manifest model key, repeatable')
    p.add_argument('--keep-open',action='store_true',help='Explicit user review: open visible copies and leave successes open')
    p.add_argument('--writable-copy',action='store_true',help='Diagnose host open mode on an owned copy; never saves CAD')
    a=p.parse_args()
    if not a.output.resolve().is_relative_to((ROOT/'artifacts').resolve()):
        p.error('Private output must be inside artifacts/')
    manifest=json.loads(a.manifest.read_text(encoding='utf-8'))
    if manifest.get('contract')!='rockpro-model-survey-v1' or not manifest.get('archive_matches_extracted'):
        p.error('Verified source manifest required')
    os.environ['ROCKPRO_IRONCAD_YEAR']=str(a.year)
    models=manifest['models']
    if a.only:
        if set(a.only)-{m['key'] for m in models}:p.error('Unknown model key')
        models=[m for m in models if m['key'] in a.only]
    request={'expected_pid':a.pid,'models':models,'preview_only':a.preview_only,'keep_open':a.keep_open,'writable_copy':a.writable_copy}
    if a.context:request['context_path']=str(a.context.resolve(strict=True))
    with cad_writer_lock():
        run(a.output,ROOT/'scripts/native/BundleModelSurvey.cs',request)


if __name__=='__main__':main()
