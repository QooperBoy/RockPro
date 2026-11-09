import comtypes.client
from comtypes.automation import IDispatch
app=comtypes.client.GetBestInterface(comtypes.client.GetActiveObject('IronCAD.Application').QueryInterface(IDispatch))
assert all(app.Pages.Item(i).Saved for i in range(1,app.Pages.Count+1)), 'Unsaved documents; abort'
app.Quit()
print('Closed saved session')
