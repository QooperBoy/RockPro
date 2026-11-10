"""Local favorites and distinct saved-project selection history, separate from stock."""
import json
from .mcp import project_store


def _ensure(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS studio_part_preferences (
        part_id TEXT PRIMARY KEY, favorite INTEGER NOT NULL CHECK(favorite IN (0,1)),
        updated_at TEXT NOT NULL)''')


def read(known_ids):
    with project_store.db() as conn:
        _ensure(conn)
        result={r['part_id']:dict(favorite=bool(r['favorite']),project_count=0,last_used=None)
                for r in conn.execute('SELECT * FROM studio_part_preferences') if r['part_id'] in known_ids}
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        records=[]
        if 'configurator_draft_versions' in tables:
            records+=list(conn.execute('SELECT id,payload,created_at AS stamp FROM configurator_draft_versions'))
        if 'configurator_drafts' in tables:
            records+=list(conn.execute('SELECT id,payload,updated_at AS stamp FROM configurator_drafts'))
        projects={}
        for record in records:
            try:payload=json.loads(record['payload'])
            except (ValueError,TypeError) as exc:raise ValueError('Nie można odczytać historii wyboru części') from exc
            if not isinstance(payload,dict):raise ValueError('Nieprawidłowa historia projektu')
            hardware=payload.get('hardware',[])
            if not isinstance(hardware,list):raise ValueError('Nieprawidłowa lista części w historii')
            for part in hardware:
                if not isinstance(part,dict) or not isinstance(part.get('part_id'),str):raise ValueError('Nieprawidłowa część w historii')
                key=part['part_id']
                if key not in known_ids:continue
                projects.setdefault(key,set()).add(record['id'])
                stat=result.setdefault(key,dict(favorite=False,project_count=0,last_used=None))
                stat['last_used']=max(stat['last_used'] or '',record['stamp'])
        for key,ids in projects.items():result[key]['project_count']=len(ids)
    return dict(items=result,usage_basis='distinct_saved_projects_across_revisions',scope='local_workspace')


def set_favorite(command,known_ids):
    if (not isinstance(command,dict) or set(command)!={'part_id','favorite'}
            or not isinstance(command['part_id'],str) or command['part_id'] not in known_ids
            or type(command['favorite']) is not bool):
        raise ValueError('Wybierz znaną część i jawny stan ulubionej')
    with project_store.db() as conn:
        _ensure(conn)
        conn.execute('''INSERT INTO studio_part_preferences VALUES (?,?,?)
            ON CONFLICT(part_id) DO UPDATE SET favorite=excluded.favorite,updated_at=excluded.updated_at''',
            (command['part_id'],int(command['favorite']),project_store.now()))
    return read(known_ids)
