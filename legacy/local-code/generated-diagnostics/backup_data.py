import sqlite3,json
from pathlib import Path
root=Path('../Integracja/rockpro_cad')
out=Path('artifacts/pre-versioning-backup');out.mkdir(exist_ok=True)
with sqlite3.connect(root/'data/projects.sqlite3') as src,sqlite3.connect(out/'projects.sqlite3') as dst:
 src.backup(dst)
 print([dict(project_id=r[0],spec=json.loads(r[1])) for r in src.execute('SELECT project_id,spec FROM layouts')])
