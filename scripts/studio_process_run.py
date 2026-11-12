"""Record explicit process provenance in Studio; never executes a model or AI itself."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Integracja'))
from rockpro_cad import process_runs
from rockpro_cad.auto_run import decision_event,studio_database


def all_runs(only_open=False):
    from rockpro_cad.mcp import project_store
    with project_store.db() as conn:
        process_runs._tables(conn)
        rows=conn.execute('SELECT payload FROM studio_process_runs ORDER BY created_at').fetchall()
    runs=[json.loads(r['payload']) for r in rows]
    return [r for r in runs if r['state']=='running'] if only_open else runs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,default=studio_database(),
        help='Studio SQLite; same file as reference_studio --database (default: ROCKPRO_STUDIO_DATABASE or artifacts/studio.sqlite)')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('start');p.add_argument('draft_id');p.add_argument('revision',type=int);p.add_argument('label')
    p=sub.add_parser('append');p.add_argument('run_id');p.add_argument('events',type=Path)
    p=sub.add_parser('decide',help='record an AI decision (intervention) with its reason, now')
    p.add_argument('run_id');p.add_argument('decision_id');p.add_argument('reason')
    p.add_argument('--stage',default='native');p.add_argument('--label',default='AI decision')
    p=sub.add_parser('finish');p.add_argument('run_id');p.add_argument('state',choices=['completed','partial','failed'])
    p=sub.add_parser('list',help='list runs, oldest first (--open: only runs that were never closed)')
    p.add_argument('--open',action='store_true')
    p=sub.add_parser('export');p.add_argument('run_id');p.add_argument('output',type=Path)
    args=parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    from rockpro_cad.mcp import project_store
    project_store.DB_PATH=args.database.resolve()
    if args.command=='start':result=process_runs.create(args.draft_id,args.revision,args.label)
    elif args.command=='append':result=process_runs.append(args.run_id,json.loads(args.events.read_text(encoding='utf-8-sig')))
    elif args.command=='decide':
        result=process_runs.append(args.run_id,[decision_event(args.decision_id,args.reason,args.stage,args.label)])
    elif args.command=='finish':result=process_runs.append(args.run_id,state=args.state)
    elif args.command=='list':
        now=datetime.now(timezone.utc)
        for r in all_runs(args.open):
            age=(now-datetime.fromisoformat(r['created_at'].replace('Z','+00:00'))).total_seconds()/3600
            print(f"{r['id']}  {r['state']:<9}  {r['created_at'][:19]}Z  {age:6.1f} h  {len(r['events']):4} events  {r['label']}")
        return
    else:
        result=process_runs.read(args.run_id)
        with args.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
