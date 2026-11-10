import sys,json
sys.stdout.reconfigure(encoding='utf-8')
from wholecase_common import *
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'));legacy,base,doc=connect(Path(cfg['folder'])/'Skeleton_probe_drop.ics');scene=doc.QueryInterface(ICAPI.IZSceneDoc)
p=scene.GetFirstChild();f=p.QueryInterface(ICAPI.IZPartFeatureMgr).GetFeatureAt(0).QueryInterface(ICAPI.IZElement);print('f',element_data(f),flush=True)
sb=f.QueryInterface(ICAPI.IZSizeBox);sb.LengthExpression='914 mm';sb.WidthExpression='602 mm';sb.HeightExpression='9.8 mm';p.QueryInterface(ICAPI.IZPart).Regenerate();scene.Update();print('after',element_data(p));print('feature',element_data(f));doc.Save()
