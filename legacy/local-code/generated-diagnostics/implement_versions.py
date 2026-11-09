from pathlib import Path
p=Path('Integracja/rockpro_cad/mcp/layout.py')
s=p.read_text(encoding='utf-8');s=s[:s.index('def ensure(conn):')]+'''def ensure(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS layouts (project_id TEXT PRIMARY KEY REFERENCES projects(id), spec TEXT NOT NULL, updated_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS layout_versions (project_id TEXT NOT NULL REFERENCES projects(id), revision INTEGER NOT NULL, spec TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(project_id,revision))")
    # Preserve the existing saved layout as revision 1, once, inside the write lock.
    for row in conn.execute("SELECT * FROM layouts WHERE project_id NOT IN (SELECT project_id FROM layout_versions)").fetchall():
        payload, digest = encode_spec(json.loads(row['spec']))
        conn.execute("INSERT INTO layout_versions VALUES (?,?,?,?,?)", (row['project_id'],1,payload,digest,row['updated_at']))


def encode_spec(spec):
    import hashlib
    payload=json.dumps(spec,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    return payload,hashlib.sha256(payload.encode('utf-8')).hexdigest()


def get_layout(project_id,revision=None):
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        project_exists(conn,project_id);ensure(conn)
        if revision is not None:
            if type(revision) is not int or revision < 1: raise ValueError('Invalid layout revision')
            row=conn.execute('SELECT * FROM layout_versions WHERE project_id=? AND revision=?',(project_id,revision)).fetchone()
            if row is None: raise ValueError('Layout revision not found')
        else:
            row=conn.execute('SELECT * FROM layout_versions WHERE project_id=? ORDER BY revision DESC LIMIT 1',(project_id,)).fetchone()
    return dict(saved=bool(row),revision=row['revision'] if row else 0,sha256=row['sha256'] if row else None,updated_at=row['created_at'] if row else None,**calculate_layout(json.loads(row['spec']) if row else {}))


def save_layout(project_id,spec,expected_revision):
    if type(expected_revision) is not int or expected_revision<0: raise ValueError('expected_revision must be a nonnegative integer; read get_layout first')
    result=calculate_layout(spec);stamp=now()
    payload,digest=encode_spec(result['spec'])
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        project_exists(conn,project_id);ensure(conn)
        current=conn.execute('SELECT COALESCE(MAX(revision),0) FROM layout_versions WHERE project_id=?',(project_id,)).fetchone()[0]
        if current!=expected_revision:
            raise ValueError('LAYOUT_CONFLICT: Układ zmienił inny użytkownik lub AI. Odczytana wersja '+str(expected_revision)+', aktualna '+str(current)+'. Pobierz aktualny układ i porównaj zmiany przed ponownym zapisem.')
        revision=current+1
        conn.execute('INSERT INTO layout_versions VALUES (?,?,?,?,?)',(project_id,revision,payload,digest,stamp))
        conn.execute("INSERT OR REPLACE INTO layouts VALUES (?,?,?)",(project_id,payload,stamp))
        conn.execute("UPDATE projects SET updated_at=? WHERE id=?",(stamp,project_id))
        conn.execute("UPDATE stages SET status='outdated',updated_at=? WHERE project_id=? AND key IN ('geometry','hardware','wheels','documentation','materials','production')",(stamp,project_id))
        conn.execute("UPDATE stages SET status='review',updated_at=? WHERE project_id=? AND key='layout'",(stamp,project_id))
        conn.execute("INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)",(project_id,stamp,"layout_saved",json.dumps(dict(revision=revision,sha256=digest,spec=result['spec']),ensure_ascii=False)))
    return dict(saved=True,revision=revision,sha256=digest,updated_at=stamp,**result)
''';p.write_text(s,encoding='utf-8')
p=Path('Integracja/rockpro_cad/mcp/worker.py');s=p.read_text(encoding='utf-8');s=s.replace('def change_dimensions_on_copy(changes, source=None, project_id=None, label=None):','def change_dimensions_on_copy(changes, source=None, project_id=None, label=None, layout_revision=None):');s=s.replace('    report = _change_dimensions_on_copy(changes,source)','''    binding=None
    if layout_revision is not None:
        from layout import get_layout
        if not project_id: raise ValueError('layout_revision requires project_id')
        binding=get_layout(project_id,layout_revision)
        if changes != binding['parameters']: raise ValueError('CAD parameters do not match the pinned layout revision')
    report = _change_dimensions_on_copy(changes,source)
    if binding:
        report['layout_binding']={k:binding[k] for k in ('revision','sha256','spec')}
        (Path(report['copy']).parent/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')''');s=s.replace('"get_layout":(get_layout,{"project_id"}),"save_layout":(save_layout,{"project_id","spec"})','"get_layout":(get_layout,{"project_id","revision"}),"save_layout":(save_layout,{"project_id","spec","expected_revision"})');s=s.replace('set(arguments)!=keys','set(arguments)-keys');s=s.replace('{"source", "changes","project_id","label"}','{"source", "changes","project_id","label","layout_revision"}');p.write_text(s,encoding='utf-8')
