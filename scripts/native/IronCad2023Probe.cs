// Explicit native compatibility test; creates only an owned diagnostic model.
using System;
using System.IO;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;
class IronCad2023Probe {
 static JavaScriptSerializer J=new JavaScriptSerializer();
 static object Parameters(IZSceneElement e) {
  e.ForceSetupParameterExpression();var list=new List<object>();var pm=e.ParameterMgr;
  for(int i=0;i<pm.Count;i++){var p=pm.GetParameter(i);list.Add(new{name=p.Name,expression=p.Expression,value=p.Value});}
  return list;
 }
 [STAThread] static int Main(string[] args) {
  if(args.Length!=1)return 2;
  string folder=Path.GetFullPath(args[0]);if(Directory.Exists(folder))return 3;
  Directory.CreateDirectory(folder);IZDoc owned=null;IZSceneDoc scene=null;
  var report=new Dictionary<string,object>();bool passed=false;
  try {
   dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;
   if(!app.ApiVersion.StartsWith("25."))throw new Exception("Expected IronCAD 2023");
   report["api_version"]=app.ApiVersion;
   owned=app.OpenNewDoc(eZDocType.Z_SCENE,false,true,"");scene=(IZSceneDoc)owned;
   var profile=scene.CreateProfile();double[][] xy={new double[]{0,0},new double[]{0.1,0},new double[]{0.1,0.05},new double[]{0,0.05}};
   for(int i=0;i<4;i++)profile.CreateLine(xy[i],xy[(i+1)%4],i+1);
   var part=scene.CreatePart();((IZElement)part).Name="RockPro compatibility probe";
   var feature=((IZPartFeatureMgr)part).CreateExtrudeFeature(eZOperationType.Z_UNITE,false,0.02,0,0,profile,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB);
   part.Update();scene.Update();
   report["part_parameters"]=Parameters((IZSceneElement)part);
   report["feature_parameters"]=Parameters((IZSceneElement)feature);
   report["bounds_before"]=part.GetBody(true).GetBoundingBox();
   var parameter=scene.ParameterMgr.CreateParameter(eZParamType.Z_PARAMETER_TYPE_LENGTH,"RP_ProbeThickness",0.02);
   parameter.Expression="40 mm";
   // Explicit script-driven update, not a claimed native geometry expression.
   ((IZExtrudeFeature)feature).set_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_FORWARD,parameter.Value);
   part.Update();scene.Update();
   var bounds=(Array)part.GetBody(true).GetBoundingBox();
   if(Math.Abs(Convert.ToDouble(bounds.GetValue(5))-Convert.ToDouble(bounds.GetValue(2))-0.04)>1e-7)throw new Exception("Resize measurement failed");
   report["bounds_changed"]=bounds;report["binding_mode"]="script_driven_extrusion_from_scene_parameter";
   scene.SaveAs(Path.Combine(folder,"diagnostic.ics"),eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
   report["saved"]=owned.Name;
   owned.Close();owned=null;
   bool already;owned=app.OpenFile2(Path.Combine(folder,"diagnostic.ics"),false,false,out already);
   if(already)throw new Exception("Reopen ownership refused");scene=(IZSceneDoc)owned;
   parameter=scene.ParameterMgr.GetParameterByName("RP_ProbeThickness");
   if(Math.Abs(parameter.Value-0.04)>1e-7)throw new Exception("Reopened parameter differs");
   object first;scene.GetTopElement().GetChildrenZArray().Get(0,out first);part=(IZPart)first;
   bounds=(Array)part.GetBody(true).GetBoundingBox();
   if(Math.Abs(Convert.ToDouble(bounds.GetValue(5))-Convert.ToDouble(bounds.GetValue(2))-0.04)>1e-7)throw new Exception("Reopened geometry differs");
   report["bounds_reopened"]=bounds;
   parameter.Expression="20 mm";
   ((IZExtrudeFeature)((IZPartFeatureMgr)part).GetFeatureAt(0)).set_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_FORWARD,parameter.Value);
   part.Update();scene.Update();bounds=(Array)part.GetBody(true).GetBoundingBox();
   if(Math.Abs(Convert.ToDouble(bounds.GetValue(5))-Convert.ToDouble(bounds.GetValue(2))-0.02)>1e-7)throw new Exception("Post-reopen resize failed");
   report["bounds_restored"]=bounds;
   scene.SaveAs(Path.Combine(folder,"diagnostic_restored.ics"),eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
   passed=true;
  } catch(Exception ex){report["error"]=ex.ToString();}
  finally {
   if(owned!=null){try{if(owned.Modified)scene.SaveAs(Path.Combine(folder,"recovery.ics"),eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);owned.Close();}catch(Exception ex){report["cleanup_error"]=ex.ToString();passed=false;}}
   report["passed"]=passed;File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(report));
  }
  return passed?0:1;
 }
}
