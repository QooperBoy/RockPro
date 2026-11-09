exec(open('probe_document.py',encoding='utf-8').read().split("report['success']")[0])
import sys;sys.stdout.reconfigure(encoding='utf-8')
cfg=json.loads(Path('skeleton_state.json').read_text(encoding='utf-8-sig'));folder=Path(cfg['folder']);app=doc.Application
cats=app.Catalogs;cats._FlagAsMethod('Item');block=cats.Item(1).Entries.Item(1).Object
print('block',block.Name)
block._FlagAsMethod('save');print('saved block',block.save(0,str(folder/'Clean_block.ics')))
pages=app.Pages;pages._FlagAsMethod('Add');new=pages.Add('',False);print('new',new.Name)
part=new.Shape.ChildShapes.Add(str(folder/'Clean_block.ics'));print('part',part.Name)
print('saved',new.SaveAsEx2(str(folder/'Skeleton_probe.ics'),3,False))
