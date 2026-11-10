import json,pathlib,array,math
p=pathlib.Path('artifacts/registry-native-20261024-01/viewer');d=json.loads((p/'model.json').read_text());raw=(p/'geometry.bin').read_bytes()
for root in (42,192,380):
 for e in d['elements']:
  if e['root_id']!=root:continue
  a=array.array('f');a.frombytes(raw[e['offset']:e['offset']+e['floats']*4]);m=e['matrix'];pts=[[sum(m[k+4*j]*a[i+j]for j in range(3))+m[12+k]for k in range(3)]for i in range(0,len(a),3)];b=[round(min(p[k]for p in pts)*1000,1)for k in range(3)]+[round(max(p[k]for p in pts)*1000,1)for k in range(3)];print(root,e['node_id'],b)
