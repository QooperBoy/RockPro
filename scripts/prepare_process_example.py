"""Store an explicitly simulated process on a new generic Studio draft, never CAD."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad import configurator, studio_examples, process_runs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path)
    args=parser.parse_args()
    if args.database:
        from rockpro_cad.mcp import project_store
        project_store.DB_PATH=args.database.resolve()
    draft=studio_examples.catalog()['items'][0]['draft']
    draft['name']='DEMO pomiaru SDK / AI — symulacja 270 + 30'
    saved=configurator.save_draft(draft)
    items=configurator.preview(draft)['placement']['items']
    handles=[r for r in items if r['part_id']=='H7159']
    run=process_runs.create(saved['id'],saved['revision'],'270 standard + 30 AI — przykład','simulation')
    events=[dict(event_id='reason',kind='intervention',operation_id='new-handle',stage='handles',
        label='Nowy wariant uchwytu — przykład',reason='SYMULACJA: brak mapy otworu nowego wariantu. Agent przygotowuje kotwę i wycięcie do kontroli.',
        origin='ai',executor='agent',part_id='H7159',status='resolved')]
    for i in range(300):
        e=dict(event_id=f'op-{i}',operation_id=f'op-{i}',kind='operation',stage='structure' if i<270 else 'handles',
            label=f'Przykładowa operacja {i+1}',status='success',origin='standard' if i<270 else 'ai',executor='sdk',
            occurrence_id=handles[1 if i<270 else 0]['id'],part_id='H7159',duration_ms=2)
        if i>=270:e['intervention_id']='new-handle'
        events.append(e)
    process_runs.append(run['id'],events,state='completed')
    print(json.dumps(dict(draft_id=saved['id'],run_id=run['id'],mode='simulation'),ensure_ascii=False))


if __name__=='__main__':main()