p=Path('Integracja/rockpro_cad/mcp/project_store.py');s=p.read_text(encoding='utf-8');s=s.replace('    try:\n        with conn: yield conn','''    # Additive migration; older snapshots remain explicitly unbound.
    conn.execute('BEGIN IMMEDIATE')
    columns={r[1] for r in conn.execute('PRAGMA table_info(snapshots)')}
    if 'layout_binding' not in columns: conn.execute('ALTER TABLE snapshots ADD COLUMN layout_binding TEXT')
    conn.commit()
    try:
        with conn: yield conn''');s=s.replace('row["parameters"]=json.loads(row["parameters"])','row["parameters"]=json.loads(row["parameters"])\n        row["layout_binding"]=json.loads(row["layout_binding"]) if row["layout_binding"] else None');s=s.replace('    with db() as conn:\n        current=project_exists(conn,project_id)','''    item['layout_binding']=report.get('layout_binding')
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        current=project_exists(conn,project_id)
        if item['layout_binding']:
            from layout import ensure
            ensure(conn)
            binding=item['layout_binding']
            version=conn.execute('SELECT * FROM layout_versions WHERE project_id=? AND revision=?',(project_id,binding['revision'])).fetchone()
            if not version or version['sha256']!=binding['sha256'] or json.loads(version['spec'])!=binding['spec']:
                raise ValueError('Invalid snapshot layout binding')''');s=s.replace('INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?)','INSERT INTO snapshots (id,project_id,created_at,label,note,path,source,sha256,parameters,validation,report_path) VALUES (?,?,?,?,?,?,?,?,?,?,?)');s=s.replace('        if advance:\n','        conn.execute("UPDATE snapshots SET layout_binding=? WHERE id=?",(json.dumps(item["layout_binding"],ensure_ascii=False) if item["layout_binding"] else None,item["id"]))\n        if advance:\n');p.write_text(s,encoding='utf-8')
p=Path('Integracja/rockpro_cad/mcp/server.py');s=p.read_text(encoding='utf-8').replace('"label":{"type":"string"},','"label":{"type":"string"}, "layout_revision":{"type":"integer","minimum":1},');s=s.replace('"Read saved layout from project SQLite",{"project_id":S}','"Read current or historical immutable layout; revision 0 means unsaved",{"project_id":S,"revision":{"type":"integer","minimum":1}}');s=s.replace('{"project_id":S,"spec":layout_spec},["project_id","spec"]','{"project_id":S,"spec":layout_spec,"expected_revision":{"type":"integer","minimum":0}},["project_id","spec","expected_revision"]');p.write_text(s,encoding='utf-8')
p=Path('Integracja/rockpro_cad/addin/LayoutForm.cs');s=p.read_text(encoding='utf-8');s=s.replace(' async Task LoadLayout()', ' long layoutRevision=0;\n async Task LoadLayout()');s=s.replace('var spec=Rpc.Obj(r["spec"]);','layoutRevision=Convert.ToInt64(r["revision"]);var spec=Rpc.Obj(r["spec"]);');s=s.replace('project_id=projectId,spec=spec}', 'project_id=projectId,spec=spec,expected_revision=layoutRevision}');s=s.replace('dirty=false;Render(r);if(cad)', 'layoutRevision=Convert.ToInt64(r["revision"]);dirty=false;Render(r);if(cad)');s=s.replace('label="Szkielet z układu urządzeń"','label="Szkielet z układu urządzeń",layout_revision=layoutRevision');s=s.replace('MessageBox.Show(this,ex.Message,"RockPro — wynik operacji");','MessageBox.Show(this,ex.Message+(ex.Message.Contains("LAYOUT_CONFLICT")?"\\n\\nTwoje pola pozostają w formularzu. Skopiuj potrzebne wartości, zamknij i otwórz konfigurator, aby wczytać aktualną wersję. Nie ponawiamy zapisu automatycznie.":""),"RockPro — wynik operacji");');p.write_text(s,encoding='utf-8')
p=Path('Integracja/rockpro_cad/mcp/test_layout.py');s=p.read_text(encoding='utf-8').replace("save_layout('p',dict(count=4,side='Y'))","save_layout('p',dict(count=4,side='Y'),0)");p.write_text(s,encoding='utf-8')
