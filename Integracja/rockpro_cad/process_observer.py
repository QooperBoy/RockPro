"""Read-only local observer. No COM, worker dispatch, migrations or CAD replay."""
import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sqlite3

from .part_registry import STAGES as PART_STAGES, stage_for

LIMIT=8*1024*1024
LABELS={'case.capture':'Kopia źródła', 'case.create':'Wykonawca SDK (czas łączny)',
        'case.measure':'Kontrola pomiarów', 'case.save_reopen':'Kontrola pliku mostu',
        'case.verify':'Kontrola po otwarciu', 'case.source_check':'Integralność źródła',
        'case.receipt':'Zapis potwierdzenia', 'native.create':'Dodanie elementu',
        'native.regenerate':'Regeneracja', 'native.measure':'Pomiar SDK',
        'native.save':'Zapis ICS', 'native.reopen':'Ponowne otwarcie ICS'}


STAGES = [
    ('source', 'A · Przygotowanie źródła', '#dce8f2'),
    ('sdk', 'B · Montaż SDK — czas łączny', '#e6e9ed'),
    *[(r['id'], f"{r['order']:02} · {r['label']}", r['background']) for r in PART_STAGES],
    ('checks', '09 · Regeneracja i kontrola', '#deeddb'),
    ('save', '10 · Zapis i ponowne otwarcie', '#dcebee'),
    ('receipt', '11 · Integralność i potwierdzenie', '#e8edda'),
    ('other', '12 · Pozostałe zdarzenia', '#eeeeee'),
]

def stage_key(row):
    operation = row.get('operation', '')
    if operation == 'case.capture': return 'source'
    if operation == 'case.create': return 'sdk'
    if operation == 'native.create':
        return stage_for(row.get('family_id') or row.get('family') or row.get('occurrence_id'))
    if operation in ('native.save','native.reopen','case.save_reopen'): return 'save'
    if operation in ('case.source_check','case.receipt'): return 'receipt'
    if operation in ('native.regenerate','native.measure','case.measure','case.verify'): return 'checks'
    return 'other'


def grouped_events(rows):
    # Parent duration is deliberately not a sum: SDK and child spans overlap.
    return [(key, title, color, [(i,r) for i,r in enumerate(rows) if stage_key(r)==key])
            for key,title,color in STAGES if any(stage_key(r)==key for r in rows)]


def bounded_json(path):
    path=Path(path)
    with path.open('rb') as stream:data=stream.read(LIMIT+1)
    if len(data)>LIMIT: raise ValueError('Plik przekracza limit 8 MB')
    return json.loads(data.decode('utf-8-sig'))


def read_lines(path):
    path=Path(path)
    with path.open('rb') as stream:data=stream.read(LIMIT+1)
    if len(data)>LIMIT: raise ValueError('Ślad przekracza limit 8 MB')
    lines=data.splitlines(keepends=True); rows=[]; warnings=[]
    for i,line in enumerate(lines):
        if i==len(lines)-1 and not line.endswith(b'\n'):
            warnings.append('Niepełny ostatni wpis — oczekiwanie na zapis'); break
        try:
            row=json.loads(line)
            if not isinstance(row,dict): raise ValueError()
            rows.append(row)
        except (ValueError,UnicodeError): warnings.append('Uszkodzony wpis '+str(i+1))
    if any(r.get('event')=='logging_limit_reached' for r in rows): warnings.append('Log został ucięty — przebieg niepełny')
    return rows,warnings


def valid_elements(preview):
    if preview.get('kind')!='rockpro_process_preview' or preview.get('units')!='mm': raise ValueError('Nieznany kontrakt podglądu')
    items=preview.get('elements',[])
    if not isinstance(items,list) or len(items)>1000: raise ValueError('Limit elementów')
    ids=set()
    for row in items:
        if not isinstance(row,dict):raise ValueError('Niepoprawny element podglądu')
        b=row.get('bounds'); ident=row.get('id')
        if not isinstance(ident,str) or len(ident)>160 or ident in ids: raise ValueError('Niepoprawne ID podglądu')
        ids.add(ident)
        if (not isinstance(b,list) or len(b)!=6 or
            any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>100000 for v in b) or
            any(b[i]>=b[i+3] for i in range(3))): raise ValueError('Niepoprawny obrys podglądu')
    return items


