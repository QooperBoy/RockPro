from inspect_case import *
app=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
path=OUT/'size_probe.ics'
shutil.copyfile(OUT/'working_input.ics',path)
_,doc=app.OpenFile2(str(path),False,False)
scene=doc.QueryInterface(A.IZSceneDoc)
try:
 e=scene.QueryInterface(A.IZSceneDocUtility).GetElementById(3);sb=e.QueryInterface(A.IZSizeBox)
 print('before',sb.Length,sb.Width,sb.Height,list(e.QueryInterface(A.IZPart).GetBoundingBox(True)),flush=True)
 p=scene.ParameterMgr.CreateParameter(A.Z_PARAMETER_TYPE_LENGTH,'RP_Length',2);p.Expression='2000 mm';p.ParamTableVisibility=True
 sb.LengthResizeBehavior=A.Z_RESIZE_ABOUT_SIZEBOX_CENTER
 sb.LengthExpression='Parent\\Params\\RP_Length'
 e.QueryInterface(A.IZSceneElement).ForceSetupParameterExpression();e.QueryInterface(A.IZPart).Regenerate();scene.Update()
 print('after',sb.Length,sb.Width,sb.Height,list(e.QueryInterface(A.IZPart).GetBoundingBox(True)),flush=True)
 scene.SaveAs(str(OUT/'size_probe_result.ics'),A.Z_LINKS_COPY_ALL,False)
finally:
 if doc.Modified:scene.SaveAsCopy(str(OUT/'size_probe_recovery.ics'),A.Z_LINKS_COPY_ALL,False)
 doc.Close()
