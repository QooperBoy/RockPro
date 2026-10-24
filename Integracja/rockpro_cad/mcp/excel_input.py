"""ROC-18: bounded XLSX input, explicit units, shared layout CAS and immutable source versions."""
import hashlib
import io
import json
import math
from pathlib import Path
import posixpath
import re
import uuid
import xml.etree.ElementTree as ET
import zipfile
import layout
import project_store as store

MAX_BYTES=2*1024*1024
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
META={'schema_version','project_id','expected_layout_revision'}


def _xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('Niedozwolone deklaracje XML')
    return ET.fromstring(data)


def _cells(data):
    if len(data)>MAX_BYTES:raise ValueError('Arkusz przekracza limit 2 MB')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        info=z.infolist();names=[i.filename for i in info]
        if len(names)>100 or len(set(names))!=len(names) or sum(i.file_size for i in info)>16*1024*1024:raise ValueError('Niepoprawny lub zbyt duży pakiet XLSX')
        if any('vbaproject' in n.lower() or 'externallink' in n.lower() for n in names):raise ValueError('Makra i odwołania zewnętrzne nie są obsługiwane')
        wb=_xml(z.read('xl/workbook.xml'));sheets=wb.findall('s:sheets/s:sheet',NS)
        if len(sheets)!=1 or sheets[0].get('name')!='Konfiguracja':raise ValueError('Wymagany jeden arkusz: Konfiguracja')
        rid=sheets[0].get('{'+REL+'}id')
        rels=_xml(z.read('xl/_rels/workbook.xml.rels'))
        matches=[r for r in rels if r.get('Id')==rid]
        if len(matches)!=1 or matches[0].get('TargetMode')=='External':raise ValueError('Niepoprawne odwołanie do arkusza')
        target=matches[0].get('Target','')
        target=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
        if not re.fullmatch(r'xl/worksheets/[^/]+\.xml',target):raise ValueError('Niedozwolona ścieżka arkusza')
        strings=[]
        if 'xl/sharedStrings.xml' in names:
            ss=_xml(z.read('xl/sharedStrings.xml'))
            strings=[''.join(n.itertext()) for n in ss.findall('s:si',NS)]
            if len(strings)>10000:raise ValueError('Za dużo tekstu')
        root=_xml(z.read(target));result={}
        for cell in root.findall('s:sheetData/s:row/s:c',NS):
            address=cell.get('r','');match=re.fullmatch(r'([A-D])([1-9][0-9]{0,2})',address)
            if not match or int(match[2])>200:raise ValueError('Dane poza zakresem A1:D200')
            if address in result:raise ValueError('Powtórzona komórka '+address)
            if cell.find('s:f',NS) is not None:raise ValueError('Formuła w '+address+': wpisz wartość bez formuły')
            kind=cell.get('t','n');raw=cell.findtext('s:v',None,NS)
            if kind=='inlineStr':v=''.join(cell.find('s:is',NS).itertext()) if cell.find('s:is',NS) is not None else ''
            elif raw is None:v=None
            elif kind=='s':
                index=int(raw)
                if index<0 or index>=len(strings):raise ValueError('Niepoprawny tekst '+address)
                v=strings[index]
            elif kind=='b':
                if raw not in ('0','1'):raise ValueError('Niepoprawna wartość logiczna '+address)
                v=raw=='1'
            elif kind=='n':
                v=float(raw)
                if not math.isfinite(v):raise ValueError('Niepoprawna liczba '+address)
            elif kind=='str':v=raw
            else:raise ValueError('Nieobsługiwany typ komórki '+address)
            if isinstance(v,str) and len(v)>2000:raise ValueError('Za długi tekst '+address)
            result[address]=v
        return result


def parse_workbook(data):
    digest=hashlib.sha256(data).hexdigest();errors=[];spec={};meta={}
    def error(cell,code,message):errors.append(dict(cell=cell,code=code,message=message))
    try:cells=_cells(data)
    except (ValueError,KeyError,ET.ParseError,zipfile.BadZipFile,OverflowError,RuntimeError) as exc:
        return dict(valid=False,source_sha256=digest,errors=[dict(cell=None,code='XLSX_INVALID',message=str(exc))])
    if [cells.get(c+'4') for c in 'ABC']!=['Pole','Wartość','Jednostka']:error('A4:C4','HEADER_INVALID','Wymagane nagłówki: Pole / Wartość / Jednostka')
    seen=set()
    for row in range(5,201):
        key=cells.get('A'+str(row));v=cells.get('B'+str(row));unit=cells.get('C'+str(row)) or ''
        if key is None and v is None and not unit:continue
        addr='B'+str(row)
        if key not in META and key not in layout.LAYOUT_PROPERTIES:
            error('A'+str(row),'FIELD_UNKNOWN','Nieznane pole: '+str(key));continue
        if key in seen:error('A'+str(row),'FIELD_DUPLICATE','Powtórzone pole '+key);continue
        seen.add(key)
        if key in META:
            if unit:error('C'+str(row),'UNIT_INVALID','Pole techniczne nie ma jednostki')
            if key=='project_id':
                if not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',v):error(addr,'PROJECT_INVALID','Wpisz ID projektu z RockPro')
                else:meta[key]=v
            else:
                if type(v) not in (int,float) or not float(v).is_integer() or v<0:error(addr,'INTEGER_REQUIRED','Wymagana nieujemna liczba całkowita')
                else:meta[key]=int(v)
            continue
        kind=layout.LAYOUT_PROPERTIES[key]['type']
        if kind=='number':
            if unit not in ('mm','cm','m'):error('C'+str(row),'UNIT_INVALID','Wymagana jednostka mm, cm albo m');continue
            if type(v) not in (int,float):error(addr,'NUMBER_REQUIRED','Wpisz liczbę; jednostkę podaj w kolumnie C');continue
            spec[key]=v*{'mm':1,'cm':10,'m':1000}[unit]
        elif kind=='integer':
            if unit!='szt':error('C'+str(row),'UNIT_INVALID','Liczba urządzeń wymaga jednostki szt')
            if type(v) not in (int,float) or not float(v).is_integer():error(addr,'INTEGER_REQUIRED','Wymagana liczba całkowita')
            else:spec[key]=int(v)
        elif kind=='boolean':
            if unit or type(v) is not bool:error(addr,'BOOLEAN_REQUIRED','Wymagana wartość logiczna TRUE/FALSE bez jednostki')
            else:spec[key]=v
        else:
            if unit or not isinstance(v,str):error(addr,'TEXT_REQUIRED','Wymagany tekst bez jednostki')
            else:spec[key]=v
    for key in sorted(META|set(layout.DEFAULT)-seen):
        if key not in seen:error(None,'FIELD_REQUIRED','Brak pola '+key)
    if meta.get('schema_version')!=1:error(None,'SCHEMA_VERSION','Obsługiwana wersja arkusza: 1')
    result=None
    if not errors:
        try:result=layout.calculate_layout(spec)
        except ValueError as exc:error(None,'LAYOUT_INVALID',str(exc))
    if errors:return dict(valid=False,source_sha256=digest,errors=errors)
    _,semantic_sha=layout.encode_spec(result['spec'])
    return dict(valid=True,source_sha256=digest,configuration_sha256=semantic_sha,
                schema_version=1,project_id=meta['project_id'],expected_layout_revision=meta['expected_layout_revision'],
                layout=result,errors=[])