def read_trace(path):
    path=Path(path); rows,warnings=read_lines(path); elements=[]; preview_identity=None
    folder=path.parent.parent if path.parent.name=='trace' else path.parent
    preview=folder/'process_preview.json'
    if preview.exists():
        with preview.open('rb') as stream:data=stream.read(LIMIT+1)
        if len(data)>LIMIT: raise ValueError('Zbyt duży podgląd')
        expected={r['refs'].get('inventory_sha256') for r in rows
                  if isinstance(r.get('refs'),dict) and isinstance(r['refs'].get('inventory_sha256'),str)}
        if not expected or expected!={hashlib.sha256(data).hexdigest()}:
            warnings.append('Podgląd niepowiązany z hashem śladu; rysunek wyłączony')
        else:
            preview_data=json.loads(data)
            elements=valid_elements(preview_data)
            preview_identity=(preview_data.get('operation_id'),hashlib.sha256(data).hexdigest())
    native=folder/'native_progress.jsonl'
    if native.exists() and native!=path:
        extra,notes=read_lines(native); rows+=extra; warnings+=notes
    bound_runs={row['run_id'] for row in rows if preview_identity and
                isinstance(row.get('run_id'),str) and isinstance(row.get('refs'),dict) and
                row['refs'].get('inventory_sha256')==preview_identity[1] and
                str(row.get('operation','')).startswith('case.')}
    unbound=False;unbound_coarse=False
    for row in rows:
        if str(row.get('operation','')).startswith('case.'):
            bound=bool(isinstance(row.get('run_id'),str) and len(bound_runs)==1 and row['run_id'] in bound_runs)
            row['_observer_evidence_bound']=bound
            unbound_coarse=unbound_coarse or not bound
        if str(row.get('operation','')).startswith('native.'):
            refs=row.get('refs') if isinstance(row.get('refs'),dict) else {}
            bound=bool(preview_identity and preview_identity[0]
                       and row.get('operation_id')==preview_identity[0]
                       and refs.get('inventory_sha256')==preview_identity[1])
            row['_observer_evidence_bound']=bound
            unbound=unbound or not bound
    if unbound:
        warnings.append('Ślad natywny bez zgodnego ID operacji i SHA podglądu — zdarzenia widoczne, lecz nie są dowodem utworzenia części tego modelu')
    if unbound_coarse:
        warnings.append('Etapy case.* nie należą do jednego przebiegu powiązanego z SHA podglądu — niepowiązane wpisy nie potwierdzają utworzenia modelu')
    def stamp(r):
        try:
            value=datetime.fromisoformat(r.get('timestamp_utc','').replace('Z','+00:00'))
            return value.timestamp() if value.tzinfo is not None else 0
        except (ValueError,TypeError,AttributeError,OverflowError,OSError): return 0
    rows.sort(key=stamp)
    return rows,elements,warnings


def read_journal(path):
    """No store.db(): that helper migrates and acquires a write lock."""
    path=Path(path).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=0.2)) as conn:
        conn.row_factory=sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'case_operations' not in tables: return []
        return [dict(r) for r in conn.execute('SELECT operation_id,project_id,state,created_at,updated_at FROM case_operations ORDER BY updated_at DESC LIMIT 100')]


def read_report(path):
    report=bounded_json(path)
    checks=report.get('checks',[])
    if not isinstance(checks,list): raise ValueError('Nieznany format raportu')
    rows=[dict(operation=r.get('label','Kontrola'),event='operation_finished',
               result={'status':'passed' if r.get('passed') else 'unknown'},actor=None,
               timestamp_utc='',duration_ms=None) for r in checks if isinstance(r,dict) and 'label' in r]
    if not rows: raise ValueError('Raport nie zawiera etapów; wybierz ślad JSONL')
    return rows,[],['Raport historyczny: brak pomiarów czasu i pochodzenia decyzji. Nie odtwarza rzeczywistej kolejności dodawania części.']


