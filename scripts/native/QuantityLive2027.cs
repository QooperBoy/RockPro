// Autonomous-controller proof: setter deliberately does not call Apply or toggle suppression.
using System;using System.IO;using System.Reflection;using System.Linq;using System.Collections.Generic;using System.Runtime.InteropServices;using System.Web.Script.Serialization;using interop.ICApiIronCAD;
namespace RockPro{public static class LatchInProcess{
static Dictionary<string,object> O(object x){return (Dictionary<string,object>)x;}
static IZDoc D(object x){return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));}
public static int Run(string folder){var j=new JavaScriptSerializer{MaxJsonLength=64000000};var r=new Dictionary<string,object>();bool pass=false;
try{
 var q=O(j.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));if(System.Diagnostics.Process.GetCurrentProcess().Id!=Convert.ToInt32(q["expected_pid"]))throw new Exception("Host changed");
 dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;if(!app.ApiVersion.StartsWith("29."))throw new Exception("2027 required");
 string path=(string)q["output"];if(Path.GetFileName(path)!="RockPro_Hisense85_r003_liczba_okuc_IC2027.ics")throw new Exception("Wrong revision");
 var doc=((Array)app.GetAllOpenDocs()).Cast<object>().Select(D).Single(d=>d.Name==path);var s=(IZSceneDoc)doc;var u=(IZSceneDocUtility)s;
 var props=s.GetTopElement().get_CustomPropMgr(false);string text=(string)props.GetValueByName("RockPro.MountCounts.v1");var manifest=O(j.DeserializeObject(text));if((string)manifest["contract"]!="rockpro-tv-counts-v2")throw new Exception("Wrong manifest");
 string mode=(string)q["mode"];int n=Convert.ToInt32(q["number"]);
 if(mode=="status"){
  string status=s.ParameterMgr.GetParameterByName("RP_IloscOkuc_Status").TextParameterValue;
  bool expected=Convert.ToBoolean(q["expect_error"]);if(status.StartsWith("BŁĄD",StringComparison.Ordinal)!=expected)throw new Exception("Unexpected quantity status: "+status);
  r["status"]=status;
 }else if(mode=="switch"){
  foreach(var assembly in AppDomain.CurrentDomain.GetAssemblies()){var type=assembly.GetType("RockPro.CAD.MountCountController");if(type!=null)type.GetMethod("Stop").Invoke(null,null);}
  var controller=Assembly.LoadFrom((string)q["controller"]).GetType("RockPro.CAD.MountCountController");controller.GetField("Suspended").SetValue(null,false);controller.GetMethod("Start").Invoke(null,new object[]{app});app.ActiveDoc=doc;r["controller_version"]=controller.Assembly.GetName().Version.ToString();
 }else if(mode=="set"){
  foreach(var row in ((object[])manifest["rows"]).Select(O))s.ParameterMgr.GetParameterByName((string)row["count"]).Expression=n.ToString();
  s.ParameterMgr.GetParameterByName("RP_GlebokoscSkrzyni").Expression=q["depth"]+" mm";
  app.ActiveDoc=doc;s.Update();r["manual_suppression_changes"]=0;r["manual_apply_calls"]=0;
 }else{
  var rows=new List<object>();
  foreach(var row in ((object[])manifest["rows"]).Select(O)){
   int actual=(int)Math.Round(s.ParameterMgr.GetParameterByName((string)row["count"]).Value);if(actual!=n)throw new Exception("Count value mismatch");
   var slots=(object[])row["slots"];int active=0;
   for(int i=0;i<slots.Length;i++){
    foreach(object id in (object[])slots[i])if(u.GetElementById(Convert.ToInt32(id)).GetStateStatus(eZElementState.Z_SUPPRESSED)!=(i>=n))throw new Exception("Autonomous suppression not synchronized: "+id);
    if(i<n){
     active++;
     double center=s.ParameterMgr.GetParameterByName((string)row["center"]).Value*1000;
     double spread=s.ParameterMgr.GetParameterByName((string)row["spread"]).Value*1000;
     double expected=-1011.5+center+(n==1?0:(-0.5+(double)i/(n-1))*spread);
     foreach(object id in (object[])slots[i]){var e=u.GetElementById(Convert.ToInt32(id));if(e.Type!=eZElementType.Z_ELEMENT_ASSEMBLY)continue;double actualY=((IZSceneElement)e).GetTransformToGlobal().GetValue(3,1)*1000;if(Math.Abs(actualY-expected)>.08)throw new Exception("Row spacing mismatch "+id+": "+actualY+" expected "+expected);}
    }
   }
   rows.Add(new{count=row["count"],value=actual,active_slots=active});
  }
  foreach(var pose in ((object[])manifest["poses"]).Select(O)){
   var element=u.GetElementById(Convert.ToInt32(pose["id"]));if(element.GetStateStatus(eZElementState.Z_SUPPRESSED))continue;
   var matrix=((IZSceneElement)element).GetTransformToGlobal();var expected=((Array)pose["world"]).Cast<object>().Select(Convert.ToDouble).ToArray();
   if(Enumerable.Range(0,12).Max(k=>Math.Abs(matrix.GetValue(k/4,k%4)-expected[k]))>1e-8)throw new Exception("Catalog rotation or scale changed "+pose["id"]);
  }
  r["rows"]=rows;r["depth_mm"]=s.ParameterMgr.GetParameterByName("RP_GlebokoscSkrzyni").Value*1000;
  if(mode=="save"){
   foreach(var row in ((object[])manifest["rows"]).Select(O)){
    string count=(string)row["count"];
    if(count.StartsWith("RP_Uchwyty")){
     string center=(string)row["center"];
     string height=count.Replace("RP_Uchwyty","RP_Uchwyt").Replace("_Liczba","_Wysokosc");
     s.ParameterMgr.GetParameterByName(height).Notes="Wspólna wysokość środków wszystkich uchwytów tego bocznego rzędu. "+(count.Contains("Czapka")?"Liczona od dolnej krawędzi sklejki czapki.":"Liczona od spodu sklejki dna, bez kół.")+" Nazwa zachowana z R002; przesuwają się wszystkie wystąpienia i ich wycięcia.";
     s.ParameterMgr.GetParameterByName(center).Notes="Środek całego bocznego rzędu uchwytów w osi Y, od przedniej krawędzi sklejki. Liczbę sztuk zmienia "+count+"; rozstaw skrajnych osi ustala osobny parametr Rozstaw. Otwory podążają za każdym wystąpieniem.";
    }
   }
   var c=(IZCamera)s.CameraMgr.ActiveCamera;c.Perspective=false;c.Direction=new double[]{.65,.85,-.5};c.Up=new double[]{0,0,1};s.AdjustCameraToFitShapeInRect(1500,1100);s.Redraw();s.ExportImage(Path.Combine(folder,"final.png"),eZImageFormat.Z_IMAGE_PNG,1500,1100,true);
   s.SaveAs(path,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
   r["parameters"]=Enumerable.Range(0,s.ParameterMgr.Count).Select(i=>s.ParameterMgr.GetParameter(i)).Select(p=>new{name=p.Name,expression=p.Expression,value=p.Type==eZParamType.Z_PARAMETER_TYPE_TEXT?0:p.Value,text=p.Type==eZParamType.Z_PARAMETER_TYPE_TEXT?p.TextParameterValue:null,type=p.Type.ToString(),notes=p.Notes}).ToArray();
  }
 }
 pass=true;
}catch(Exception e){r["error"]=e.ToString();}r["passed"]=pass;File.WriteAllText(Path.Combine(folder,"result.json"),j.Serialize(r));return pass?0:1;
}}}
