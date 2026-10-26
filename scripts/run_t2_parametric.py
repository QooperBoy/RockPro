"""Queue one T2 operation before touching COM; never retry a dispatched job."""
import argparse
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.cad_lock import cad_writer_lock, CadBusyError
from run_t1_machining_job import run


def execute(folder, request, wait_seconds=180):
    if request.get('contract')!='rockpro-t2-parametric-prototype-v1':raise ValueError('Unsupported T2 contract')
    deadline=time.monotonic()+wait_seconds
    cancel=Path(str(folder)+'.cancel')
    print('T2: oczekiwanie na wspólnego wykonawcę CAD',flush=True)
    while True:
        if cancel.exists():raise RuntimeError('T2 queue cancelled before CAD dispatch')
        try:
            lock=cad_writer_lock()
            lock.__enter__()
        except CadBusyError:
            if time.monotonic()>=deadline:raise
            time.sleep(3)
            continue
        break
    try:
        if cancel.exists():raise RuntimeError('T2 queue cancelled before CAD dispatch')
        print('T2: blokada CAD przejęta; pojedyncze wykonanie',flush=True)
        return run(folder,ROOT/'scripts/native/T2ParametricPrototype.cs',request)
    finally:lock.__exit__(None,None,None)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('request',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--wait-seconds',type=float,default=180);args=parser.parse_args()
    execute(args.output,json.loads(args.request.read_text(encoding='utf-8-sig')),args.wait_seconds)
