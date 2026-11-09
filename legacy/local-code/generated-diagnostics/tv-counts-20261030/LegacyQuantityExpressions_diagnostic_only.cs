// Quantity-controlled mounting rows on a new copy of the explicitly pinned R002 snapshot.
using System;using System.IO;using System.Linq;using System.Collections.Generic;
using System.Globalization;using System.Reflection;using System.Runtime.InteropServices;
using System.Text.RegularExpressions;using System.Web.Script.Serialization;using interop.ICApiIronCAD;
namespace RockPro {public static class LatchInProcess {
static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=64000000};
static Dictionary<string,object> Q;static IZSceneDoc S;static IZSceneDocUtility U;
static Dictionary<int,Dictionary<string,object>> Rows;static List<Binding> Bindings;
static List<object> ManifestRows;static Type Controller;static string Progress;
class Binding {public int id,root;public bool cut;public double[] world,lengths;public Dictionary<int,double[]> bodies;}
static Dictionary<string,object> O(object x){return (Dictionary<string,object>)x;}
static double[] N(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
static string F(double x){return x.ToString("G16",CultureInfo.InvariantCulture);}
static IZDoc D(object x){return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));}
static string Hash(string p){using(var s=File.OpenRead(p))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant();}
static void Mark(string t){File.AppendAllText(Progress,DateTime.UtcNow.ToString("o")+" "+t+Environment.NewLine);}
static double[] M(IZSceneElement e,bool world=true){var m=world?e.GetTransformToGlobal():e.GetTransformToParent();return Enumerable.Range(0,16).Select(i=>m.GetValue(i/4,i%4)).ToArray();}
static void Set(IZSceneElement e,double[] a){var m=e.GetTransformToParent();for(int i=0;i<16;i++)m.SetValue(i/4,i%4,a[i]);e.SetTransformToParent(m);}
static IZParameter P(string n){return S.ParameterMgr.GetParameterByName(n);}
static double V(string n){return P(n).Value*1000;}
static void Param(IZParameterMgr mgr,string n,string exp,bool scalar=false,string note="Położenie montażowe; wynik parametrów sceny, nie edytować tutaj."){
 IZParameter p=null;for(int i=0;i<mgr.Count;i++)if(mgr.GetParameter(i).Name==n)p=mgr.GetParameter(i);if(p==null)p=mgr.CreateParameter(scalar?eZParamType.Z_PARAMETER_TYPE_SCALAR:eZParamType.Z_PARAMETER_TYPE_LENGTH,n,0);p.Expression=exp;if(String.IsNullOrWhiteSpace(p.Expression))throw new Exception("Rejected native expression for "+n+": "+exp);p.Notes=note;
}
static int Depth(IZElement e){int n=0;while(e.GetParent()!=null){e=e.GetParent();n++;if(n>30)throw new Exception("Hierarchy budget");}return n;}
static string Ref(string expression,int depth){return Regex.Replace(expression,@"\bRP_[A-Za-z0-9_]+\b",m=>String.Concat(Enumerable.Repeat("Parent\\",depth))+"Params\\"+m.Value);}
static string[] Zero(){return new[]{"0 mm","0 mm","0 mm"};}
static double[][] Shift(int id){var all=O(Q["shifts"]);return ((object[])all[id.ToString()]).Select(N).ToArray();}
static string[] ShiftExpression(int id){var c=Shift(id);var ns=(object[])Q["primary"];var basis=N(Q["base"]);return Enumerable.Range(0,3).Select(k=>"0 mm"+String.Concat(Enumerable.Range(0,6).Where(j=>Math.Abs(c[k][j])>1e-8).Select(j=>" + ("+F(c[k][j])+")*("+ns[j]+" - "+F(basis[j])+" mm)"))).ToArray();}
static double[] Local(double[] world,double[] parent){var r=new double[16];r[15]=1;for(int a=0;a<3;a++){for(int b=0;b<3;b++)r[a*4+b]=Enumerable.Range(0,3).Sum(k=>world[a*4+k]*parent[b*4+k]);r[12+a]=Enumerable.Range(0,3).Sum(k=>(world[12+k]-parent[12+k])*parent[a*4+k]);}return r;}
static double[] Rotate(double[] m,double[] anchor,double angle,double[] target){var r=(double[])m.Clone();double c=Math.Cos(angle),s=Math.Sin(angle);for(int i=0;i<3;i++){r[i*4]=m[i*4]*c-m[i*4+1]*s;r[i*4+1]=m[i*4]*s+m[i*4+1]*c;}double x=m[12]-anchor[0],y=m[13]-anchor[1];r[12]=target[0]+x*c-y*s;r[13]=target[1]+x*s+y*c;r[14]=target[2]+m[14]-anchor[2];return r;}
static List<IZPart> Parts(IZElement e){var result=new List<IZPart>();if(e.Type==eZElementType.Z_ELEMENT_PART){result.Add((IZPart)e);return result;}var a=e.GetChildrenZArray();for(int i=0;i<e.GetChildrenCount();i++){object x;a.Get(i,out x);result.AddRange(Parts((IZElement)x));}return result;}
static double[] WorldBox(IZPart p){var b=N(p.GetBody(true).GetBoundingBox());var m=M((IZSceneElement)p);var points=new List<double[]>();for(int i=0;i<8;i++){var v=new[]{b[(i&1)==0?0:3],b[(i&2)==0?1:4],b[(i&4)==0?2:5]};points.Add(Enumerable.Range(0,3).Select(j=>(m[12+j]+Enumerable.Range(0,3).Sum(k=>v[k]*m[k*4+j]))*1000).ToArray());}return Enumerable.Range(0,3).Select(k=>points.Min(p0=>p0[k])).Concat(Enumerable.Range(0,3).Select(k=>points.Max(p0=>p0[k]))).ToArray();}
static double HalfWidth(IZElement e,int axis){double origin=M((IZSceneElement)e)[12+axis]*1000;return Parts(e).Select(WorldBox).Max(b=>Math.Max(Math.Abs(b[axis]-origin),Math.Abs(b[axis+3]-origin)));}
static IZElement Copy(IZElement original){var se=(IZSceneElement)original;var m=se.GetTransformToParent();m.MakeIdentity();var items=(Array)se.CreateCopies(1,m);if(items.Length!=1)throw new Exception("One copy expected");return (IZElement)items.GetValue(0);}
static void Bind(IZSceneElement e,double[] world,string[] delta,int parentId,string label,bool cut,int root){
 var element=(IZElement)e;var parent=(IZSceneElement)U.GetElementById(parentId);var pm=M(parent);var local=Local(world,pm);
 var anchor=e.GetAnchorTransform();anchor.MakeIdentity();e.SetAnchorTransform(anchor);e.AnchorBehavior=eZAnchorBehavior.Z_ANCHOR_BEHAVIOR_FIXED_POSITION;Set(e,local);
 int depth=Convert.ToInt32(Rows[parentId]["depth"])+1;var parentMove=ShiftExpression(parentId);
 for(int k=0;k<3;k++)Param(e.ParameterMgr,"RP_QWorld"+"XYZ"[k],Ref(delta[k],depth));
 for(int a=0;a<3;a++){
  string expr=F(local[12+a]*1000)+" mm";
  for(int k=0;k<3;k++)if(Math.Abs(pm[a*4+k])>1e-8)expr+=" + ("+F(pm[a*4+k])+")*(("+"RP_QWorld"+"XYZ"[k]+")-("+Ref(parentMove[k],depth)+"))";
  Param(e.ParameterMgr,"RP_Polozenie"+"XYZ"[a],expr);
 }
 e.ForceSetupParameterExpression();for(int a=0;a<3;a++)e.set_PositionTransformComponentExpression((eZTransformComponentType)a,"RP_Polozenie"+"XYZ"[a]);
 element.Name="RockPro | Liczba | "+label;
 var b=new Binding{id=element.Id,root=root,world=world,cut=cut};
 if(cut){var p=((IZExtrudeFeature)e).CrossSection;b.world=M((IZSceneElement)p);b.lengths=((Array)p.GetCurveIds()).Cast<object>().Select(x=>p.GetCurveLength(Convert.ToInt32(x))).OrderBy(x=>x).ToArray();}
 else {var parts=Parts(element);b.bodies=parts.ToDictionary(x=>((IZElement)x).Id,x=>N(x.GetBody(true).GetBoundingBox()));for(int i=0;i<parts.Count;i++)((IZElement)parts[i]).Name="RockPro | Liczba | "+label+" — podczęść "+(i+1).ToString("D2")+" (rola do identyfikacji)";}
 Bindings.Add(b);
}
static IZFeature FindFeature(int part,int feature){var m=(IZPartFeatureMgr)U.GetElementById(part);for(int i=0;i<m.GetFeaturesCount();i++)if(((IZElement)m.GetFeatureAt(i)).Id==feature)return m.GetFeatureAt(i);throw new Exception("Missing cut "+feature);}
static int Cut(Dictionary<string,object> q,double[] sourceAnchor,double angle,double[] target,string[] delta,string label,int root){
 int part=Convert.ToInt32(q["target_part"]);var targetPart=(IZPart)U.GetElementById(part);
 var original=FindFeature(Convert.ToInt32(q["source_part"]),Convert.ToInt32(q["source_feature"]));var ex=(IZExtrudeFeature)original;
 var world=Rotate(M((IZSceneElement)original),sourceAnchor,angle,target);
 var crossLocal=M((IZSceneElement)ex.CrossSection,false);var profile=S.CreateProfile();ex.CrossSection.CopyCurvesTo(profile);
 var fresh=((IZPartFeatureMgr)targetPart).CreateExtrudeFeature(eZOperationType.Z_SUBTRACT,false,ex.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_FORWARD),ex.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_BACKWARD),0,profile,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB);
 Set((IZSceneElement)((IZExtrudeFeature)fresh).CrossSection,crossLocal);((IZExtrudeFeature)fresh).ExtrudeThroughPart=ex.ExtrudeThroughPart;
 // Position before recording the cross-section's world baseline.
 Set((IZSceneElement)fresh,Local(world,M((IZSceneElement)targetPart)));
 Bind((IZSceneElement)fresh,world,delta,part,"Wycięcie — "+label,true,root);
 return ((IZElement)fresh).Id;
}
static string SlotOffset(Dictionary<string,object> r,int i){string n=(string)r["count"],span=(string)r["spread"];return "("+i+" - ("+n+" - 1)/2)*"+span+"*2/("+n+" + ABS("+n+" - 2))";}
static void BuildRows(){
 foreach(var r in ((object[])Q["rows"]).Select(O)){
  string kind=(string)r["kind"],side=(string)r["side"],count=(string)r["count"];var slots=new List<object>();double half=0;
  Mark("row "+count);
  if(kind=="handle"){
   int source=Convert.ToInt32(r["source_mount"]),parent=Convert.ToInt32(r["source_parent"]);var original=U.GetElementById(source);var baseWorld=M((IZSceneElement)original);
   half=HalfWidth(original,1);var members=new List<IZElement>{original};for(int i=1;i<4;i++)members.Add(Copy(original));
   var center=(string)r["center"];var height=(string)r["height"];double centerBase=V(center);double heightBase=V(height);
   for(int i=0;i<4;i++){
    string label="Uchwyt H7159 — "+r["section"]+" — "+side+" — pozycja "+(i+1);var delta=Zero();
    if(side=="Prawa")delta[0]="RP_SzerokoscSkrzyni - "+F(N(Q["base"])[0])+" mm";
    delta[1]=center+" - "+F(centerBase)+" mm + "+SlotOffset(r,i);
    delta[2]=height+" - "+F(heightBase)+" mm";
    if((string)r["section"]=="Czapka")delta[2]+=" + RP_WysokoscDolu - "+F(N(Q["base"])[2])+" mm + RP_UniesienieCzapki - "+F(N(Q["base"])[4])+" mm";
    int root=members[i].Id;var ids=new List<int>{root};
    foreach(var cut in ((object[])r["cuts"]).Select(O))ids.Add(Cut(cut,baseWorld.Skip(12).Take(3).ToArray(),0,baseWorld.Skip(12).Take(3).ToArray(),delta,label,root));
    Bind((IZSceneElement)members[i],baseWorld,delta,parent,label,false,root);slots.Add(ids.ToArray());
   }
   var c=O(((object[])r["cuts"])[0]);((IZElement)FindFeature(Convert.ToInt32(c["source_part"]),Convert.ToInt32(r["remove_feature"]))).Remove();
  }else{
   for(int i=0;i<4;i++){
    var ids=new List<int>();
    foreach(var h in ((object[])r["halves"]).Select(O)){
     int source=Convert.ToInt32(h["source_mount"]),parent=Convert.ToInt32(h["source_parent"]);var original=U.GetElementById(source);var sourceWorld=M((IZSceneElement)original);var anchor=sourceWorld.Skip(12).Take(3).ToArray();
     half=Math.Max(half,HalfWidth(original,0));double angle=side=="Lewa"?-Math.PI/2:Math.PI/2;
     var target=new[]{side=="Lewa"?-2.032:-2.032+N(Q["base"])[0]/1000,(-1011.5+V((string)r["center"]))/1000,anchor[2]};
     var world=Rotate(sourceWorld,anchor,angle,target);var delta=Zero();
     if(side=="Prawa")delta[0]="RP_SzerokoscSkrzyni - "+F(N(Q["base"])[0])+" mm";
     delta[1]=(string)r["center"]+" - "+F(V((string)r["center"]))+" mm + "+SlotOffset(r,i);
     delta[2]="RP_WysokoscDolu - "+F(N(Q["base"])[2])+" mm";
     if((string)h["section"]=="Czapka")delta[2]+=" + RP_UniesienieCzapki - "+F(N(Q["base"])[4])+" mm";
     var fresh=Copy(original);int root=fresh.Id;ids.Add(root);
     string label="Zamek L905/915 — "+h["section"]+" — "+side+" — para "+(i+1);
     foreach(var cut in ((object[])h["cuts"]).Select(O))ids.Add(Cut(cut,anchor,angle,target,delta,label,root));
     Bind((IZSceneElement)fresh,world,delta,parent,label,false,root);
    }
    slots.Add(ids.ToArray());
   }
  }
  ManifestRows.Add(new{count=count,center=r["center"],spread=r["spread"],minimum=r["minimum"],half_width=half,clearance=12,slots=slots.ToArray()});
 }
}
static void Apply(){
 Controller.GetMethod("Apply").Invoke(null,new object[]{S});
 var targets=Bindings.Where(b=>b.cut).Select(b=>U.GetElementById(b.id).GetOwnerPart()).GroupBy(e=>e.Id).Select(g=>g.First());
 foreach(var e in targets){var p=(IZPart)e;p.Update();p.GetBody(true).GetBoundingBox();}
 S.Update();
}
static Dictionary<string,object> Check(string name){
 var errors=new List<object>();double poseMax=0,sizeMax=0;
 foreach(var b in Bindings){
  var e=U.GetElementById(b.id);if(e.GetStateStatus(eZElementState.Z_SUPPRESSED))continue;
  if(U.GetElementById(b.root).GetStateStatus(eZElementState.Z_SUPPRESSED))continue;
  var se=(IZSceneElement)e;var delta=Enumerable.Range(0,3).Select(k=>se.ParameterMgr.GetParameterByName("RP_QWorld"+"XYZ"[k]).Value).ToArray();
  var actual=M(b.cut?(IZSceneElement)((IZExtrudeFeature)e).CrossSection:se);double error=0;
  for(int k=0;k<3;k++)error=Math.Max(error,Math.Abs(actual[12+k]-b.world[12+k]-delta[k])*1000);
  for(int k=0;k<12;k++)error=Math.Max(error,Math.Abs(actual[k]-b.world[k])*1000);
  if(error>.08)errors.Add(new{id=b.id,pose_mm=error});poseMax=Math.Max(poseMax,error);
  if(b.cut){var p=((IZExtrudeFeature)e).CrossSection;var lengths=((Array)p.GetCurveIds()).Cast<object>().Select(x=>p.GetCurveLength(Convert.ToInt32(x))).OrderBy(x=>x).ToArray();if(lengths.Length!=b.lengths.Length||lengths.Zip(b.lengths,(a,c)=>Math.Abs(a-c)*1000).Max()>.01)errors.Add(new{cut=b.id,error="Contour changed"});}
  else foreach(var part in Parts(e)) {int id=((IZElement)part).Id;var bounds=N(part.GetBody(true).GetBoundingBox());var baseline=b.bodies[id];double err=Enumerable.Range(0,6).Max(k=>Math.Abs(bounds[k]-baseline[k])*1000);sizeMax=Math.Max(sizeMax,err);if(err>.08)errors.Add(new{part=id,size_mm=err});}
 }
 int activeHardware=0,activeCuts=0;
 foreach(var raw in ManifestRows){var r=O(J.DeserializeObject(J.Serialize(raw)));int n=(int)Math.Round(P((string)r["count"]).Value);var slots=(object[])r["slots"];
  for(int i=0;i<slots.Length;i++)foreach(object id in (object[])slots[i]){var e=U.GetElementById(Convert.ToInt32(id));bool suppressed=e.GetStateStatus(eZElementState.Z_SUPPRESSED);if(suppressed!=(i>=n))errors.Add(new{member=id,error="Quantity suppression mismatch"});if(!suppressed){if(e.Type==eZElementType.Z_ELEMENT_ASSEMBLY){
 activeHardware++;double center=V((string)r["center"]),span=V((string)r["spread"]);
 double expected=-1011.5+center+(n==1?0:(-0.5+(double)i/(n-1))*span);
 double actualY=M((IZSceneElement)e)[13]*1000;
 if(Math.Abs(actualY-expected)>.08)errors.Add(new{member=id,error="Independent row position",actual_mm=actualY,expected_mm=expected});
 }else activeCuts++;}}
 }
 return new Dictionary<string,object>{{"name",name},{"passed",errors.Count==0},{"pose_error_mm",poseMax},{"catalog_shape_error_mm",sizeMax},{"active_hardware_units",activeHardware},{"active_cuts",activeCuts},{"errors",errors}};
}
static void Picture(string path){var camera=(IZCamera)S.CameraMgr.ActiveCamera;camera.Perspective=false;camera.Direction=new double[]{.65,.85,-.5};camera.Up=new double[]{0,0,1};S.AdjustCameraToFitShapeInRect(1500,1100);S.Redraw();S.ExportImage(path,eZImageFormat.Z_IMAGE_PNG,1500,1100,true);}
public static int Run(string folder){var result=new Dictionary<string,object>();var checks=new List<object>();IZDoc owned=null;bool pass=false;Progress=Path.Combine(folder,"progress.txt");
 try{
  Q=O(J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));if((string)Q["contract"]!="rockpro-tv-counts-v1"||System.Diagnostics.Process.GetCurrentProcess().Id!=Convert.ToInt32(Q["expected_pid"]))throw new Exception("Wrong request/host");
  dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;if(!app.ApiVersion.StartsWith("29."))throw new Exception("2027 required");
  var before=((Array)app.GetAllOpenDocs()).Cast<object>().Select(D).Select(d=>new{path=d.Name,modified=d.Modified}).ToArray();
  string source=(string)Q["source"],output=(string)Q["output"];if(Hash(source)!=(string)Q["sha256"]||File.Exists(output))throw new Exception("Source changed/output exists");
  string working=Path.Combine(folder,"working.ics");File.Copy(source,working,false);bool already;owned=app.OpenFile2(working,false,true,out already);if(already){owned=null;throw new Exception("Owned copy already open");}
  S=(IZSceneDoc)owned;U=(IZSceneDocUtility)S;S.ConstraintSolver=false;Bindings=new List<Binding>();ManifestRows=new List<object>();Rows=((object[])Q["inventory"]).Select(O).ToDictionary(r=>Convert.ToInt32(r["id"]));
  Controller=Assembly.LoadFrom((string)Q["controller"]).GetType("RockPro.CAD.MountCountController");if(Hash(Controller.Assembly.Location)!=Hash((string)Q["controller"]))throw new Exception("Cached controller differs from requested build");Controller.GetField("Suspended").SetValue(null,true);
  foreach(var p in ((object[])Q["parameters"]).Select(O)){
   // Set heights only after capturing old geometry; their defaults are applied below.
   if(((string)p["name"]).EndsWith("_Wysokosc"))continue;
   Param(S.ParameterMgr,(string)p["name"],(string)p["expression"],(bool)p["scalar"],(string)p["notes"]);
  }
  BuildRows();Mark("members and exact source contours prepared");
  var manifest=new{contract="rockpro-tv-counts-v1",rows=ManifestRows.ToArray()};var props=S.GetTopElement().get_CustomPropMgr(false);props.AddCustomProp("RockPro.MountCounts.v1",J.Serialize(manifest),false);
  foreach(var p in ((object[])Q["parameters"]).Select(O).Where(p=>((string)p["name"]).EndsWith("_Wysokosc")))Param(S.ParameterMgr,(string)p["name"],(string)p["expression"],false,(string)p["notes"]);
  var defaults=Enumerable.Range(0,S.ParameterMgr.Count).Select(i=>S.ParameterMgr.GetParameter(i)).ToDictionary(p=>p.Name,p=>p.Expression);
  Action restore=()=>{foreach(var p in defaults)P(p.Key).Expression=p.Value;};
  Action<string> check=name=>{Mark("checking "+name);Apply();var c=Check(name);checks.Add(c);if(!(bool)c["passed"])throw new Exception("Check failed "+name);};
  check("po_dwa_na_bokach");Picture(Path.Combine(folder,"po_dwa.png"));
  foreach(var r in ((object[])Q["rows"]).Select(O))P((string)r["count"]).Expression=(string)r["kind"]=="handle"?"1":"0";
  check("po_jednym_bez_zamkow_bocznych");Picture(Path.Combine(folder,"po_jednym.png"));
  restore();P("RP_GlebokoscSkrzyni").Expression="972 mm";P("RP_WysokoscDolu").Expression=F(N(Q["base"])[2]+40)+" mm";P("RP_WysokoscCzapki").Expression=F(N(Q["base"])[3]+30)+" mm";
  foreach(var r in ((object[])Q["rows"]).Select(O))P((string)r["count"]).Expression=(string)r["side"]=="Lewa"?"3":"1";
  check("trzy_i_jeden_zmiana_gabarytow");Picture(Path.Combine(folder,"trzy_i_jeden.png"));
  restore();check("powrot_do_dwoch");Picture(Path.Combine(folder,"final.png"));S.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
  owned.Close2(true);owned=null;owned=app.OpenFile2(output,false,true,out already);if(already){owned=null;throw new Exception("Output already open");}S=(IZSceneDoc)owned;U=(IZSceneDocUtility)S;
  check("ponowne_otwarcie");foreach(var r in ((object[])Q["rows"]).Select(O))P((string)r["count"]).Expression="3";
  check("liczba_po_otwarciu");restore();check("finalny_powrot");Picture(Path.Combine(folder,"final.png"));S.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
  foreach(var old in before){var d=((Array)app.GetAllOpenDocs()).Cast<object>().Select(D).Single(x=>x.Name==old.path);if(d.Modified!=old.modified)throw new Exception("Preexisting document changed "+old.path);}
  if(Hash(source)!=(string)Q["sha256"])throw new Exception("Source changed");
  Controller.GetMethod("Start").Invoke(null,new object[]{app});Controller.GetField("Suspended").SetValue(null,false);
  result["source_unchanged"]=true;result["existing_documents_preserved"]=true;result["output"]=output;result["output_sha256"]=Hash(output);result["manifest"]=manifest;
  result["parameters"]=Enumerable.Range(0,S.ParameterMgr.Count).Select(i=>S.ParameterMgr.GetParameter(i)).Select(p=>new{name=p.Name,expression=p.Expression,value=p.Value,type=p.Type.ToString(),notes=p.Notes}).ToArray();
  pass=true;
 }catch(Exception e){result["error"]=e.ToString();if(owned!=null)try{S.SaveAs(Path.Combine(folder,"FAILED_DO_NOT_USE.ics"),eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);owned.Close2(true);}catch(Exception cleanup){result["cleanup_error"]=cleanup.ToString();}}
 result["bindings_count"]=Bindings==null?0:Bindings.Count;result["checks"]=checks;result["passed"]=pass;File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(result));return pass?0:1;
}
}}
