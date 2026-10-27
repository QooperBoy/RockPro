"""Serialize the fixed T1 structure job with other chats using the same host."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.cad_lock import cad_writer_lock, CadBusyError
from run_t1_machining_job import run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('request',type=Path)
    parser.add_argument('--wait-seconds',type=float,default=180)
    args=parser.parse_args()
    req=json.loads(args.request.read_text(encoding='utf-8-sig'))
    if req.get('contract')!='rockpro-t1-structure-v1':raise ValueError('Wrong T1 structure contract')
    deadline=time.monotonic()+args.wait_seconds
    announced=False
    while True:
        try:
            with cad_writer_lock():
                run(args.output,ROOT/'scripts/native/T1HingeStructure2023.cs',req)
                return 0
        except CadBusyError:
            if time.monotonic()>=deadline:raise
            if not announced:
                print('Czekam na zakończenie innej operacji CAD; blokada pozostaje aktywna.',flush=True)
                announced=True
            time.sleep(2)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
