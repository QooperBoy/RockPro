"""Local project registry. Workflow statuses are manual records, never CAD validation."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1]/"data"/"projects.sqlite3"
STAGES = [("inquiry","Zapytanie"),("devices","Urządzenia"),("layout","Układ"),
          ("geometry","Konstrukcja"),("hardware","Okucia"),("wheels","Koła i piętrowanie"),
          ("documentation","Dokumentacja"),("materials","Materiały"),("production","Produkcja")]
STATUSES = {"draft","waiting","review","approved","outdated"}

def now(): return datetime.now(timezone.utc).isoformat()

@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(DB_PATH,timeout=10)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript('''CREATE TABLE IF NOT EXISTS projects (
      id TEXT PRIMARY KEY,name TEXT NOT NULL,client TEXT NOT NULL,device TEXT NOT NULL,
      quantity INTEGER NOT NULL,notes TEXT NOT NULL,source TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS stages (project_id TEXT NOT NULL REFERENCES projects(id),key TEXT NOT NULL,
      label TEXT NOT NULL,status TEXT NOT NULL,note TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(project_id,key));
    CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),
      created_at TEXT NOT NULL,label TEXT NOT NULL,note TEXT NOT NULL,path TEXT NOT NULL,source TEXT NOT NULL,
      sha256 TEXT NOT NULL,parameters TEXT NOT NULL,validation TEXT NOT NULL,report_path TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),
      created_at TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL);''')
    # Additive migration; older snapshots remain explicitly unbound.
    conn.execute('BEGIN IMMEDIATE')
    columns={r[1] for r in conn.execute('PRAGMA table_info(snapshots)')}
    if 'layout_binding' not in columns: conn.execute('ALTER TABLE snapshots ADD COLUMN layout_binding TEXT')
    for table in ('projects','stages'):
        if 'revision' not in {r[1] for r in conn.execute('PRAGMA table_info('+table+')')}:
            conn.execute('ALTER TABLE '+table+' ADD COLUMN revision INTEGER NOT NULL DEFAULT 1')
    conn.commit()
    try:
        with conn: yield conn
    finally: conn.close()

def text(value,name,limit=10000):
    if not isinstance(value,str) or len(value)>limit: raise ValueError(name+" must be text (max "+str(limit)+")")
    return value.strip()

def project_exists(conn,project_id):
    row=conn.execute("SELECT * FROM projects WHERE id=?",(project_id,)).fetchone()
    if row is None: raise ValueError("Project not found: "+str(project_id))
    return dict(row)

def list_projects():
    with db() as conn: rows=[dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY updated_at DESC")]
    return {"projects":rows,"database":str(DB_PATH),"backend":"local SQLite"}

def list_snapshots(project_id):
    with db() as conn:
        project_exists(conn,project_id)
        rows=[dict(r) for r in conn.execute("SELECT * FROM snapshots WHERE project_id=? ORDER BY created_at DESC",(project_id,))]
    from worker import digest
    for row in rows:
        row["parameters"]=json.loads(row["parameters"])
        row["layout_binding"]=json.loads(row["layout_binding"]) if row["layout_binding"] else None
        try: row["integrity"]="verified" if digest(Path(row["path"]))==row["sha256"] else "modified"
        except OSError: row["integrity"]="missing"
    return {"snapshots":rows}

def get_project(project_id):
    with db() as conn:
        conn.execute("BEGIN")
        result=project_exists(conn,project_id)
        rows={r["key"]:dict(r) for r in conn.execute("SELECT * FROM stages WHERE project_id=?",(project_id,))}
        result["stages"]=[rows[key]|{"validation":"manual"} for key,_ in STAGES]
    result.update(list_snapshots(project_id))
    return {"project":result}

class RevisionConflict(ValueError):
    def __init__(self, code, expected, current):
        self.details = dict(code=code, expected_revision=expected,
                            current_revision=current['revision'], current=current)
        super().__init__(json.dumps(self.details, ensure_ascii=False))


def check_revision(expected, current, code):
    if type(expected) is not int or expected < 0:
        raise ValueError('expected_revision must be a nonnegative integer; read the entity first')
    if expected != current['revision']:
        raise RevisionConflict(code, expected, current)


def audit(conn, project_id, entity, before, after, actor='unspecified', change_source='unspecified', reason='manual', stamp=None):
    # Caller-supplied provenance is descriptive, not authenticated identity.
    actor=text(actor,'actor',200);change_source=text(change_source,'change_source',200)
    payload=dict(entity=entity,entity_key=after.get('key',project_id),before=before,after=after,
                 actor=actor,source=change_source,identity_verified=False,reason=reason)
    conn.execute('INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)',
                 (project_id,stamp or now(),entity+'_changed',json.dumps(payload,ensure_ascii=False)))


def change_stages(conn, project_id, keys, status, actor, change_source, reason, stamp):
    for key in sorted(set(keys)):
        before=dict(conn.execute('SELECT * FROM stages WHERE project_id=? AND key=?',(project_id,key)).fetchone())
        conn.execute('UPDATE stages SET status=?,updated_at=?,revision=revision+1 WHERE project_id=? AND key=?',
                     (status,stamp,project_id,key))
        after=dict(conn.execute('SELECT * FROM stages WHERE project_id=? AND key=?',(project_id,key)).fetchone())
        audit(conn,project_id,'stage',before,after,actor,change_source,reason,stamp)


def get_history(project_id,limit=50,before_id=None):
    if type(limit) is not int or not 1<=limit<=200: raise ValueError('limit must be integer 1..200')
    if before_id is not None and (type(before_id) is not int or before_id<1): raise ValueError('Invalid before_id')
    with db() as conn:
        project_exists(conn,project_id)
        rows=[dict(r) for r in conn.execute('SELECT * FROM events WHERE project_id=? AND (? IS NULL OR id<?) ORDER BY id DESC LIMIT ?',
                                            (project_id,before_id,before_id,limit+1))]
    more=len(rows)>limit;rows=rows[:limit]
    for row in rows: row['payload']=json.loads(row['payload'])
    return dict(events=rows,next_before_id=rows[-1]['id'] if more else None)


def save_project(name,project_id=None,client=None,device=None,quantity=None,notes=None,source=None,
                 expected_revision=None,actor='unspecified',change_source='unspecified'):
    from worker import source_path
    name=text(name,'name',200)
    if not name: raise ValueError('Project name is required')
    stamp=now()
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        old=project_exists(conn,project_id) if project_id else None
        if old: check_revision(expected_revision,old,'PROJECT_CONFLICT')
        elif expected_revision is not None and (type(expected_revision) is not int or expected_revision!=0):
            raise ValueError('New project expected_revision must be absent or zero')
        previous=old or {}
        client=previous.get('client','') if client is None else client
        device=previous.get('device','') if device is None else device
        quantity=previous.get('quantity',1) if quantity is None else quantity
        notes=previous.get('notes','') if notes is None else notes
        if type(quantity) is not int or not 1<=quantity<=100000: raise ValueError('quantity must be integer 1..100000')
        client,device,notes=text(client,'client',500),text(device,'device',500),text(notes,'notes')
        path=str(source_path(source or previous.get('source')))
        if Path(path).name == 'snapshot.ics': raise ValueError('Archive is read-only; bind the working revision instead')
        if old:
            conn.execute('UPDATE projects SET name=?,client=?,device=?,quantity=?,notes=?,source=?,updated_at=?,revision=revision+1 WHERE id=?',
                         (name,client,device,quantity,notes,path,stamp,project_id))
            invalid=set()
            if path!=old['source']: invalid.update(['geometry','hardware','wheels','documentation','materials','production'])
            if quantity!=old['quantity']: invalid.update(['materials','production'])
            if device!=old['device']: invalid.update(k for k,_ in STAGES if k not in ('inquiry','devices'))
            change_stages(conn,project_id,invalid,'outdated',actor,change_source,'project_inputs_changed',stamp)
        else:
            project_id=uuid.uuid4().hex
            conn.execute('INSERT INTO projects (id,name,client,device,quantity,notes,source,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
                         (project_id,name,client,device,quantity,notes,path,stamp,stamp))
            conn.executemany('INSERT INTO stages (project_id,key,label,status,note,updated_at) VALUES (?,?,?,?,?,?)',
                             [(project_id,k,l,'draft','',stamp) for k,l in STAGES])
        audit(conn,project_id,'project',old,project_exists(conn,project_id),actor,change_source,'save_project',stamp)
    return get_project(project_id)


def set_stage(project_id,stage,status,note='',expected_revision=None,actor='unspecified',change_source='unspecified'):
    if stage not in dict(STAGES) or status not in STATUSES: raise ValueError('Unknown stage or status')
    note=text(note,'note');stamp=now()
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        project_exists(conn,project_id)
        before=dict(conn.execute('SELECT * FROM stages WHERE project_id=? AND key=?',(project_id,stage)).fetchone())
        check_revision(expected_revision,before,'STAGE_CONFLICT')
        conn.execute('UPDATE stages SET status=?,note=?,updated_at=?,revision=revision+1 WHERE project_id=? AND key=?',
                     (status,note,stamp,project_id,stage))
        conn.execute('UPDATE projects SET updated_at=? WHERE id=?',(stamp,project_id))
        after=dict(conn.execute('SELECT * FROM stages WHERE project_id=? AND key=?',(project_id,stage)).fetchone())
        audit(conn,project_id,'stage',before,after,actor,change_source,'manual_stage',stamp)
    return get_project(project_id)

def pinned_source(project_id,source=None):
    from worker import source_path
    project=get_project(project_id)["project"]
    path=source_path(project["source"])
    if source and source_path(source)!=path: raise ValueError("Source differs from project's pinned ICS file")
    return str(path)

def register_snapshot(project_id,report,label,note="",advance=False,actor="unspecified",change_source="cad") :
    import shutil
    from worker import digest
    if not report.get("passed") or not report.get("source_unchanged"): raise ValueError("Cannot register failed CAD validation")
    # Archive is separate from the open working revision. Never edit archives through this API.
    working=Path(report["copy"])
    archive=working.parent/"snapshot.ics"
    with working.open("rb") as src, archive.open("xb") as dst: shutil.copyfileobj(src,dst)
    if digest(archive)!=digest(working): raise RuntimeError("Archive checksum mismatch")
    values=report["after_reopen"]["measurements"]["parameters_mm"]
    item={"id":uuid.uuid4().hex,"project_id":project_id,"created_at":now(),"label":text(label or "Snapshot","label",200),
          "note":text(note,"note"),"path":str(archive),"source":report["source"],"sha256":digest(archive),
          "parameters":values,"validation":"passed","report_path":str(working.parent/"report.json")}
    item['layout_binding']=report.get('layout_binding')
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        current=project_exists(conn,project_id)
        if item['layout_binding']:
            from layout import ensure
            ensure(conn)
            binding=item['layout_binding']
            version=conn.execute('SELECT * FROM layout_versions WHERE project_id=? AND revision=?',(project_id,binding['revision'])).fetchone()
            if not version or version['sha256']!=binding['sha256'] or json.loads(version['spec'])!=binding['spec']:
                raise ValueError('Invalid snapshot layout binding')
        if Path(current["source"]).resolve()!=Path(report["source"]).resolve():
            raise RuntimeError("Project source changed during CAD operation; snapshot retained on disk but not registered")
        conn.execute("INSERT INTO snapshots (id,project_id,created_at,label,note,path,source,sha256,parameters,validation,report_path) VALUES (?,?,?,?,?,?,?,?,?,?,?)",tuple(json.dumps(item[k],ensure_ascii=False) if k=="parameters" else item[k] for k in ("id","project_id","created_at","label","note","path","source","sha256","parameters","validation","report_path")))
        conn.execute("UPDATE snapshots SET layout_binding=? WHERE id=?",(json.dumps(item["layout_binding"],ensure_ascii=False) if item["layout_binding"] else None,item["id"]))
        if advance:
            conn.execute("UPDATE projects SET source=?,updated_at=?,revision=revision+1 WHERE id=?",(str(working),item["created_at"],project_id))
            audit(conn,project_id,'project',current,project_exists(conn,project_id),actor,change_source,'cad_source_advanced',item['created_at'])
            change_stages(conn,project_id,['geometry','hardware','wheels','documentation','materials','production'],
                          'outdated',actor,change_source,'cad_source_advanced',item['created_at'])
        else: conn.execute("UPDATE projects SET updated_at=? WHERE id=?",(item["created_at"],project_id))
    return {"snapshot":item,**get_project(project_id)}
