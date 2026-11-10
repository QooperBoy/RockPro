import comtypes.client,json
from comtypes.automation import IDispatch
app=comtypes.client.GetBestInterface(comtypes.client.GetActiveObject('IronCAD.Application').QueryInterface(IDispatch))
rows=[]
for i in range(1,app.Pages.Count+1):
 d=app.Pages.Item(i)
 rows.append(dict(name=d.FullName,saved=bool(d.Saved)))
print(json.dumps(rows))