def _read(path):
    import worker
    path=Path(path).resolve(strict=True);folder=(worker.ROOT/'imports').resolve()
    if not path.is_relative_to(folder) or path.suffix.lower()!='.xlsx':raise ValueError('Umieść arkusz XLSX w katalogu Integracja/imports')
    with path.open('rb') as stream:data=stream.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise ValueError('Arkusz przekracza limit 2 MB')
    return data


def preview_excel_configuration(path):
    return parse_workbook(_read(path))


def _ensure(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS excel_configurations (
      project_id TEXT NOT NULL REFERENCES projects(id), configuration_sha256 TEXT NOT NULL,
      layout_revision INTEGER NOT NULL, PRIMARY KEY(project_id,configuration_sha256))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS excel_import_sources (
      project_id TEXT NOT NULL REFERENCES projects(id), source_sha256 TEXT NOT NULL,
      schema_version INTEGER NOT NULL, configuration_sha256 TEXT NOT NULL, source_xlsx BLOB NOT NULL,
      result_json TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(project_id,source_sha256))""")


def import_excel_configuration(project_id,path,expected_revision,expected_source_sha256):
    data=_read(path);preview=parse_workbook(data)
    if not preview['valid']:return dict(imported=False,**preview)
    if expected_source_sha256!=preview['source_sha256']:raise ValueError('EXCEL_SOURCE_CHANGED: Arkusz zmienił się od podglądu')
    if project_id!=preview['project_id']:raise ValueError('EXCEL_PROJECT_MISMATCH: Arkusz dotyczy innego projektu')
    if type(expected_revision) is not int or expected_revision!=preview['expected_layout_revision']:raise ValueError('EXCEL_REVISION_MISMATCH: Wersja w arkuszu różni się od odczytanej')
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');store.project_exists(conn,project_id);layout.ensure(conn);_ensure(conn)
        current=conn.execute('SELECT COALESCE(MAX(revision),0) FROM layout_versions WHERE project_id=?',(project_id,)).fetchone()[0]
        previous=conn.execute('SELECT result_json FROM excel_import_sources WHERE project_id=? AND source_sha256=?',(project_id,preview['source_sha256'])).fetchone()
        if previous:
            result=json.loads(previous['result_json']);result.update(reused=True,current_layout_revision=current,historical=result['layout_revision']!=current)
            return result
        duplicate=conn.execute('SELECT layout_revision FROM excel_configurations WHERE project_id=? AND configuration_sha256=?',(project_id,preview['configuration_sha256'])).fetchone()
        if current!=expected_revision:raise ValueError('LAYOUT_CONFLICT: Układ zmienił się od przygotowania arkusza; porównaj aktualną wersję')
        if duplicate:
            revision=duplicate['layout_revision'];reused=True
        else:
            saved=layout.save_layout_in_transaction(conn,project_id,preview['layout'],expected_revision,'excel','excel_import')
            revision=saved['revision'];reused=False
            conn.execute('INSERT INTO excel_configurations VALUES (?,?,?)',(project_id,preview['configuration_sha256'],revision))
        result=dict(imported=True,reused=reused,source_sha256=preview['source_sha256'],configuration_sha256=preview['configuration_sha256'],
                    schema_version=1,layout_revision=revision,historical=revision!=current if reused else False,
                    project_id=project_id,source_version_retained=True,production_approved=False)
        conn.execute('INSERT INTO excel_import_sources VALUES (?,?,?,?,?,?,?)',
            (project_id,preview['source_sha256'],1,preview['configuration_sha256'],data,json.dumps(result,ensure_ascii=False),store.now()))
        conn.execute('INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)',(project_id,store.now(),'excel_configuration_imported',json.dumps(result,ensure_ascii=False)))
        return result
