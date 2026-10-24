"""Read-only local observer. No COM, worker dispatch, migrations or CAD replay."""
import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sqlite3

LIMIT=8*1024*1024
LABELS={'case.capture':'Kopia źródła', 'case.create':'Wykonawca SDK (czas łączny)',
        'case.measure':'Kontrola pomiarów', 'case.save_reopen':'Kontrola pliku mostu',
        'case.verify':'Kontrola po otwarciu', 'case.source_check':'Integralność źródła',
        'case.receipt':'Zapis potwierdzenia', 'native.create':'Dodanie elementu',
        'native.regenerate':'Regeneracja', 'native.measure':'Pomiar SDK',
        'native.save':'Zapis ICS', 'native.reopen':'Ponowne otwarcie ICS'}


def bounded_json(path):
    path=Path(path)
    if path.stat().st_size>LIMIT: raise ValueError('Plik przekracza limit 8 MB')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read_lines(path):
    path=Path(path)
    if path.stat().st_size>LIMIT: raise ValueError('Ślad przekracza limit 8 MB')
    data=path.read_bytes(); lines=data.splitlines(keepends=True); rows=[]; warnings=[]
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
        b=row.get('bounds'); ident=row.get('id')
        if not isinstance(ident,str) or len(ident)>160 or ident in ids: raise ValueError('Niepoprawne ID podglądu')
        ids.add(ident)
        if (not isinstance(b,list) or len(b)!=6 or
            any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>100000 for v in b) or
            any(b[i]>=b[i+3] for i in range(3))): raise ValueError('Niepoprawny obrys podglądu')
    return items


def read_trace(path):
    path=Path(path); rows,warnings=read_lines(path); elements=[]
    folder=path.parent.parent if path.parent.name=='trace' else path.parent
    preview=folder/'process_preview.json'
    if preview.exists():
        data=preview.read_bytes()
        if len(data)>LIMIT: raise ValueError('Zbyt duży podgląd')
        expected={r.get('refs',{}).get('inventory_sha256') for r in rows if r.get('refs',{}).get('inventory_sha256')}
        if not expected or expected!={hashlib.sha256(data).hexdigest()}:
            warnings.append('Podgląd niepowiązany z hashem śladu; rysunek wyłączony')
        else: elements=valid_elements(json.loads(data))
    native=folder/'native_progress.jsonl'
    if native.exists() and native!=path:
        extra,notes=read_lines(native); rows+=extra; warnings+=notes
    def stamp(r):
        try: return datetime.fromisoformat(r.get('timestamp_utc','').replace('Z','+00:00')).timestamp()
        except (ValueError,TypeError): return 0
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
    ids={r.get('occurrence_id') for r in rows if r.get('operation')=='native.create' and r.get('result',{}).get('status')=='passed'}
    # A completed coarse create phase is sufficient only when no detailed part
    # stream exists. Never invent per-part timestamps for an old report.
    complete=any(r.get('operation')=='case.create' and r.get('result',{}).get('status')=='passed' for r in rows)
    return elements if complete else [e for e in elements if e['id'] in ids]