def visible_elements(rows,elements):
    detailed=[r for r in rows if r.get('operation')=='native.create']
    states={}
    for row in detailed:
        if row.get('_observer_evidence_bound') is False:continue
        ident=row.get('occurrence_id')
        if isinstance(ident,str):states[ident]=event_status(row)
    ids={ident for ident,status in states.items() if status=='passed'}
    # A completed coarse create phase is sufficient only when no detailed part
    # stream exists. Never invent per-part timestamps for an old report.
    coarse=[r for r in rows if r.get('operation')=='case.create' and r.get('_observer_evidence_bound') is not False]
    complete=bool(coarse and event_status(coarse[-1])=='passed')
    return elements if complete and not detailed else [e for e in elements if e['id'] in ids]


def event_status(row):
    result=row.get('result')
    return result.get('status') if isinstance(result,dict) else None


def stage_state(events,index):
    """Observed failure cannot be erased by a later successful sibling operation."""
    observed=[row for i,row in events if i<=index]
    if not observed:return 'oczekuje'
    if any(event_status(row) in ('failed','error') for row in observed):return 'BŁĄD'
    if any(row.get('event')=='logging_limit_reached' or
           event_status(row) in ('unknown','partial','limited','skipped','not_run')
           for row in observed):return 'niepełny'
    if any(row.get('_observer_evidence_bound') is False for row in observed):return 'niepowiązany'
    pending={};finished=0
    for row in observed:
        identity_fields=('run_id','operation_id','operation','occurrence_id')
        if any(row.get(k) is not None and not isinstance(row[k],str) for k in identity_fields):return 'niepełny'
        key=tuple(row.get(k) for k in identity_fields)
        if row.get('event')=='operation_started':pending[key]=pending.get(key,0)+1
        elif row.get('event')=='operation_finished':
            if event_status(row) not in ('passed','success','complete','completed'):return 'niepełny'
            pending[key]=max(0,pending.get(key,0)-1);finished+=1
    if finished and not any(pending.values()) and all(i<=index for i,_ in events):return 'OK'
    return 'w toku'


def summarize_events(rows,warnings=()):
    """Measured samples, not inferred CAD success, agent cost or automation ratio.

    A duration sum is recorded work within one category. It is deliberately not
    an elapsed/CPU time: parent SDK phases and child operations can overlap.
    """
    import statistics
    stamps=[];invalid_stamps=0;actors={};slowest=[];invalid_durations=0
    def duration(row):
        value=row.get('duration_ms')
        return value if type(value) in (int,float) and 0<=value<=1e12 and math.isfinite(value) else None
    for row in rows:
        try:
            stamp=datetime.fromisoformat(row.get('timestamp_utc','').replace('Z','+00:00'))
            if stamp.tzinfo is None:raise ValueError('Timezone required')
            stamps.append(stamp.timestamp())
        except (ValueError,TypeError,AttributeError,OverflowError,OSError):invalid_stamps+=1
        if row.get('event')!='operation_finished':continue
        actor=row.get('actor') if row.get('actor') in ('script','agent','human') else 'unknown'
        actors[actor]=actors.get(actor,0)+1
        measured=duration(row)
        if measured is None:invalid_durations+=1
        else:slowest.append(dict(operation=row.get('operation'),occurrence_id=row.get('occurrence_id'),
                                 duration_ms=measured,status=event_status(row),
                                 evidence_bound=row.get('_observer_evidence_bound')))
    stages=[]
    for key,title,color,events in grouped_events(rows):
        finished=[r for _,r in events if r.get('event')=='operation_finished']
        times=[duration(r) for r in finished if duration(r) is not None]
        stages.append(dict(stage_id=key,label=title,state=stage_state(events,len(rows)-1),
                           finished_count=len(finished),measured_count=len(times),
                           failed_count=sum(event_status(r) in ('failed','error') for r in finished),
                           recorded_work_ms=sum(times) if times else None,
                           median_ms=statistics.median(times) if times else None,
                           max_ms=max(times) if times else None,
                           parent_wrapper=key=='sdk'))
    return dict(schema='rockpro.process-summary/1',scope='read-only recorded execution evidence',
                event_count=len(rows),warnings=list(warnings),stages=stages,
                observed_window_ms=(max(stamps)-min(stamps))*1000 if len(stamps)>=2 else None,
                invalid_timestamp_count=invalid_stamps,missing_or_invalid_duration_count=invalid_durations,
                finished_by_executor=actors,
                unbound_native_events=sum(r.get('_observer_evidence_bound') is False and
                                         str(r.get('operation','')).startswith('native.') for r in rows),
                slowest_recorded_operations=sorted(slowest,key=lambda r:r['duration_ms'],reverse=True)[:10],
                time_semantics='Stage sums overlap. Observed window is first-to-last timestamp, not full process or CPU time.',
                automation_percent=None,agent_intervention_count=None,model_tokens=None,model_cost=None,
                authorship_status='unavailable; executor is not decision author',production_approved=False)


