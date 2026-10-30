"""Pinned IronCAD 2027 helper. Prepare a copy, then edit portable row parameters."""
from __future__ import annotations
import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
WALLS = {"przod": 1, "tyl": 2, "lewa": 3, "prawa": 4, "gora": 5, "dno": 6}
BODY = {1:11175, 2:11208, 3:11201, 4:11194, 6:11227}
CAP = {1:11131, 2:11158, 3:11151, 4:11144, 5:11171}
UPPER = {1:11271, 2:11231, 3:228, 4:231}
LOWER = {1:11333, 2:11311, 3:241, 4:244}

def migration_request(source: Path, output: Path, controller: Path, pid: int, stamp: str):
    project = source.parents[2]
    owners = {str(i):10 for i in BODY.values()}
    owners.update({str(i):11 for i in CAP.values()})
    owners.update({str(i):2 for i in UPPER.values()})
    owners.update({str(i):3 for i in LOWER.values()})
    # Stable whole-hardware IDs in the pinned R002/R004 revision; labels are not keys.
    obstacles = [dict(id=i, wall=w) for i,w in [(1235,1),(1329,1),(1376,1),(1540,2),(1634,2),(1587,2),
        (1389,1),(1342,1),(1248,1),(1600,2),(1647,2),(1553,2),(8635,1),(8664,1),(8867,2),(8896,2)]]
    return dict(contract='rockpro-tv-wall-migration-v1',expected_pid=pid,source=str(source),output=str(output),
        snapshot=str(project/'04_Snapshoty'/f'RockPro_przed_remap_{stamp}.ics'),controller=str(controller),
        wall_targets={'1':BODY,'2':CAP},owner_roles=owners,
        role_targets={0:{**{f'1/{w}':i for w,i in BODY.items()},**{f'2/{w}':i for w,i in CAP.items()}},10:BODY,11:CAP,2:UPPER,3:LOWER},obstacles=obstacles)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    prepare=sub.add_parser('prepare',help='Create a new wall-mapped copy of the known R004 Hisense case')
    prepare.add_argument('--source',type=Path,required=True);prepare.add_argument('--output',type=Path,required=True)
    edit=sub.add_parser('set',help='Set a portable row on the open mapped copy; the running add-in performs the remap')
    edit.add_argument('--model',type=Path,required=True);edit.add_argument('--row',choices=['UchwytyA','UchwytyB','UchwytyC','UchwytyD','ZamkiA','ZamkiB'],required=True)
    edit.add_argument('--wall',choices=WALLS);edit.add_argument('--section',type=int,choices=(1,2));edit.add_argument('--count',type=int,choices=range(5));edit.add_argument('--u',type=float);edit.add_argument('--v',type=float);edit.add_argument('--spread',type=float)
    parser.add_argument('--pid',type=int,help='Optional explicit host guard; otherwise detect the sole 2027 instance')
    args=parser.parse_args()
    if args.pid is None:
        host=subprocess.run(['powershell.exe','-NoProfile','-Command',
            "@(Get-Process IRONCAD -ErrorAction SilentlyContinue | Where-Object {$_.Path -like '*\\2027\\bin\\IRONCAD.exe'} | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress"],capture_output=True,text=True,check=True)
        pids=json.loads(host.stdout.strip() or '[]')
        pids=pids if isinstance(pids,list) else [pids]
        if len(pids)!=1:parser.error('Expected exactly one IronCAD 2027 instance; no CAD operation started.')
        args.pid=pids[0]
    if args.command=='set' and any(v is not None and not math.isfinite(v) for v in (args.u,args.v,args.spread)):
        parser.error('Mounting dimensions must be finite numbers.')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence=ROOT/'artifacts'/f'tv-wall-mounts-{stamp}'
    controller=ROOT/'Integracja/rockpro_cad/addin/bin-counts-v10f-2027/RockPro.MountCounts.dll'
    if args.command=='prepare':
        if args.output.exists():parser.error('Output exists; choose a new copy.')
        request=migration_request(args.source.resolve(),args.output.resolve(),controller,args.pid,stamp)
        script=ROOT/'scripts/native/PrepareTvWallMounts2027.cs'
    else:
        if args.row.startswith('Zamki') and (args.wall in ('gora','dno') or args.section is not None):parser.error('Latch rows require a vertical body/cap joint, without a section selector.')
        changes={};prefix=f'RP_{args.row}_'
        for value,name in [(WALLS.get(args.wall),'Sciana'),(args.section,'Sekcja'),(args.count,'Liczba')]:
            if value is not None:changes[prefix+name]=str(value)
        for value,name in [(args.u,'SrodekU'),(args.v,'Pion' if args.row.startswith('Zamki') else 'PozycjaV'),(args.spread,'Rozstaw')]:
            if value is not None:changes[prefix+name]=f'{value:.12g} mm'
        if not changes:parser.error('Specify parameters to change.')
        request=dict(contract='rockpro-tv-wall-edit-v1',expected_pid=args.pid,model=str(args.model.resolve()),changes=changes)
        script=ROOT/'scripts/native/SetTvWallMounts2027.cs'
    request_path=ROOT/'artifacts'/f'tv-wall-request-{stamp}.json';request_path.write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
    env=dict(os.environ,ROCKPRO_IRONCAD_YEAR='2027')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/run_t1_machining_job.py'),str(evidence),str(script),str(request_path)],cwd=ROOT,env=env)
    print('Evidence:',evidence)
    return result.returncode
if __name__=='__main__':raise SystemExit(main())
