import json
from pathlib import Path
from ironcad_adapter import connect, find, parameters, parameter_data, ICAPI
source = Path(__file__).resolve().parent.parent / 'AI_CAD/T_1_1/Showcase_Epson_parametry.ics'
legacy, base, doc = connect(source)
scene = doc.QueryInterface(ICAPI.IZSceneDoc)
rows = []
for path in [['góra', 'konstrukcja'], ['góra', 'konstrukcja', 'przód', 'WG', 'Formatka']]:
    elem = find(scene, path)
    row = {'path': path, 'id': elem.Id, 'parameters': [parameter_data(p) for p in parameters(elem)]}
    try:
        box = elem.QueryInterface(ICAPI.IZSizeBox)
        row['sizebox_m'] = [box.Length, box.Width, box.Height]
        row['length_expression'] = box.LengthExpression
    except Exception as exc:
        row['size_error'] = str(exc)
    try:
        row['bounding_box_m'] = elem.QueryInterface(ICAPI.IZFeature).GetBoundingBox()
    except Exception as exc:
        row['bbox_error'] = str(exc)
    rows.append(row)
    print(json.dumps(row, ensure_ascii=True), flush=True)
Path(__file__).with_name('target_inventory.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
