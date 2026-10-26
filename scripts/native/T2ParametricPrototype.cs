// Experimental, source-pinned T2 prototype. Uses the existing in-process runner.
// Never saves CAD: the final working copy is intentionally left modified/open.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;

namespace RockPro { public static class LatchInProcess {
static readonly JavaScriptSerializer Json=new JavaScriptSerializer{MaxJsonLength=64000000};
const string SourceHash="e7dccb157f58ffec249c4634896b71b831b6228354afd688f37ba83f50cb75cb";
static IZSceneDoc Scene;
static IZSceneDocUtility Utility;
static Dictionary<string,object> Parameters;
static Dictionary<int,double[]> BindingOffsets=new Dictionary<int,double[]>();
static Dictionary<int,int> CatalogFaces=new Dictionary<int,int>();
static Dictionary<int,IZElement> Elements=new Dictionary<int,IZElement>();
static Dictionary<string,object> Obj(object x){return (Dictionary<string,object>)x;}
static double[] N(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
static string Hash(string path){using(var stream=File.OpenRead(path))using(var sha=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
static void Near(double a,double b,string message,double tolerance=.005){if(Double.IsNaN(a)||Math.Abs(a-b)>tolerance)throw new Exception(message+": "+a+" != "+b);}
static string Expr(string text,int depth){foreach(string name in Parameters.Keys)text=System.Text.RegularExpressions.Regex.Replace(text,"\\b"+name+"\\b",m=>String.Concat(Enumerable.Repeat("Parent\\",depth))+"Params\\"+name);return text;}
static void SetParameter(IZParameterMgr mgr,string name,string expression,string notes){
 IZParameter p=null;for(int i=0;i<mgr.Count;i++){var x=mgr.GetParameter(i);if(x.Name==name)p=x;}
 if(p==null)p=mgr.CreateParameter(eZParamType.Z_PARAMETER_TYPE_LENGTH,name,0);
 p.Expression=expression;p.Notes=notes;
}
static void Bind(IZSceneElement element,Dictionary<string,object> spec,int depth){
 bool preserve=spec.ContainsKey("operation")&&!(bool)spec["scalable"];
 element.AnchorBehavior=(eZAnchorBehavior)0;
 if(!preserve){var anchor=element.GetAnchorTransform();anchor.MakeIdentity();element.SetAnchorTransform(anchor);}
 var source=(object[])spec["parent_matrix"];var m=element.GetTransformToParent();
 for(int i=0;i<4;i++)for(int j=0;j<4;j++)m.SetValue(i,j,Convert.ToDouble(((object[])source[i])[j])*(i==3&&j<3?.001:1));
 element.SetTransformToParent(m);
 var positions=(object[])spec["position"];
 if(preserve){var position=element.GetPositionTransform();var geometry=element.GetTransformToParent();var offset=Enumerable.Range(0,3).Select(j=>(position.GetValue(3,j)-geometry.GetValue(3,j))*1000).ToArray();BindingOffsets[((IZElement)element).Id]=offset;positions=Enumerable.Range(0,3).Select(j=>(object)("("+(string)positions[j]+") + ("+offset[j].ToString("G17",System.Globalization.CultureInfo.InvariantCulture)+" mm)")).ToArray();}
 for(int j=0;j<3;j++)SetParameter(element.ParameterMgr,"RP_Pozycja"+"XYZ"[j],Expr((string)positions[j],depth),"Pozycja wyliczona z parametrów T2. Nie zmieniać ręcznie; zachowuje orientację części wzorca.");
 element.ForceSetupParameterExpression();
 for(int j=0;j<3;j++){
  string name="RP_Pozycja"+"XYZ"[j];element.set_PositionTransformComponentExpression((eZTransformComponentType)j,name);
  if(String.IsNullOrEmpty(element.get_PositionTransformComponentExpression((eZTransformComponentType)j)))throw new Exception("Binding refused: "+name+" element="+((IZElement)element).Id+" name="+((IZElement)element).Name+" depth="+depth+" parameters="+element.ParameterMgr.Count+" local="+element.ParameterMgr.GetParameterByName(name).Expression+" anchor="+element.AnchorBehavior+" expression="+Expr((string)positions[j],depth));
 }
}
static void Values(Dictionary<string,object> values){foreach(var kv in values)Scene.ParameterMgr.GetParameterByName(kv.Key).Expression=Convert.ToDouble(kv.Value).ToString(System.Globalization.CultureInfo.InvariantCulture)+" mm";}
static void Update(){((IZAssembly)Scene.GetTopElement()).RegenerateParts(true);Scene.Update();}
static int Walk(IZElement e){Elements[e.Id]=e;int count=1;var array=e.GetChildrenZArray();for(int i=0;i<e.GetChildrenCount();i++){object raw;array.Get(i,out raw);var c=(IZElement)raw;if(c.Type==eZElementType.Z_ELEMENT_PART||c.Type==eZElementType.Z_ELEMENT_ASSEMBLY)count+=Walk(c);}return count;}
static void Position(IZSceneElement e,double[] expected,string label,bool world){var m=world?e.GetTransformToGlobal():e.GetPositionTransform();for(int j=0;j<3;j++)Near(m.GetValue(3,j)*1000,expected[j],label+" axis "+j);}
static void Rotation(IZSceneElement e,object raw,string label){var m=e.GetTransformToGlobal();var rows=(object[])raw;for(int i=0;i<3;i++)for(int j=0;j<3;j++)Near(m.GetValue(i,j),Convert.ToDouble(((object[])rows[i])[j]),label,.000001);}
static object Check(Dictionary<string,object> test,Dictionary<string,object> req){
 Values(Obj(test["parameters"]));Update();
 foreach(object item in (object[])test["nodes"]){var row=Obj(item);Position((IZSceneElement)Elements[Convert.ToInt32(row["id"])],N(row["world_position_mm"]),"Node "+row["id"],true);}
 foreach(object item in (object[])test["features"]){var row=Obj(item);var f=(IZFeature)Utility.GetElementById(Convert.ToInt32(row["id"]));var expected=N(row["position_mm"]);double[] offset;if(BindingOffsets.TryGetValue(Convert.ToInt32(row["id"]),out offset))for(int j=0;j<3;j++)expected[j]+=offset[j];Position((IZSceneElement)f,expected,"Feature "+row["id"],false);
  if(row.ContainsKey("bounds_mm")){var wanted=N(row["bounds_mm"]);var actual=N(f.GetBoundingBox());for(int j=0;j<6;j++)Near(actual[j]*1000,wanted[j],"Feature dimensions "+row["id"]+" axis "+j+" HExpr="+((IZSizeBox)f).HeightExpression+" H="+((IZSizeBox)f).Height,.02);}
 }
 var measurements=((object[])req["measurements"]).Select(Obj).ToDictionary(x=>Convert.ToInt32(x["id"]));
 bool baseline=(string)test["name"]=="wzorzec"||(string)test["name"]=="powrot";
 foreach(object item in (object[])test["parts"]){var row=Obj(item);int id=Convert.ToInt32(row["id"]);var e=Elements[id];Position((IZSceneElement)e,N(row["world_position_mm"]),"Part "+id,true);var original=measurements[id];Rotation((IZSceneElement)e,original["world_matrix"],"Part rotation "+id);
  if(original["opaque_root"]!=null)Near(((Array)((IZPart)e).GetBody(true).GetFaceIds()).Length,CatalogFaces[id],"Catalog face count "+id,0);
  if(baseline||original["opaque_root"]!=null){var actual=N(((IZPart)e).GetBody(true).GetBoundingBox());var wanted=N(original["bounds_local_m"]);for(int j=0;j<6;j++)Near(actual[j]*1000,wanted[j]*1000,"Catalog/baseline geometry "+id+" axis "+j,.02);}
 }
 var values=Obj(test["parameters"]);bool closed=new[]{"RP_UniesienieCzapki","RP_OdsuniecieKlapy","RP_UniesienieRacka"}.All(n=>Convert.ToDouble(values[n])==0);
 if(closed)foreach(object item in (object[])req["latch_pairs"]){var pair=Obj(item);var a=((IZSceneElement)Elements[Convert.ToInt32(pair["upper_source_id"])]).GetTransformToGlobal();var b=((IZSceneElement)Elements[Convert.ToInt32(pair["lower_source_id"])]).GetTransformToGlobal();for(int j=0;j<3;j++)Near(a.GetValue(3,j)*1000,b.GetValue(3,j)*1000,"Latch pair alignment");}
 return new{name=test["name"],nodes=((object[])test["nodes"]).Length,features=((object[])test["features"]).Length,parts=measurements.Count,rigid_catalog_geometry=true,closed_latch_pairs_checked=closed?6:0,passed=true};
}
static void Dirty(IZElement e){
 // Graphics invalidation only: Part.Update/Assembly.Update force a rebuild of
 // opaque catalog histories and can invalidate their historical fillet edges.
 var children=e.GetChildrenZArray();for(int i=0;i<e.GetChildrenCount();i++){object raw;children.Get(i,out raw);var child=(IZElement)raw;if(child.Type==eZElementType.Z_ELEMENT_PART||child.Type==eZElementType.Z_ELEMENT_ASSEMBLY)Dirty(child);}
 e.SetDirtyFlag(eZDirtyFlag.Z_DIRTY_GRAPHICS);
}
public static int Run(string folder){var result=new Dictionary<string,object>();IZDoc doc=null;IZBaseApp app=null;bool passed=false;try{
 var req=Obj(Json.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));
 if((string)req["contract"]!="rockpro-t2-parametric-prototype-v1"||(string)req["source_sha256"]!=SourceHash)throw new Exception("Unsupported T2 recipe");
 if(Convert.ToInt32(req["expected_pid"])!=System.Diagnostics.Process.GetCurrentProcess().Id)throw new Exception("Wrong process");
 string source=Path.GetFullPath((string)req["source"]);if(Hash(source)!=SourceHash)throw new Exception("T2 source revision changed");
 dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");app=(IZBaseApp)legacy.ZIronCADApp;if(!app.ApiVersion.StartsWith("25."))throw new Exception("Expected IronCAD 2023");
 string copy=Path.Combine(folder,"RockPro_T2_parametryczny_IC2023.ics");File.Copy(source,copy,false);bool already;doc=app.OpenFile2(copy,false,true,out already);if(already)throw new Exception("Owned copy already open");
 Scene=(IZSceneDoc)doc;Utility=(IZSceneDocUtility)doc;Parameters=Obj(req["parameters"]);Elements.Clear();BindingOffsets.Clear();CatalogFaces.Clear();int count=Walk(Scene.GetTopElement());if(count!=449)throw new Exception("T2 source hierarchy mismatch");
 foreach(object item in (object[])req["nodes"]){var spec=Obj(item);var e=Elements[Convert.ToInt32(spec["id"])];if(e.Name!=(string)spec["name"]||e.Type.ToString()!=(string)spec["type"])throw new Exception("T2 source identity mismatch");}
 foreach(object item in (object[])req["measurements"]){var r=Obj(item);if(r["opaque_root"]!=null){int id=Convert.ToInt32(r["id"]);CatalogFaces[id]=((Array)((IZPart)Elements[id]).GetBody(true).GetFaceIds()).Length;}}
 foreach(var kv in Parameters)SetParameter(Scene.ParameterMgr,kv.Key,Convert.ToDouble(kv.Value).ToString(System.Globalization.CultureInfo.InvariantCulture)+" mm",(string)Obj(req["notes"])[kv.Key]);
 var wrapped=new HashSet<int>();
 foreach(object item in (object[])req["nodes"]){var spec=Obj(item);var node=Elements[Convert.ToInt32(spec["id"])];int depth=((string)spec["path"]).Split('/').Length-1;
  if(node.Type==eZElementType.Z_ELEMENT_PART&&!(bool)spec["opaque"]){
   var part=(IZPart)node;bool linked;part.HasInternalLinks(out linked);if(linked)part.Unlink();
   var original=((IZSceneElement)node).GetTransformToParent();
   var parent=(IZAssembly)node.GetParent();var wrapper=parent.CreateSubAssembly();((IZElement)wrapper).Name=spec.ContainsKey("label")?(string)spec["label"]:"RockPro T2 | Pozycja części "+node.Id;
   var identity=((IZSceneElement)wrapper).GetTransformToParent();identity.MakeIdentity();((IZSceneElement)wrapper).SetTransformToParent(identity);wrapper.MoveChild(node,false);((IZSceneElement)node).SetTransformToParent(original);
   var ws=new Dictionary<string,object>(spec);ws["parent_matrix"]=new object[]{new object[]{1,0,0,0},new object[]{0,1,0,0},new object[]{0,0,1,0},new object[]{0,0,0,1}};
   var positions=(object[])spec["position"];var oldMatrix=(object[])spec["parent_matrix"];
   ws["position"]=Enumerable.Range(0,3).Select(j=>(object)("("+(string)positions[j]+") - ("+Convert.ToDouble(((object[])oldMatrix[3])[j]).ToString("G17",System.Globalization.CultureInfo.InvariantCulture)+" mm)")).ToArray();
   Bind((IZSceneElement)wrapper,ws,depth);wrapped.Add(node.Id);
  }else Bind((IZSceneElement)node,spec,depth);
 }
 foreach(object item in (object[])req["features"]){var spec=Obj(item);var f=(IZFeature)Utility.GetElementById(Convert.ToInt32(spec["id"]));var part=Elements[Convert.ToInt32(spec["part_id"])];int depth=((object[])req["nodes"]).Select(Obj).Where(n=>Convert.ToInt32(n["id"])==part.Id).Select(n=>((string)n["path"]).Split('/').Length).Single();if(wrapped.Contains(part.Id))depth++;
  if((bool)spec["scalable"]){var box=(IZSizeBox)f;((IZPart)part).Update();box.Reset(false);box.KeepAnchorFixedInSpace=true;box.LengthResizeBehavior=eZResizeBehaviorType.Z_RESIZE_ABOUT_ANCHOR;box.WidthResizeBehavior=eZResizeBehaviorType.Z_RESIZE_ABOUT_ANCHOR;box.HeightResizeBehavior=eZResizeBehaviorType.Z_RESIZE_ABOUT_ANCHOR;}
  Bind((IZSceneElement)f,spec,depth);
  if((bool)spec["scalable"]){var dims=(object[])spec["dimensions"];var se=(IZSceneElement)f;var box=(IZSizeBox)f;
   for(int j=0;j<3;j++)SetParameter(se.ParameterMgr,"RP_Rozmiar"+"XYZ"[j],Expr((string)dims[j],depth),"Wyliczony rozmiar formatki lub długość profilu. Sterowany wymiarami sceny T2.");
   var existing=new HashSet<string>(Enumerable.Range(0,se.ParameterMgr.Count).Select(i=>se.ParameterMgr.GetParameter(i).Name));
   if(existing.Contains("S")&&existing.Contains("H")&&existing.Contains("L")){
    SetParameter(se.ParameterMgr,"S","RP_RozmiarX","Grubość formatki; wyliczona z danych wariantu T2.");
    SetParameter(se.ParameterMgr,"H","RP_RozmiarY","Drugi wymiar formatki; sterowany polskimi parametrami sceny T2.");
    SetParameter(se.ParameterMgr,"L","RP_RozmiarZ","Długość formatki; sterowana polskimi parametrami sceny T2.");
    box.LengthExpression="S";box.WidthExpression="H";box.HeightExpression="L";
   }else{box.LengthExpression="RP_RozmiarX";box.WidthExpression="RP_RozmiarY";box.HeightExpression="RP_RozmiarZ";}
   se.ForceSetupParameterExpression();
   if(String.IsNullOrEmpty(box.HeightExpression))throw new Exception("Size expression refused: "+((IZElement)f).Id);
  }
 }
 File.WriteAllText(Path.Combine(folder,"binding-complete.json"),Json.Serialize(new{nodes=((object[])req["nodes"]).Length,features=((object[])req["features"]).Length}));
 var checks=new List<object>();try{foreach(object item in (object[])req["checks"]){checks.Add(Check(Obj(item),req));File.WriteAllText(Path.Combine(folder,"progress.json"),Json.Serialize(checks));}}finally{Values(Parameters);Update();}
 foreach(object item in (object[])req["nodes"]){var spec=Obj(item);if(spec.ContainsKey("label"))Elements[Convert.ToInt32(spec["id"])].Name=(string)spec["label"];if((string)spec["role"]=="outer_panel")((IZPart)Elements[Convert.ToInt32(spec["id"])]).SurfaceFinish.Color=0x808040;}
 Elements[4499].Name="RockPro T2 | Spód";Elements[7036].Name="RockPro T2 | Zdejmowana czapka";Elements[4601].Name="RockPro T2 | Zdejmowana klapa przednia";Elements[6366].Name="RockPro T2 | Niezależny rack";
 File.WriteAllText(Path.Combine(folder,"display-stage.json"),"{\"stage\":\"before_graphics_invalidation\"}");
 Dirty(Scene.GetTopElement());app.ActiveDoc=doc;
 File.WriteAllText(Path.Combine(folder,"display-stage.json"),"{\"stage\":\"before_graphics_update\"}");
 Scene.UpdateGraphics(0);Scene.AdjustCameraToFitShapeInRect(1280,800);Scene.Redraw();
 foreach(var pair in CatalogFaces)Near(((Array)((IZPart)Elements[pair.Key]).GetBody(true).GetFaceIds()).Length,pair.Value,"Catalog after graphics "+pair.Key,0);
 File.WriteAllText(Path.Combine(folder,"display-stage.json"),"{\"stage\":\"graphics_and_catalog_topology_passed\"}");
 result["catalog_parts_topology_checked"]=CatalogFaces.Count;
 if(Hash(source)!=SourceHash||Hash(copy)!=SourceHash)throw new Exception("Unexpected disk modification");
 result["checks"]=checks;result["document"]=doc.Name;result["modified"]=doc.Modified;result["saved"]=false;result["source_unchanged"]=true;result["production_approved"]=false;passed=true;
 }catch(Exception e){result["error"]=e.ToString();}
 finally{if(!passed&&doc!=null){try{doc.Close();result["failed_copy_closed"]=true;}catch(Exception e){result["cleanup_error"]=e.ToString();}}result["passed"]=passed;File.WriteAllText(Path.Combine(folder,"result.json"),Json.Serialize(result));}
 return passed?0:1;
}
}}
