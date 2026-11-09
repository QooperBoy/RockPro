from comtypes import typeinfo
import json
rows=[]
for guid in ['{6EE9ED93-0C2B-4808-B138-F294D9A71B0A}', '{D8E3895D-8CA1-46CF-85F9-800B9A649F82}']:
 row={'guid':guid}
 try:row['query_path']=str(typeinfo.QueryPathOfRegTypeLib(guid,12,0,0))
 except Exception as e:row['query_error']=str(e)
 try:
  lib=typeinfo.LoadRegTypeLib(guid,12,0,0);a=lib.GetLibAttr();row['loaded_version']=[int(a.wMajorVerNum),int(a.wMinorVerNum)];row['passed']=True
 except Exception as e:row['load_error']=str(e);row['passed']=False
 rows.append(row)
print(json.dumps(rows))
raise SystemExit(0 if all(r['passed'] for r in rows) else 1)
