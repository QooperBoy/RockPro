import pathlib,json
p=pathlib.Path('artifacts/part-images-20261027/mapping.json');d=json.loads(p.read_text())
for row in d['items']:
 if row['id']=='410429':row['node_ids']=[43]
 if row['id']=='17251S':row['roots']=[192,78]
 if row['id'].startswith('EG-'):
  row['crop']=dict(axis=0,length_m=.12);row['label']='Render CAD · fragment profilu';row['source']='Fragment 120 mm wycięty widokiem z siatki profilu T1; pełny przekrój bez skalowania. Render poglądowy.'
p.write_text(json.dumps(d),encoding='utf-8')
