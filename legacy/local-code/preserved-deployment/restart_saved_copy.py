exec(open('probe_document.py',encoding='utf-8').read().split("report['success']")[0])
cfg=json.loads(Path('skeleton_state.json').read_text(encoding='utf-8-sig'))
assert Path(cfg['snapshot']).is_file() and Path(cfg['snapshot']).stat().st_size>100000
assert doc.FullName.lower()==cfg['snapshot'].lower()
print('snapshot bytes',Path(cfg['snapshot']).stat().st_size)
doc.save();print('saved');doc.Application.Quit();print('quit requested')
