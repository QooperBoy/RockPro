from wholecase_common import *
cfg,legacy,base,doc,scene=get_doc(); u=scene.QueryInterface(ICAPI.IZSceneDocUtility)
e=u.GetElementById(9090);s=e.QueryInterface(ICAPI.IZSceneElement)
old=s.PositionTransformComponentValue[0];oldexp=s.PositionTransformComponentExpression[0]
print('rigid before',matrix(e)[3],old,flush=True)
try:
    s.PositionTransformComponentExpression[0]=f'{old:.17g} m + (Parent\\Parent\\Parent\\Params\\RP_Length - 914 mm)'
    scene.ParameterMgr.GetParameterByName('RP_Length').Expression='934 mm'
    scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update()
    print('rigid after',matrix(e)[3],s.PositionTransformComponentValue[0],flush=True)
finally:
    scene.ParameterMgr.GetParameterByName('RP_Length').Expression='914 mm'
    s.PositionTransformComponentExpression[0]=oldexp or f'{old:.17g} m'
    scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update()
f=u.GetElementById(854);sb=f.QueryInterface(ICAPI.IZSizeBox);oldh=sb.Height
try:
    print('profile before',bbox(u.GetElementById(853),True),flush=True)
    sb.HeightExpression=f'{oldh:.17g} m + (Parent\\Parent\\Parent\\Parent\\Params\\RP_Length - 914 mm)'
    scene.ParameterMgr.GetParameterByName('RP_Length').Expression='934 mm'
    scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update()
    print('profile after',bbox(u.GetElementById(853),True),'feature',sb.Height,flush=True)
finally:
    scene.ParameterMgr.GetParameterByName('RP_Length').Expression='914 mm'
    scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update();doc.Save()
