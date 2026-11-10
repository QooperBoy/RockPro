from pathlib import Path
import json
r=Path(__file__).resolve().parent
receipt=json.loads((r/'real-H7159-20261021-03/native_receipt.json').read_text(encoding='utf-8'))
poses=json.loads((r/'source-poses.json').read_text(encoding='utf-8'))
print('BINDING',json.dumps(receipt['source_binding']))
print('SOURCE SIGNATURE',json.dumps(receipt['source_body_signature']))
for row in poses['rows']:
 n=row['name'].lower()
 if n=='h7159' or any(x in n for x in ['płyta','plyta','floor','front','dno','przód','przod','sklej']):
  print('POSE',json.dumps({k:row.get(k) for k in ['id','name','path','kind','matrix_world_mm','bounding_box_local','bbox_world_mm']}))