class Observer:
    def __init__(self,root,path=None,database=None,model=None):
        import tkinter as tk
        from tkinter import ttk, filedialog
        self.tk=tk; self.ttk=ttk; self.root=root; self.path=None; self.database=database
        self.model=model;self.viewer_server=None;self.row_indices={};self.rows=[];self.elements=[];self.playing=False;self.rebuilding=False
        root.title('RockPro — obserwator procesu (tylko odczyt)');root.geometry('1240x780');root.minsize(950,600)
        root.configure(bg='#eef2f6')
        style=ttk.Style();style.theme_use('clam');style.configure('Treeview',rowheight=27,font=('Segoe UI',10))
        top=tk.Frame(root,bg='#203c42',padx=18,pady=14);top.pack(fill='x')
        tk.Label(top,text='ROCKPRO  /  Przebieg pracy',font=('Segoe UI',19,'bold'),fg='white',bg='#203c42').pack(side='left')
        tk.Label(top,text='ODCZYT • BEZ STEROWANIA CAD',fg='#ffb97b',bg='#203c42',font=('Segoe UI',10,'bold')).pack(side='right')
        bar=ttk.Frame(root,padding=10);bar.pack(fill='x')
        ttk.Button(bar,text='Otwórz ślad / raport…',command=lambda:self.choose(filedialog)).pack(side='left')
        ttk.Button(bar,text='Odtwórz / pauza',command=self.play).pack(side='left',padx=8)
        ttk.Button(bar,text='Odśwież',command=self.refresh).pack(side='left')
        self.follow=tk.BooleanVar(value=True);ttk.Checkbutton(bar,text='Śledź nowe wpisy',variable=self.follow).pack(side='left',padx=15)
        self.caption=tk.StringVar(value='Wybierz lokalny ślad JSONL lub raport prototypu.')
        ttk.Label(root,textvariable=self.caption,padding=10,wraplength=1180).pack(fill='x')
        self.metrics=tk.StringVar(value='Pomiary: brak śladu.')
        ttk.Label(root,textvariable=self.metrics,padding=(10,0,10,8),wraplength=1180).pack(fill='x')
        book=ttk.Notebook(root);book.pack(fill='both',expand=True,padx=12)
        timeline=ttk.Frame(book);book.add(timeline,text='Etapy i podgląd')
        journal=ttk.Frame(book);book.add(journal,text='Dziennik operacji SQLite')
        self.tree=ttk.Treeview(timeline,columns=('status','time','actor'),show='tree headings',height=12)
        for name,title,width in [('stage','Etap',245),('status','Stan',180),('time','Czas [ms]',95),('actor','Wykonawca',100)]:
            col='#0' if name=='stage' else name
            self.tree.heading(col,text=title);self.tree.column(col,width=width,stretch=name=='stage')
        self.tree.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(timeline,orient='vertical',command=self.tree.yview);scroll.pack(side='left',fill='y');self.tree.configure(yscrollcommand=scroll.set)
        self.current=tk.StringVar(value='Etap: brak zdarzeń')
        ttk.Label(root,textvariable=self.current,padding=10,font=('Segoe UI',12,'bold')).pack(fill='x')
        ttk.Button(bar,text='Otwórz rzeczywisty model 3D…',command=self.open_viewer).pack(side='left',padx=8)
        self.tree.tag_configure('active',background='#ffe1b8',foreground='#623300',font=('Segoe UI',10,'bold'))
        self.tree.tag_configure('failure',background='#f8d6d6',foreground='#922222')
        self.tree.bind('<<TreeviewSelect>>',self.select)
        self.slider=tk.Scale(root,from_=0,to=1,orient='horizontal',command=self.seek,showvalue=False,bg='#eef2f6',highlightthickness=0);self.slider.pack(fill='x',padx=15)
        self.details=tk.StringVar();ttk.Label(root,textvariable=self.details,padding=12,wraplength=1180).pack(fill='x')
        ttk.Button(journal,text='Wybierz bazę (odczyt)…',command=lambda:self.choose_db(filedialog)).pack(anchor='w',pady=8)
        self.journal=ttk.Treeview(journal,columns=('id','project','state','updated'),show='headings')
        for col,title in [('id','Operacja'),('project','Projekt ID'),('state','Stan zapisany'),('updated','Aktualizacja UTC')]:self.journal.heading(col,text=title)
        self.journal.pack(fill='both',expand=True)
        self.db_status=tk.StringVar(value='Brak wybranej bazy. Odczyt nie tworzy ani nie migruje tabel.')
        ttk.Label(journal,textvariable=self.db_status,padding=10).pack(fill='x')
        if path:self.path=Path(path);self.refresh()
        self.refresh_db();root.after(2000,self.poll)

    def open_viewer(self):
        from tkinter import filedialog, messagebox
        import secrets, threading, webbrowser
        from http.server import ThreadingHTTPServer
        from .layer_viewer import make_handler
        if not self.model:
            selected=filedialog.askopenfilename(title='Wybierz eksport model.json (nie musi odpowiadać śladowi)',filetypes=[('Eksport siatki','model.json')])
            if not selected:return
            self.model=Path(selected).parent
        try:
            if self.viewer_server is None:
                token=secrets.token_urlsafe(24)
                self.viewer_server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.model,token))
                self.viewer_url=f'http://127.0.0.1:{self.viewer_server.server_port}/{token}/'
                threading.Thread(target=self.viewer_server.serve_forever,daemon=True).start()
            webbrowser.open(self.viewer_url)
        except (OSError,ValueError,KeyError) as exc:messagebox.showerror('Podgląd 3D',str(exc))

    def choose(self,dialog):
        p=dialog.askopenfilename(filetypes=[('Ślady i raporty','*.jsonl *.json')])
        if p:self.path=Path(p);self.playing=False;self.refresh()
    def choose_db(self,dialog):
        p=dialog.askopenfilename(filetypes=[('SQLite','*.sqlite3 *.db')])
        if p:self.database=p;self.refresh_db()
    def refresh_db(self):
        if not self.database:return
        try:
            rows=read_journal(self.database)
            self.journal.delete(*self.journal.get_children())
            for r in rows:self.journal.insert('', 'end',values=(r['operation_id'],r['project_id'],r['state'],r['updated_at']))
            self.db_status.set(f'Odczyt mode=ro • {len(rows)} operacji (maks. 100). Stan applying nie dowodzi, że proces nadal żyje.')
        except (OSError,sqlite3.Error,ValueError) as exc:self.db_status.set('Nie można odczytać: '+str(exc))
    def refresh(self):
        if not self.path:return
        try:
            rows,elements,notes=read_trace(self.path) if self.path.suffix=='.jsonl' else read_report(self.path)
            summary=summarize_events(rows,notes)
            window=summary['observed_window_ms']
            span=f'{window/1000:.2f} s' if window is not None else 'brak danych'
            counts=summary['finished_by_executor']
            self.metrics.set(f'Okno zarejestrowanych zdarzeń: {span} • zakończone wywołania: '
                             f'skrypt {counts.get("script",0)}, agent {counts.get("agent",0)}, '
                             f'pozostałe {counts.get("human",0)+counts.get("unknown",0)} • '
                             'udział automatyzacji i liczba interwencji: brak danych')
            self.rows,self.elements=rows,elements;self.rebuilding=True
            expanded={key for key in self.tree.get_children() if self.tree.item(key,'open')}
            self.tree.delete(*self.tree.get_children());self.row_indices={}
            for key,title,color,events in grouped_events(rows):
                self.tree.tag_configure(key,background=color,foreground='#203b42')
                parent='stage:'+key;self.row_indices[parent]=events[0][0]
                self.tree.insert('', 'end',iid=parent,text=title,values=('—','szczegóły ↓',''),tags=(key,),open=parent in expanded)
                for i,r in events:
                    status=event_status(r) or ('start' if r.get('event')=='operation_started' else r.get('event','?'))
                    status={'passed':'OK','failed':'BŁĄD','unknown':'nieznany'}.get(status,status)
                    duration=r.get('duration_ms');time_label=f'{duration:.1f}' if type(duration) in (int,float) and math.isfinite(duration) else '—'
                    title=LABELS.get(r.get('operation'),r.get('operation','?'))
                    if r.get('occurrence_id'):title+=' · '+r['occurrence_id']
                    self.row_indices[str(i)]=i
                    self.tree.insert(parent,'end',iid=str(i),text=title,values=(status,time_label,r.get('actor') or 'nieznany'),tags=('failure',) if status=='BŁĄD' else ())
            self.slider.configure(to=max(0,len(rows)-1))
            if self.follow.get() and not self.playing:self.slider.set(max(0,len(rows)-1))
            self.caption.set(str(self.path)+'\n'+(' • '.join(notes) if notes else 'Ślad wybranego przebiegu; model 3D jest osobnym eksportem. Czasy wierszy mogą się zawierać — nie sumuj czasu SDK i jego etapów.'))
            self.rebuilding=False;self.render()
        except (OSError,ValueError,TypeError,KeyError) as exc:self.rebuilding=False;self.caption.set('Błąd odczytu: '+str(exc))
    def select(self,event):
        if not self.rebuilding and self.tree.selection():self.follow.set(False);self.slider.set(self.row_indices[self.tree.selection()[0]])
    def seek(self,value):
        if not self.rebuilding:self.render()
    def play(self):
        self.playing=not self.playing;self.follow.set(False)
        if self.playing:
            if self.slider.get()>=len(self.rows)-1:self.slider.set(0)
            self.tick()
    def tick(self):
        if not self.playing:return
        value=self.slider.get()+1
        if value>=len(self.rows):self.playing=False;return
        self.slider.set(value);self.root.after(450,self.tick)
    def poll(self):
        if self.follow.get():self.refresh();self.refresh_db()
        self.root.after(2000,self.poll)
    def render(self):
        index=min(self.slider.get(),len(self.rows)-1)
        active=stage_key(self.rows[index]) if index>=0 else None
        for key,title,color,events in grouped_events(self.rows):
            for i,r in events:
                if i>index:self.tree.item(str(i),values=('oczekuje','—',r.get('actor') or 'nieznany'))
                else:
                    status=event_status(r) or ('start' if r.get('event')=='operation_started' else r.get('event','?'))
                    status={'passed':'OK','failed':'BŁĄD','unknown':'nieznany'}.get(status,status)
                    duration=r.get('duration_ms');label=f'{duration:.1f}' if type(duration) in (int,float) and math.isfinite(duration) else '—'
                    self.tree.item(str(i),values=(status,label,r.get('actor') or 'nieznany'))
            state=stage_state(events,index)
            self.tree.item('stage:'+key,values=(state,'szczegóły ↓',''),tags=('failure',) if state=='BŁĄD' else ('active',) if key==active else (key,))
            if key==active:self.current.set('▶ '+title+'  •  '+state)
        row=self.rows[index] if index>=0 else {}
        self.details.set(f'Zdarzenie {index+1}/{len(self.rows)} • UTC: {row.get("timestamp_utc") or "brak danych"}\n'
            'Wykonawca skryptu nie oznacza autora decyzji. Interwencje agentów, model, tokeny i koszt: brak pełnych danych; udział automatyzacji nie jest wyliczany.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path);parser.add_argument('--trace',type=Path);parser.add_argument('--database',type=Path)
    args=parser.parse_args()
    import tkinter as tk
    root=tk.Tk();Observer(root,args.trace,args.database,args.model);root.mainloop()

if __name__=='__main__':main()
