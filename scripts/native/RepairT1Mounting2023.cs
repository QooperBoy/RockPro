// Narrow in-memory repair of the measured T1 prototype. Never saves a document.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;

namespace RockPro { public static class LatchInProcess {
static JavaScriptSerializer Json=new JavaScriptSerializer{MaxJsonLength=64000000};
static IZSceneDoc Scene;
static Dictionary<string,object> Parameters;
static Dictionary<string,IZElement> Nodes=new Dictionary<string,IZElement>();
static Dictionary<string,object> Obj(object x){return (Dictionary<string,object>)x;}
static double[] Numbers(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
static string Expression(string s,int depth){foreach(string n in Parameters.Keys)s=System.Text.RegularExpressions.Regex.Replace(s,"\\b"+n+"\\b",m=>String.Concat(Enumerable.Repeat("Parent\\",depth))+"Params\\"+n);return s;}
static void Near(double actual,double expected,string message,double tol=.003){if(Double.IsNaN(actual)||Math.Abs(actual-expected)>tol)throw new Exception(message+": "+actual+" != "+expected);}
static void Parameter(IZParameterMgr mgr,string name,string expression,string notes){IZParameter p=null;for(int i=0;i<mgr.Count;i++){var candidate=mgr.GetParameter(i);if(candidate.Name==name)p=candidate;}if(p==null)p=mgr.CreateParameter(eZParamType.Z_PARAMETER_TYPE_LENGTH,name,0);p.Expression=expression;p.Notes=notes;}
static void Values(Dictionary<string,object> values){foreach(var kv in values)Scene.ParameterMgr.GetParameterByName(kv.Key).Expression=Convert.ToDouble(kv.Value).ToString(System.Globalization.CultureInfo.InvariantCulture)+" mm";}
static void Update(){((IZAssembly)Scene.GetTopElement()).RegenerateParts(true);Scene.Update();}
static void Pose(IZSceneElement e,Dictionary<string,object> s,int depth){
 var anchor=e.GetAnchorTransform();anchor.MakeIdentity();e.SetAnchorTransform(anchor);
 var m=e.GetTransformToParent();m.MakeIdentity();var rows=(object[])s["rotation"];var initial=Numbers(s["initial"]);
 for(int i=0;i<3;i++){for(int j=0;j<3;j++)m.SetValue(i,j,Convert.ToDouble(((object[])rows[i])[j]));m.SetValue(3,i,initial[i]/1000);}e.SetTransformToParent(m);
 // Local parameters explicitly initialize the native assembly parameter context.
 // Bare local names are the documented SDK binding pattern; verify readback.
 var positions=(object[])s["position"];var mgr=e.ParameterMgr;
 for(int axis=0;axis<3;axis++)Parameter(mgr,"RP_Polozenie"+"XYZ"[axis],Expression((string)positions[axis],depth),"Wyliczone położenie montażowe; sterowane parametrami sceny. Nie zmieniać ręcznie.");
 e.ForceSetupParameterExpression();
 for(int axis=0;axis<3;axis++){string name="RP_Polozenie"+"XYZ"[axis];e.set_PositionTransformComponentExpression((eZTransformComponentType)axis,name);if(String.IsNullOrEmpty(e.get_PositionTransformComponentExpression((eZTransformComponentType)axis)))throw new Exception("Position expression not accepted: "+name);}
}
static IZFeature FirstFeature(IZElement e){return ((IZPartFeatureMgr)e).GetFeatureAt(0);}
static void Dimensions(IZFeature f,Dictionary<string,object> s){var box=(IZSizeBox)f;if(s.ContainsKey("dimensions")){var a=(object[])s["dimensions"];box.LengthExpression=Expression((string)a[0],2);box.WidthExpression=Expression((string)a[1],2);box.HeightExpression=Expression((string)a[2],2);}else if(s.ContainsKey("length"))box.HeightExpression=Expression((string)s["length"],2);((IZSceneElement)f).ForceSetupParameterExpression();}
static IZFeature AddCut(Dictionary<string,object> cut){
 var part=(IZPart)Nodes[(string)cut["target"]];var fm=(IZPartFeatureMgr)part;string name="RockPro | Przerwa profilu przy zawiasie | "+cut["key"];
 for(int i=fm.GetFeaturesCount()-1;i>=0;i--)if(((IZElement)fm.GetFeatureAt(i)).Name==name){if(fm.GetFeatureAt(i).OperationType!=eZOperationType.Z_SUBTRACT)throw new Exception("Unexpected existing cut");((IZElement)fm.GetFeatureAt(i)).Remove();}
 var dims=Numbers(cut["dimensions_initial"]);var pr=Scene.CreateProfile();double[][] pts={new[]{0.0,0.0},new[]{dims[0]/1000,0.0},new[]{dims[0]/1000,dims[1]/1000},new[]{0.0,dims[1]/1000}};
 for(int i=0;i<4;i++)pr.CreateLine(pts[i],pts[(i+1)%4],i+1);
 // Initialize the cutter in an identity part before copying into a rotated profile.
 // SizeBox.Reset on an unregenerated negative feature used stale/default extents.
 var temporary=Scene.CreatePart();try{
 var seed=(IZFeature)((IZPartFeatureMgr)temporary).CreateExtrudeFeature(eZOperationType.Z_UNITE,false,dims[2]/1000,0,0,pr,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB);
 temporary.Update();((IZSizeBox)seed).Reset(false);
 var f=seed.CopyFeatureTo(part);f.OperationType=eZOperationType.Z_SUBTRACT;((IZElement)f).Name=name;
 Pose((IZSceneElement)f,cut,2);part.Regenerate();part.Update();Dimensions(f,cut);return f;
 }finally{((IZElement)temporary).Remove();}
}
static double[] Point(IZElement node,double[] local){var m=((IZSceneElement)node).GetTransformToGlobal();return Enumerable.Range(0,3).Select(j=>m.GetValue(3,j)*1000+Enumerable.Range(0,3).Sum(k=>local[k]*m.GetValue(k,j))).ToArray();}
static double[] Bounds(IZElement node){var b=Numbers(((IZPart)node).GetBody(true).GetBoundingBox());var points=new List<double[]>();for(int mask=0;mask<8;mask++)points.Add(Point(node,Enumerable.Range(0,3).Select(j=>b[j+(((mask>>j)&1)==1?3:0)]*1000).ToArray()));return Enumerable.Range(0,3).Select(j=>points.Min(p=>p[j])).Concat(Enumerable.Range(0,3).Select(j=>points.Max(p=>p[j]))).ToArray();}
static void Plane(IZElement node,int id,int axis,double expected,int normal){var body=((IZPart)node).GetBody(true);var faces=(IZBodyFace)body;bool rev;ZMathPoint p;ZMathVector n;faces.GetPlaneData(id,out rev,out p,out n);var vertices=(IZBodyVertex)body;foreach(object v in (Array)faces.GetFaceVertexIds(id))Near(Point(node,Numbers(vertices.GetPosition(Convert.ToInt32(v))).Select(x=>x*1000).ToArray())[axis],expected,"Mounting plane "+node.Name);var m=((IZSceneElement)node).GetTransformToGlobal();double[] nn={n.X,n.Y,n.Z};Near(Enumerable.Range(0,3).Sum(k=>nn[k]*m.GetValue(k,axis))*(rev?-1:1),normal,"Mounting normal");}
static object Check(Dictionary<string,object> c){
 Values(Obj(c["parameters"]));Update();var p=Obj(c["parameters"]);Func<string,double> val=n=>Convert.ToDouble(p[n]);
 foreach(object item in (object[])c["checks"]){var x=Obj(item);var node=Nodes[(string)x["key"]];var m=((IZSceneElement)node).GetTransformToParent();var expected=Numbers(x["position"]);var r=(object[])x["rotation"];
  for(int j=0;j<3;j++){Near(m.GetValue(3,j)*1000,expected[j],"Position "+x["key"]+" axis "+j);for(int k=0;k<3;k++)Near(m.GetValue(k,j),Convert.ToDouble(((object[])r[k])[j]),"Rotation "+x["key"]);}
  if(x.ContainsKey("dimensions")){var b=Numbers(((IZPart)node).GetBody(true).GetBoundingBox());var d=Numbers(x["dimensions"]);for(int j=0;j<3;j++)Near((b[j+3]-b[j])*1000,d[j],"Dimension "+x["key"]);}
 }
 double height=val("RP_WysokoscKorpusu")+val("RP_WysokoscPokrywy")+val("RP_RozsunieciePokrywy");
 foreach(var kv in Nodes){if(kv.Key.StartsWith("socket/"))Plane(kv.Value,44,2,height,-1);
  if(kv.Key.StartsWith("corner/")){string code=kv.Key.Split('/')[1];bool[] high={code[1]=='1',code[2]=='1',code[0]=='1'};double[] size={val("RP_Dlugosc"),val("RP_Glebokosc"),height};int[] faces={17,51,34};var m=((IZSceneElement)kv.Value).GetTransformToParent();for(int k=0;k<3;k++){int j=Enumerable.Range(0,3).First(a=>Math.Abs(m.GetValue(k,a))>.9);Plane(kv.Value,faces[k],j,high[j]?size[j]:0,high[j]?-1:1);}}
 }
 var front=Bounds(Nodes["profile/bottom/front"]);var rear=Bounds(Nodes["profile/bottom/rear"]);
 foreach(string side in new[]{"left","right"}){var pad=Bounds(Nodes["support/"+side]);Near(pad[1]-front[4],val("RP_LuzMontazowy"),"Front pad clearance");Near(rear[1]-pad[4],val("RP_LuzMontazowy"),"Rear pad clearance");}
 for(int slot=1;slot<=2;slot++)foreach(string half in new[]{"base","lid"}){var profile=(IZPart)Nodes["profile/"+(half=="base"?"EG-0500_1":"EG-0500_2")+"/rear"];if(profile.HasInterference(Nodes["hinge/"+slot+"/"+half]))throw new Exception("Hinge/profile interference");}
 return new{name=c["name"],parts_checked=Nodes.Count,corner_mount_planes=24,socket_mount_planes=4,pad_clearances=4,hinge_collision_pairs=4,passed=true};
}
public static int Run(string folder){var result=new Dictionary<string,object>();bool changed=false;try{
 var req=Obj(Json.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));if((string)req["contract"]!="rockpro-t1-mounting-repair-v1")throw new Exception("Wrong repair contract");
 dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;if(!app.ApiVersion.StartsWith("25."))throw new Exception("Wrong host");var doc=app.ActiveDoc;if(doc.Name!=(string)req["document"]||doc.FileGUID!=(string)req["guid"])throw new Exception("Wrong target document");
 Scene=(IZSceneDoc)doc;Parameters=Obj(req["parameters"]);var top=(IZAssembly)Scene.GetTopElement();var all=top.GetChildrenZArray();var expected=Obj(req["expected_names"]);if(top.GetChildrenCount()!=expected.Count)throw new Exception("Unexpected scene contents");var byId=new Dictionary<int,IZElement>();for(int i=0;i<top.GetChildrenCount();i++){object raw;all.Get(i,out raw);var e=(IZElement)raw;if(!expected.ContainsKey(e.Id.ToString())||e.Name!=(string)expected[e.Id.ToString()])throw new Exception("Scene edited since inspection");byId[e.Id]=e;}
 foreach(var kv in Parameters)Parameter(Scene.ParameterMgr,kv.Key,Convert.ToDouble(kv.Value).ToString(System.Globalization.CultureInfo.InvariantCulture)+" mm",(string)Obj(req["notes"])[kv.Key]);changed=true;
 foreach(object item in (object[])req["parts"]){var s=Obj(item);var e=byId[Convert.ToInt32(s["id"])];Nodes[(string)s["key"]]=e;Pose((IZSceneElement)e,s,1);if(s.ContainsKey("dimensions")||s.ContainsKey("length"))Dimensions(FirstFeature(e),s);}
 foreach(object item in (object[])req["cuts"]){var c=Obj(item);var fm=(IZPartFeatureMgr)Nodes[(string)c["target"]];IZFeature found=null;for(int i=0;i<fm.GetFeaturesCount();i++)if(((IZElement)fm.GetFeatureAt(i)).Name=="RockPro wyciecie / "+c["key"])found=fm.GetFeatureAt(i);if(found==null)throw new Exception("Missing original machining");Pose((IZSceneElement)found,c,2);}
 foreach(object item in (object[])req["new_cuts"])AddCut(Obj(item));
 var checks=new List<object>();try{foreach(object item in (object[])req["check_cases"]){checks.Add(Check(Obj(item)));File.WriteAllText(Path.Combine(folder,"progress.json"),Json.Serialize(checks));}}finally{Values(Parameters);Update();}
 // Only remove old names after all new expressions have survived resize/restore.
 foreach(string old in (object[])req["old_parameters"]) {var param=Scene.ParameterMgr.GetParameterByName(old);if(param!=null)Scene.ParameterMgr.DeleteParam(param);}
 foreach(object item in (object[])req["parts"]){var s=Obj(item);Nodes[(string)s["key"]].Name=(string)s["label"];}
 Update();checks.Add(Check(Obj(((object[])req["check_cases"])[2])));
 foreach(var e in Nodes.Values)e.SetDirtyFlag(eZDirtyFlag.Z_DIRTY_GRAPHICS);Scene.UpdateGraphics(0);Scene.Redraw();result["checks"]=checks;result["passed"]=true;result["document"]=doc.Name;result["unsaved"]=doc.Modified;
 }catch(Exception e){result["passed"]=false;result["error"]=e.ToString();if(changed){try{Values(Parameters);Update();Scene.UpdateGraphics(0);Scene.Redraw();}catch(Exception restore){result["restore_error"]=restore.ToString();}}}
 File.WriteAllText(Path.Combine(folder,"result.json"),Json.Serialize(result));return result.ContainsKey("passed")&&(bool)result["passed"]?0:1;
}
}}
