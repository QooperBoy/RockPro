import json,html
from pathlib import Path
root=Path(__file__).resolve().parent
cfg=json.loads((root/'skeleton_state.json').read_text(encoding='utf-8-sig'));folder=Path(cfg['folder']);rows=json.loads((folder/'legacy_panels.json').read_text(encoding='utf-8'))
trs=[]
for r in rows:
 d=sorted(r['dimensions_raw'],reverse=True)
 trs.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [r['half'],r['name'],*(f'{x:.2f}' for x in d)])+'</tr>')
page='''<!doctype html><meta charset="utf-8"><title>RockPro — rozpoznanie płyt</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;color:#20333d}table{border-collapse:collapse;width:100%}td,th{padding:12px;text-align:left;border-bottom:1px solid #ccd7dc}th{background:#e8f0f3}.note{padding:18px;background:#fff2ce}h1{font-size:28px}</style><h1>RockPro: geometria dwóch zespołów „konstrukcja”</h1><p>Odczyt z otwartej sceny Epson EB-PU2216B (2).ics; kopia zachowuje bieżący stan. Jednostki: mm. Wymiary formatek są obwiedniami istniejących płyt; nie uwzględniają obrysu wycięć.</p><table><tr><th>Zespół</th><th>Płyta</th><th>Długość</th><th>Szerokość</th><th>Grubość</th></tr>'''+''.join(trs)+'''</table><p>Obrys obu konstrukcji: 914 × 602 mm. Wysokość góry: 104,13 mm; dołu: 239,24 mm. Grubość zmierzona w modelu: 9,8 mm.</p><p class="note">Różnica źródłowa: tylna płyta dołu jest przesunięta o −3,02 mm w osi wysokości względem pozostałych ścian. Nowy prosty szkielet będzie miał tę płytę wyrównaną do pozostałych ścian. To jawna normalizacja wariantu koncepcyjnego, a nie wierna kopia tego przesunięcia. Nie stanowi dokumentacji produkcyjnej.</p><p>Zakres szkieletu: 10 pełnych płyt bez wycięć, okuć i danych produkcyjnych WoodLAB; wspólne parametry długości, głębokości i grubości oraz oddzielne wysokości góry i dołu.</p>'''
(folder/'Rozpoznanie_plyt.html').write_text(page,encoding='utf-8')
(folder/'skeleton_parameters.json').write_text(json.dumps({'length_mm':914,'depth_mm':602,'base_height_mm':239.24,'lid_height_mm':104.13,'thickness_mm':9.8,'display_gap_mm':30,'normalizations':['base back panel height offset -3.02 mm removed in clean conceptual skeleton'],'source':cfg['snapshot']},ensure_ascii=False,indent=2),encoding='utf-8')
print(folder/'Rozpoznanie_plyt.html')
