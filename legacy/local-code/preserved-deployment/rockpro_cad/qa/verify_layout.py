import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'rockpro_cad'/'mcp'))
from worker import dispatch
pid=(root/'rockpro_cad'/'qa'/'layout_demo_id.txt').read_text()
p=dispatch('get_project',dict(project_id=pid))['project']
l=dispatch('get_layout',dict(project_id=pid))
s=p['snapshots'][0]
report=json.loads(Path(s['report_path']).read_text(encoding='utf-8'))
assert report['passed'] and report['source_unchanged'] and s['integrity']=='verified'
assert l['spec']['arrangement']=='Z' and l['spec']['separator']==9 and l['spec']['side']=='X'
assert all(abs(l['parameters'][k]-report['after_reopen']['measurements']['parameters_mm'][k])<.002 for k in l['parameters'])
out=dict(project_id=pid,source=p['source'],internal=l['internal'],external=l['external'],saved_layout=l['spec'],cad_validation=report['passed'],source_unchanged=report['source_unchanged'],snapshot_integrity=s['integrity'])
(root/'rockpro_cad'/'qa'/'layout_acceptance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out))