class Observer:
    def __init__(self,root,path=None,database=None):
        import tkinter as tk
        from tkinter import ttk, filedialog
        self.tk=tk; self.ttk=ttk; self.root=root; self.path=None; self.database=database
        self.rows=[];self.elements=[];self.playing=False;self.rebuilding=False
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
        book=ttk.Notebook(root);book.pack(fill='both',expand=True,padx=12)
        timeline=ttk.Frame(book);book.add(timeline,text='Etapy i podgląd')
        journal=ttk.Frame(book);book.add(journal,text='Dziennik operacji SQLite')
        self.tree=ttk.Treeview(timeline,columns=('stage','status','time','actor'),show='headings',height=12)
        for name,title,width in [('stage','Etap',245),('status','Stan',100),('time','Czas [ms]',95),('actor','Wykonawca',100)]:
            self.tree.heading(name,text=title);self.tree.column(name,width=width,stretch=name=='stage')
        self.tree.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(timeline,orient='vertical',command=self.tree.yview);scroll.pack(side='left',fill='y');self.tree.configure(yscrollcommand=scroll.set)
        self.canvas=tk.Canvas(timeline,bg='#f5f8fa',width=480,highlightthickness=0);self.canvas.pack(side='right',fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.render())
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
            self.rows,self.elements=rows,elements;self.rebuilding=True
            self.tree.delete(*self.tree.get_children())
            for i,r in enumerate(rows):
                status=r.get('result',{}).get('status') or ('start' if r.get('event')=='operation_started' else r.get('event','?'))
                status={'passed':'OK','failed':'błąd','unknown':'nieznany'}.get(status,status)
                duration=r.get('duration_ms');time_label=f'{duration:.1f}' if type(duration) in (int,float) and math.isfinite(duration) else '—'
                title=LABELS.get(r.get('operation'),r.get('operation','?'))
                if r.get('occurrence_id'):title+=' · '+r['occurrence_id']
                self.tree.insert('', 'end',iid=str(i),values=(title,status,time_label,r.get('actor') or 'nieznany'))
            self.slider.configure(to=max(0,len(rows)-1))
            if self.follow.get() and not self.playing:self.slider.set(max(0,len(rows)-1))
            self.caption.set(str(self.path)+'\n'+(' • '.join(notes) if notes else 'Ślad rzeczywistego przebiegu. Czasy wierszy mogą się zawierać — nie sumuj czasu SDK i jego etapów.'))
            self.rebuilding=False;self.render()
        except (OSError,ValueError,TypeError,KeyError) as exc:self.rebuilding=False;self.caption.set('Błąd odczytu: '+str(exc))
    def select(self,event):
        if not self.rebuilding and self.tree.selection():self.follow.set(False);self.slider.set(int(self.tree.selection()[0]))
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
        c=self.canvas;c.delete('all');w=max(c.winfo_width(),300);h=max(c.winfo_height(),250)
        index=min(self.slider.get(),len(self.rows)-1);upto=self.rows[:index+1]
        shown=visible_elements(upto,self.elements)
        c.create_text(w/2,24,text='Poglądowe obrysy • nie walidacja CAD',fill='#365159',font=('Segoe UI',11,'bold'))
        if self.elements:
            def project(x,y,z):return (.85*(x-y), .35*(x+y)-z)
            points=[project(*[e['bounds'][j+(3 if mask&(1<<j) else 0)] for j in range(3)]) for e in self.elements for mask in range(8)]
            lo=[min(p[j] for p in points) for j in range(2)];hi=[max(p[j] for p in points) for j in range(2)]
            scale=min((w-70)/max(hi[0]-lo[0],1),(h-110)/max(hi[1]-lo[1],1))
            for e in sorted(shown,key=lambda e:e['bounds'][0]+e['bounds'][1]):
                b=e['bounds'];verts=[]
                for mask in range(8):
                    x,y=project(*[b[j+(3 if mask&(1<<j) else 0)] for j in range(3)])
                    verts.append((35+(x-lo[0])*scale,55+(y-lo[1])*scale))
                color='#408080' if 'panel' in e['family'] or 'plywood' in e['family'] or 'plate' in e['family'] else '#c5d0d5'
                for face in ((0,1,5,4),(0,2,6,4),(4,5,7,6)):
                    c.create_polygon(*[v for k in face for v in verts[k]],fill=color,outline='#304d52',width=1)
        else:c.create_text(w/2,h/2,text='Brak powiązanej geometrii podglądu.\nNie odtwarzamy części z domysłów.',fill='#52666d',font=('Segoe UI',12),justify='center')
        c.create_text(w/2,h-30,text=f'Pokazano {len(shown)} / {len(self.elements)} obrysów',fill='#365159')
        row=self.rows[index] if index>=0 else {}
        self.details.set(f'Zdarzenie {index+1}/{len(self.rows)} • UTC: {row.get("timestamp_utc") or "brak danych"}\n'
            'Wykonawca skryptu nie oznacza autora decyzji. Interwencje agentów, model, tokeny i koszt: brak pełnych danych; udział automatyzacji nie jest wyliczany.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path);parser.add_argument('--database',type=Path)
    args=parser.parse_args()
    import tkinter as tk
    root=tk.Tk();Observer(root,args.trace,args.database);root.mainloop()

if __name__=='__main__':main()
