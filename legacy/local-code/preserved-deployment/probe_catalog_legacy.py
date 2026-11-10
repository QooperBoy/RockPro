exec(open('probe_document.py',encoding='utf-8').read().split("report['success']")[0])
import sys;sys.stdout.reconfigure(encoding='utf-8')
app=doc.Application
cats=app.Catalogs;cats._FlagAsMethod('Item');print('catalogs',cats.Count)
for i in range(1,app.Catalogs.Count+1):
 c=cats.Item(i)
 try:print('cat',c.Name,c.Entries.Count)
 except Exception as e:print(e)
 for j in range(1,min(c.Entries.Count,8)+1):
  en=c.Entries.Item(j);print(j,en.Label)
print('pages',app.Pages.Count)

