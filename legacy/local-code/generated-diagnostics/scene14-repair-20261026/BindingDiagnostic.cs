using System;using System.IO;using System.Linq;using System.Collections.Generic;using System.Runtime.InteropServices;using System.Web.Script.Serialization;using interop.ICApiIronCAD;
namespace RockPro { public static class LatchInProcess {
public static int Run(string folder){var output=new List<object>();IZElement copy=null;try{
dynamic l=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)l.ZIronCADApp;var doc=app.ActiveDoc;if(doc.Name!="Scene14")throw new Exception("Wrong scene");var scene=(IZSceneDoc)doc;var top=(IZAssembly)scene.GetTopElement();var all=top.GetChildrenZArray();IZElement original=null;
for(int i=0;i<top.GetChildrenCount();i++){object o;all.Get(i,out o);var e=(IZElement)o;if(e.Name=="RockPro / handle/left/1")original=e;}
copy=(IZElement)((Array)((IZSceneElement)original).CreateCopies(1,null)).GetValue(0);copy.Name="Temporary binding diagnostic";var se=(IZSceneElement)copy;
var pm=se.ParameterMgr;var p=pm.CreateParameter(eZParamType.Z_PARAMETER_TYPE_LENGTH,"ProbeLocal",.125);
foreach(string expr in new[]{"ProbeLocal","Params\\ProbeLocal","Parent\\Params\\RP_Depth/4","Parent\\RP_Depth/4","RP_Depth/4"}){
try{se.ForceSetupParameterExpression();se.set_PositionTransformComponentExpression(eZTransformComponentType.Z_TRANS_W,expr);top.RegenerateParts(true);scene.Update();p.Expression="140 mm";top.RegenerateParts(true);scene.Update();output.Add(new{expr=expr,stored=se.get_PositionTransformComponentExpression(eZTransformComponentType.Z_TRANS_W),position=se.GetTransformToParent().GetValue(3,1)*1000});p.Expression="125 mm";}catch(Exception ex){output.Add(new{expr=expr,error=ex.Message});}}
}catch(Exception e){output.Add(new{error=e.ToString()});}finally{if(copy!=null)copy.Remove();}File.WriteAllText(Path.Combine(folder,"result.json"),new JavaScriptSerializer().Serialize(output));return 0;}
}}
