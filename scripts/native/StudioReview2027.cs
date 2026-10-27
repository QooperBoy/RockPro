// Explicit concept-panel adapter. No catalog hardware, machining or production approval.
using System;
using System.IO;
using System.Linq;
using System.Globalization;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;

namespace RockPro { public static class LatchInProcess {
static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=64000000};
static Dictionary<string,object> O(object x){return (Dictionary<string,object>)x;}
static double[] N(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
static string F(double x){return x.ToString("R",CultureInfo.InvariantCulture);}
static IZDoc Doc(object x){return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));}
static object State(IZBaseApp app){return ((Array)app.GetAllOpenDocs()).Cast<object>().Select(x=>{var d=Doc(x);return new {path=d.Name,guid=d.FileGUID,modified=d.Modified};}).OrderBy(x=>x.guid).ToArray();}
static string Expr(object raw,string[] names,int depth){var f=O(raw);var c=N(f["coefficients"]);string s=F(Convert.ToDouble(f["constant"]))+" mm";for(int i=0;i<c.Length;i++)if(c[i]!=0)s+="+("+F(c[i])+" * "+String.Concat(Enumerable.Repeat("Parent\\",depth))+"Params\\"+names[i]+")";return s;}
static void Param(IZParameterMgr mgr,string name,string expression,string notes){var p=mgr.CreateParameter(eZParamType.Z_PARAMETER_TYPE_LENGTH,name,0);p.Expression=expression;p.Notes=notes;}
static void Update(IZSceneDoc s){((IZAssembly)s.GetTopElement()).RegenerateParts(true);s.Update();}
static void Values(IZSceneDoc s,Dictionary<string,object> v){foreach(var kv in v)s.ParameterMgr.GetParameterByName(kv.Key).Expression=F(Convert.ToDouble(kv.Value))+" mm";Update(s);}
static Dictionary<string,IZPart> Parts(IZSceneDoc s){var r=new Dictionary<string,IZPart>();var a=s.GetTopElement().GetChildrenZArray();for(int i=0;i<s.GetTopElement().GetChildrenCount();i++){object x;a.Get(i,out x);r[((IZElement)x).Name]=(IZPart)x;}return r;}
static object Check(IZSceneDoc s,object[] specs,bool changed){
 var nodes=Parts(s);var rows=new List<object>();
 if(nodes.Count!=specs.Length)throw new Exception("Unexpected panel count");
 for(int i=0;i<specs.Length;i++){
  var p=O(specs[i]);string label=changed?null:(string)p["label"];
  // Changed previews use the same stable panel ordering and names.
  var part=label==null?nodes.Values.ElementAt(i):nodes[label];
  double[] b=N(part.GetBody(true).GetBoundingBox());var m=((IZSceneElement)part).GetTransformToGlobal();
  double[] size=N(p["size_mm"]),center=N(p["center_mm"]);
  for(int k=0;k<3;k++){
   double actual=(b[k+3]-b[k])*1000, pos=(b[k]+b[k+3])*500+m.GetValue(3,k)*1000;
   if(Math.Abs(actual-size[k])>.01 || Math.Abs(pos-center[k])>.01)throw new Exception("Panel measurement failed: "+i+" axis "+k+" size "+actual+"/"+size[k]+" center "+pos+"/"+center[k]+" bbox "+J.Serialize(b)+" translation "+m.GetValue(3,k)*1000);
  }
  rows.Add(new {name=((IZElement)part).Name,bounds_local_m=b});
 }
 return new {passed=true,panels=rows};
}
public static int Run(string folder){
 var report=new Dictionary<string,object>();IZDoc owned=null;IZSceneDoc scene=null;
 try{
  var req=O(J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));
  if((string)req["contract"]!="rockpro-studio-review-panels-v1")throw new Exception("Wrong concept contract");
  dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;
  if(!app.ApiVersion.StartsWith("29.")||app.GetProcessID()!=Convert.ToInt32(req["expected_pid"]))throw new Exception("Expected pinned IronCAD 2027 host");
  var before=State(app);report["before"]=before;report["api_version"]=app.ApiVersion;
  var outputs=new List<object>();
  foreach(object item in (object[])req["models"]){
   var spec=O(item);var pars=O(spec["parameters"]);string[] names=pars.Keys.ToArray();
   string output=Path.Combine(folder,(string)spec["filename"]);
   if(File.Exists(output))throw new Exception("Refusing overwrite");
   owned=app.OpenNewDoc(eZDocType.Z_SCENE,false,true,"");scene=(IZSceneDoc)owned;
   foreach(var kv in pars)Param(scene.ParameterMgr,kv.Key,F(Convert.ToDouble(kv.Value))+" mm",
    kv.Key.Contains("wnetrza")?"Wymagany wymiar wewnętrzny korpusu w osi wskazanej nazwą. Pokrywy są dodatkowymi sekcjami.":kv.Key.Contains("Grubosc")?"Grubość sklejki koncepcyjnej. Brak obróbki i tolerancji produkcyjnych.":"Głębokość sekcji pokrywy; top = wieko górne, front = pokrywa przednia. Koncepcja, wymaga sprawdzenia okuć.");
   var panels=(object[])spec["panels"];
   foreach(object raw in panels){
    var p=O(raw);double[] dims=N(p["size_mm"]),center=N(p["center_mm"]);
    var profile=scene.CreateProfile();double[][] points={new[]{0.0,0.0},new[]{dims[0]/1000,0.0},new[]{dims[0]/1000,dims[1]/1000},new[]{0.0,dims[1]/1000}};
    for(int k=0;k<4;k++)profile.CreateLine(points[k],points[(k+1)%4],k+1);
    var part=scene.CreatePart();((IZElement)part).Name=(string)p["label"];
    part.BOMDescription="KONCEPCJA Studio: nominalny panel, bez wycięć, profili i zatwierdzonego montażu okuć. Nie jest formatką produkcyjną.";
    var feature=(IZFeature)((IZPartFeatureMgr)part).CreateExtrudeFeature(eZOperationType.Z_UNITE,false,dims[2]/1000,0,0,profile,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB);
    var cross=(IZSceneElement)((IZExtrudeFeature)feature).CrossSection;
    var identity=cross.GetTransformToParent();identity.MakeIdentity();cross.SetTransformToParent(identity);
    var fe=(IZSceneElement)feature;identity=fe.GetTransformToParent();identity.MakeIdentity();fe.SetTransformToParent(identity);
    part.Update();var sizebox=(IZSizeBox)feature;sizebox.Reset(false);
    // A newly created extrusion retains a vendor default anchor even after its
    // section is normalized. Resize about the explicit local origin, otherwise
    // changing dimensions translates the panels around that stale anchor.
    identity=fe.GetAnchorTransform();identity.MakeIdentity();fe.SetAnchorTransform(identity);
    identity=fe.GetTransformToParent();identity.MakeIdentity();fe.SetTransformToParent(identity);
    sizebox.LengthResizeBehavior=eZResizeBehaviorType.Z_RESIZE_ABOUT_ANCHOR;
    sizebox.WidthResizeBehavior=eZResizeBehaviorType.Z_RESIZE_ABOUT_ANCHOR;
    sizebox.HeightResizeBehavior=eZResizeBehaviorType.Z_RESIZE_ABOUT_ANCHOR;
    sizebox.KeepAnchorFixedInSpace=true;fe.ForceSetupParameterExpression();
    var sizes=(object[])p["size_mm_formulas"];sizebox.LengthExpression=Expr(sizes[0],names,2);sizebox.WidthExpression=Expr(sizes[1],names,2);sizebox.HeightExpression=Expr(sizes[2],names,2);
    var se=(IZSceneElement)part;identity=se.GetAnchorTransform();identity.MakeIdentity();se.SetAnchorTransform(identity);
    var pose=se.GetTransformToParent();pose.MakeIdentity();for(int k=0;k<3;k++)pose.SetValue(3,k,(center[k]-dims[k]/2)/1000);se.SetTransformToParent(pose);
    var positions=(object[])p["center_mm_formulas"];
    for(int k=0;k<3;k++)Param(se.ParameterMgr,"RP_Polozenie"+"XYZ"[k],"("+Expr(positions[k],names,1)+") - ("+Expr(sizes[k],names,1)+") / 2","Wyliczone z wymiarów sceny. Nie zmieniać ręcznie.");
    se.ForceSetupParameterExpression();for(int k=0;k<3;k++)se.set_PositionTransformComponentExpression((eZTransformComponentType)k,"RP_Polozenie"+"XYZ"[k]);
    part.SurfaceFinish.Color=0x808040;
   }
   Update(scene);var baseline=Check(scene,panels,false);object changed;
   try{Values(scene,O(spec["changed_parameters"]));changed=Check(scene,(object[])spec["changed_panels"],true);}
   finally{Values(scene,pars);}
   scene.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);if(owned.Modified||!File.Exists(output))throw new Exception("Save failed");
   owned.Close();owned=null;bool already;owned=app.OpenFile2(output,false,false,out already);if(already)throw new Exception("Reopen ownership error");scene=(IZSceneDoc)owned;
   var reopened=Check(scene,panels,false);object reopenedChanged;
   try{Values(scene,O(spec["changed_parameters"]));reopenedChanged=Check(scene,(object[])spec["changed_panels"],true);}
   finally{Values(scene,pars);}
   Check(scene,panels,false);
   scene.AdjustCameraToFitShapeInRect(1200,900);
   scene.ExportImage(Path.Combine(folder,Path.GetFileNameWithoutExtension(output)+".png"),eZImageFormat.Z_IMAGE_PNG,1200,900,false);
   if(owned.Modified)scene.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
   outputs.Add(new {path=output,baseline=baseline,resize=changed,reopened=reopened,resize_after_reopen=reopenedChanged,status="concept_panels_only_not_manufacturing"});
   owned.Close();owned=null;scene=null;
  }
  report["outputs"]=outputs;report["after"]=State(app);report["existing_documents_preserved"]=J.Serialize(before)==J.Serialize(report["after"]);
  if(!(bool)report["existing_documents_preserved"])throw new Exception("Preexisting documents changed");
  report["passed"]=true;
 }catch(Exception e){report["passed"]=false;report["error"]=e.ToString();}
 finally{
  if(owned!=null)try{scene.SaveAs(Path.Combine(folder,"recovery-owned.ics"),eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);owned.Close();}catch(Exception e){report["recovery_error"]=e.ToString();}
  File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(report));
 }
 return report.ContainsKey("passed")&&(bool)report["passed"]?0:1;
}
}}
