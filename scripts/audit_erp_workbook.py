"""Read-only OOXML audit. Never evaluates formulas or saves the source workbook."""
import collections
import hashlib
import json
import posixpath
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as E
import zipfile

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def audit(path,folder):
    path,folder=Path(path),Path(folder);folder.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    report=dict(source_sha256=digest,source_bytes=path.stat().st_size,sheets=[])
    with zipfile.ZipFile(path) as z:
        ss=E.fromstring(z.read('xl/sharedStrings.xml'))
        strings=[''.join(t.text or '' for t in x.iter('{'+NS['m']+'}t')) for x in ss]
        book=E.fromstring(z.read('xl/workbook.xml'))
        sheets=book.find('m:sheets',NS)
        relationships={r.get('Id'):r.get('Target') for r in E.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        names=[x.get('name') for x in sheets]
        for index,name in enumerate(names,1):
            stat=dict(name=name,rows=0,cells=0,formulas=0,errors={},formula_samples=[],row_labels=[],first_rows=[],header_cells={})
            errors=collections.Counter();formula_samples=[]
            target=relationships[sheets[index-1].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            member=posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/'+target)
            with z.open(member) as stream:
                for _,node in E.iterparse(stream,events=['end']):
                    if node.tag!='{'+NS['m']+'}row':continue
                    number=int(node.get('r'));cells={}
                    stat['rows']+=1
                    for cell in node:
                        addr=cell.get('r');value=cell.find('m:v',NS);f=cell.find('m:f',NS);kind=cell.get('t','n')
                        text=value.text if value is not None else None
                        if kind=='s' and text is not None:text=strings[int(text)]
                        if kind=='inlineStr':text=''.join(t.text or '' for t in cell.iter('{'+NS['m']+'}t'))
                        item=dict(value=text,type=kind)
                        if f is not None:
                            item.update(formula=f.text,formula_attributes=dict(f.attrib));stat['formulas']+=1
                            if f.text and len(formula_samples)<24:formula_samples.append(dict(cell=addr,formula=f.text,attributes=dict(f.attrib),cached=text))
                        if text is not None or f is not None:stat['cells']+=1
                        if kind=='e':errors[text]+=1
                        if number<=70:cells[addr]=item
                        if name=='Stany magazynowe' and number<=20:stat['header_cells'][addr]=item
                        if re.fullmatch('A[0-9]+',addr or '') and kind in ('s','inlineStr') and len(stat['row_labels'])<100:
                            stat['row_labels'].append([addr,text])
                    if number<=70 and cells:stat['first_rows'].append(dict(row=number,cells=cells))
                    node.clear()
            stat['errors']=dict(errors);stat['formula_samples']=formula_samples
            report['sheets'].append(stat)
            (folder/'audit-progress.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(name.encode('ascii','backslashreplace').decode(),stat['rows'],stat['cells'],stat['formulas'],stat['errors'],flush=True)
        drawings=[]
        for member in z.namelist():
            if re.fullmatch(r'xl/drawings/drawing\d+\.xml',member):
                tree=E.fromstring(z.read(member));drawings.append(dict(file=member,anchors=len(tree)))
        report['drawings']=drawings
        report['media_count']=sum(n.startswith('xl/media/') for n in z.namelist())
        report['has_vba']=any('vbaProject' in n for n in z.namelist())
        report['has_external_links']=any(n.startswith('xl/externalLinks/') for n in z.namelist())
    report['source_unchanged']=hashlib.sha256(path.read_bytes()).hexdigest()==digest
    (folder/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':audit(sys.argv[1],sys.argv[2])
