"""Migrate one measured legacy Studio T1 to editable accessory parameters.

--run explicitly creates and saves a new model through the single-writer SDK
runner. Original models, Studio drafts and the shared database are untouched.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.accessory_parameters import migrate, with_checks, regroup_saved_copy


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--inventory',type=Path)
    parser.add_argument('--receipt',type=Path,help='Kwit zapisanej kopii: zmień tylko jej grupy na Wieko 1 i Podstawa')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if args.output.exists(): parser.error('Katalog wyjściowy nie może istnieć')
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    if args.receipt:
        spec=regroup_saved_copy(read(args.request),read(args.receipt))
    else:
        if not args.inventory:parser.error('Wymagany --inventory albo --receipt')
        spec=with_checks(migrate(read(args.request),read(args.inventory)))
    spec.update(expected_pid=args.pid,save_output=True,show_final=True,
                output_filename='RockPro_T1_parametry_osprzetu.ics')
    source=ROOT/'scripts/native/StudioCad2027.cs'
    runner=ROOT/'scripts/run_t1_machining_job.py'
    spec['executor_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    spec['runner_sha256']=hashlib.sha256(runner.read_bytes()).hexdigest()
    spec['migration_evidence']={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.request,args.inventory,args.receipt) if p is not None}
    target=args.output.with_name(args.output.name+'-request.json')
    with target.open('x',encoding='utf-8') as stream:
        json.dump(spec,stream,ensure_ascii=False,allow_nan=False,indent=2)
    print(json.dumps(dict(request=str(target),parameters=len(spec['parameters']),check_cases=[x['name'] for x in spec['check_cases']]),ensure_ascii=False))
    if args.run:
        os.environ['ROCKPRO_IRONCAD_YEAR']='2027'
        from run_t1_machining_job import run
        run(args.output,source,spec)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
