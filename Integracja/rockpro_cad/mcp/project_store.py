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
        try: row["integrity"]="verified" if digest(Path(row["path"]))==row["sha256"] else "modified"
        except OSError: row["integrity"]="missing"
    return {"snapshots":rows}

def get_project(project_id):
    with db() as conn:
        result=project_exists(conn,project_id)
        rows={r["key"]:dict(r) for r in conn.execute("SELECT * FROM stages WHERE project_id=?",(project_id,))}
        result["stages"]=[rows[key]|{"validation":"manual"} for key,_ in STAGES]
    result.update(list_snapshots(project_id))
    return {"project":result}

def save_project(name,project_id=None,client=None,device=None,quantity=None,notes=None,source=None):
    from worker import source_path
    name=text(name,"name",200)
    if not name: raise ValueError("Project name is required")
    with db() as conn: previous=project_exists(conn,project_id) if project_id else {}
    client=previous.get("client","") if client is None else client
    device=previous.get("device","") if device is None else device
    quantity=previous.get("quantity",1) if quantity is None else quantity
    notes=previous.get("notes","") if notes is None else notes
    if isinstance(quantity,bool) or not isinstance(quantity,int) or not 1<=quantity<=100000: raise ValueError("quantity must be integer 1..100000")
    client,device,notes=text(client,"client",500),text(device,"device",500),text(notes,"notes")
    stamp=now()
    with db() as conn:
        old=project_exists(conn,project_id) if project_id else None
        path=str(source_path(source or (old["source"] if old else None)))
        if Path(path).name == "snapshot.ics": raise ValueError("Archive is read-only; bind the working revision instead")
        if old:
            conn.execute("UPDATE projects SET name=?,client=?,device=?,quantity=?,notes=?,source=?,updated_at=? WHERE id=?",(name,client,device,quantity,notes,path,stamp,project_id))
            if path!=old["source"]:
                conn.execute("UPDATE stages SET status='outdated',updated_at=? WHERE project_id=? AND key IN ('geometry','hardware','wheels','documentation','materials','production')",(stamp,project_id))
            if quantity!=old["quantity"]:
                conn.execute("UPDATE stages SET status='outdated',updated_at=? WHERE project_id=? AND key IN ('materials','production')",(stamp,project_id))
            if device!=old["device"]:
                conn.execute("UPDATE stages SET status='outdated',updated_at=? WHERE project_id=? AND key NOT IN ('inquiry','devices')",(stamp,project_id))
        else:
            project_id=uuid.uuid4().hex
            conn.execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?)",(project_id,name,client,device,quantity,notes,path,stamp,stamp))
            conn.executemany("INSERT INTO stages VALUES (?,?,?,?,?,?)",[(project_id,k,l,"draft","",stamp) for k,l in STAGES])
        conn.execute("INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)",(project_id,stamp,"save_project",json.dumps({"source":path},ensure_ascii=False)))
    return get_project(project_id)

def set_stage(project_id,stage,status,note=""):
    if stage not in dict(STAGES) or status not in STATUSES: raise ValueError("Unknown stage or status")
    note=text(note,"note")
    stamp=now()
    with db() as conn:
        project_exists(conn,project_id)
        conn.execute("UPDATE stages SET status=?,note=?,updated_at=? WHERE project_id=? AND key=?",(status,note,stamp,project_id,stage))
        conn.execute("UPDATE projects SET updated_at=? WHERE id=?",(stamp,project_id))
        conn.execute("INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)",(project_id,stamp,"manual_stage",json.dumps({"stage":stage,"status":status,"note":note},ensure_ascii=False)))
    return get_project(project_id)

def pinned_source(project_id,source=None):
    from worker import source_path
    project=get_project(project_id)["project"]
    path=source_path(project["source"])
    if source and source_path(source)!=path: raise ValueError("Source differs from project's pinned ICS file")
    return str(path)

def register_snapshot(project_id,report,label,note="",advance=False):
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
    with db() as conn:
        current=project_exists(conn,project_id)
        if Path(current["source"]).resolve()!=Path(report["source"]).resolve():
            raise RuntimeError("Project source changed during CAD operation; snapshot retained on disk but not registered")
        conn.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?)",tuple(json.dumps(item[k],ensure_ascii=False) if k=="parameters" else item[k] for k in ("id","project_id","created_at","label","note","path","source","sha256","parameters","validation","report_path")))
        if advance:
            conn.execute("UPDATE projects SET source=?,updated_at=? WHERE id=?",(str(working),item["created_at"],project_id))
            conn.execute("UPDATE stages SET status='outdated',updated_at=? WHERE project_id=? AND key IN ('geometry','hardware','wheels','documentation','materials','production')",(item["created_at"],project_id))
        else: conn.execute("UPDATE projects SET updated_at=? WHERE id=?",(item["created_at"],project_id))
    return {"snapshot":item,**get_project(project_id)}
