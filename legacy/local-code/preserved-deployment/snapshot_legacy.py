exec(open('probe_document.py',encoding='utf-8').read().split("report['success']")[0])
from datetime import datetime,timezone
folder=Path(__file__).resolve().parent/'skeleton'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');folder.mkdir(parents=True)
source=doc.FullName
out=folder/'Epson_source_snapshot.ics'
print('SaveAs',doc.SaveAsEx2(str(out),3,False))
print('Current',doc.FullName)
Path('skeleton_state.json').write_text(json.dumps({'folder':str(folder),'source':source,'snapshot':str(out)},ensure_ascii=False,indent=2),encoding='utf-8')
