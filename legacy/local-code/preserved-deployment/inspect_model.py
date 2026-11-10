import json
from pathlib import Path
from ironcad_adapter import connect, walk, parameters, parameter_data, ICAPI

source = Path(__file__).resolve().parent.parent / 'AI_CAD/T_1_1/Showcase_Epson_parametry.ics'
legacy, base, doc = connect(source)
scene = doc.QueryInterface(ICAPI.IZSceneDoc)
rows = []
for path, element in walk(scene.GetTopElement()):
    row = {'path': list(path), 'id': element.Id}
    try:
        row['parameters'] = [parameter_data(p) for p in parameters(element)]
    except Exception as exc:
        row['parameter_error'] = str(exc)
    rows.append(row)
Path(__file__).with_name('model_inventory.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print('Elements:', len(rows), flush=True)
for row in rows:
    if any(p['name'] in ('Larg', 'L_1', 'Prof', 'Alt') for p in row.get('parameters', [])):
        print(json.dumps(row, ensure_ascii=True), flush=True)
