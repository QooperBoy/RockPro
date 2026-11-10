"""Record explicit process provenance in Studio; never executes a model or AI itself."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Integracja'))
from rockpro_cad import process_runs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('start');p.add_argument('draft_id');p.add_argument('revision',type=int);p.add_argument('label')
    p=sub.add_parser('append');p.add_argument('run_id');p.add_argument('events',type=Path)
    p=sub.add_parser('finish');p.add_argument('run_id');p.add_argument('state',choices=['completed','partial','failed'])
    p=sub.add_parser('export');p.add_argument('run_id');p.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.command=='start':result=process_runs.create(args.draft_id,args.revision,args.label)
    elif args.command=='append':result=process_runs.append(args.run_id,json.loads(args.events.read_text(encoding='utf-8-sig')))
    elif args.command=='finish':result=process_runs.append(args.run_id,state=args.state)
    else:
        result=process_runs.read(args.run_id)
        with args.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
