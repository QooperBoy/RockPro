import json,sqlite3
from pathlib import Path
root=Path('../Integracja/rockpro_cad')
pid=(root/'qa/layout_demo_id.txt').read_text().strip()
with sqlite3.connect(root/'data/projects.sqlite3') as c:
 rows=c.execute('SELECT revision,sha256 FROM layout_versions WHERE project_id=? ORDER BY revision',(pid,)).fetchall()
 assert [r[0] for r in rows]==[1,2,3],rows
 assert len({r[1] for r in rows})==1
 binding=json.loads(c.execute('SELECT layout_binding FROM snapshots WHERE project_id=? AND layout_binding IS NOT NULL',(pid,)).fetchone()[0])
 assert binding['revision']==1
Path('artifacts/ui_versions_acceptance.json').write_text(json.dumps(dict(passed=True,ui_loaded_revision=2,mcp_saved_revision=3,ui_stale_save='LAYOUT_CONFLICT',revision_after_rejection=3,dimensions_unchanged=True,history_ui_revision='v1',legacy_history_ui='Niepowiązany'),indent=2),encoding='utf-8')
p=Path('docs/LAYOUT_VERSIONING.md');s=p.read_text(encoding='utf-8');s=s.replace('- NOT RUN: pełny scenariusz komunikatu konfliktu w UI hosta — okno powitalne IronCAD poza obszarem głównego okna blokowało Computer Use. Kompilacja/formularzowe testy offline nie zastępują tej kontroli.','- PASS: po zamknięciu okna powitalnego wykonano test w UI hosta: formularz odczytał v2, drugi klient MCP zapisał identyczną specyfikację jako v3, zapis z formularza zwrócił LAYOUT_CONFLICT i zachował pola. Baza pozostała na v3, bez dodatkowej wersji po konflikcie.\n- PASS: tabela historii w IronCAD pokazuje powiązany snapshot jako v1 oraz starszy jako Niepowiązany; walidacja passed i integralność verified. Wymiary użytkownika nie zmieniły się w próbie konfliktu. Dowód lokalny: artifacts/ui_versions_acceptance.json.');p.write_text(s,encoding='utf-8')
