from wholecase_common import *
cfg,legacy,base,doc,scene=get_doc()
u=scene.QueryInterface(ICAPI.IZSceneDocUtility)
pm=scene.ParameterMgr
try:p=pm.GetParameterByName('RP_Length')
except Exception:p=None
if not p:p=pm.CreateParameter(ICAPI.Z_PARAMETER_TYPE_LENGTH,'RP_Length',.914)
p.Expression='914 mm'
p.Notes='Dlugosc konstrukcji dolu; wspolna zmiana gory i dolu.'
e=u.GetElementById(174)
sb=e.QueryInterface(ICAPI.IZSizeBox)
orig=sb.LengthExpression
print('before',sb.Length,flush=True)
try:
    sb.LengthExpression='Parent\\Parent\\Params\\RP_Length - 18.5 mm'
    print('linked',sb.Length,sb.LengthExpression,flush=True)
    for v in [914,934,914]:
        p.Expression=f'{v} mm'
        e.QueryInterface(ICAPI.IZAssembly).RegenerateParts(True)
        scene.Update()
        print('variant',v,'container',sb.Length,'bbox',bbox(e,True),flush=True)
        for id in [180,188,196]:
            t=u.GetElementById(id)
            print(id,list(t.QueryInterface(ICAPI.IZFeature).GetBoundingBox()),flush=True)
finally:
    p.Expression='914 mm'
    e.QueryInterface(ICAPI.IZAssembly).RegenerateParts(True)
    scene.Update()
    doc.Save()
