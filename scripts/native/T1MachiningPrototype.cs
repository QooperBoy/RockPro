using System;
using System.IO;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;
namespace RockPro { public static class LatchInProcess {
static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=64000000};
static IZBaseApp App; static string Folder;
static bool Presentation=false;
static List<IZDoc> Owned=new List<IZDoc>();
static Dictionary<string,object> O(object a){return (Dictionary<string,object>)a;}
static string Hash(string p){using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
static void Write(string name,object data){File.WriteAllText(Path.Combine(Folder,name),J.Serialize(data));}
static double[] Numbers(object a){Array v=(Array)a;double[] b=new double[v.Length];for(int i=0;i<v.Length;i++)b[i]=Convert.ToDouble(v.GetValue(i));return b;}
static double[][] Matrix(IZSceneElement e,bool world){IZMathMatrix m=world?e.GetTransformToGlobal():e.GetTransformToParent();var a=new double[4][];for(int i=0;i<4;i++){a[i]=new double[4];for(int k=0;k<4;k++)a[i][k]=m.GetValue(i,k)*(i==3&&k<3?1000:1);}return a;}
static List<IZElement> Children(IZElement e){var a=new List<IZElement>();int n=e.GetChildrenCount();if(n>0){IZArray ar=e.GetChildrenZArray();for(int i=0;i<n;i++){object o;ar.Get(i,out o);a.Add((IZElement)o);}}return a;}
static object Curves(IZProfile p){var result=new List<object>();foreach(var id0 in (Array)p.GetCurveIds()){int id=Convert.ToInt32(id0);string kind=p.GetCurveType(id).ToString();var r=new Dictionary<string,object>{{"id",id},{"type",kind}};try{object a,b;double radius,start,end;
if(kind.Contains("LINE")&&!kind.Contains("SPLINE")){p.GetLineData(id,out a,out b);r["start"]=Numbers(a);r["end"]=Numbers(b);}
else if(kind.Contains("ARC")&&!kind.Contains("ELLIP")){p.GetArcData(id,out a,out radius,out start,out end);r["center"]=Numbers(a);r["radius"]=radius;r["start_angle"]=start;r["end_angle"]=end;}
else if(kind.Contains("CIRCLE")){p.GetCircleData(id,out a,out radius);r["center"]=Numbers(a);r["radius"]=radius;}
}catch(Exception ex){r["error"]=ex.Message;}result.Add(r);}return result;}
static void Walk(IZElement e,string path,List<object> rows){var r=new Dictionary<string,object>{{"id",e.Id},{"name",e.Name},{"type",e.Type.ToString()},{"path",path}};try{r["world_mm"]=Matrix((IZSceneElement)e,true);r["parent_mm"]=Matrix((IZSceneElement)e,false);}catch{}
try{var p=(IZPart)e;r["bounds_local_m"]=Numbers(p.GetBody(true).GetBoundingBox());var fm=(IZPartFeatureMgr)e;var fs=new List<object>();for(int i=0;i<fm.GetFeaturesCount();i++){var f=fm.GetFeatureAt(i);var fe=(IZElement)f;var fr=new Dictionary<string,object>{{"id",fe.Id},{"name",fe.Name},{"type",f.Type.ToString()},{"operation",f.OperationType.ToString()}};try{fr["parent_mm"]=Matrix((IZSceneElement)f,false);fr["world_mm"]=Matrix((IZSceneElement)f,true);fr["bbox_m"]=Numbers(f.GetBoundingBox());}catch{}
try{var ex=(IZExtrudeFeature)f;var p2=ex.CrossSection;fr["forward"]=ex.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_FORWARD);fr["backward"]=ex.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_BACKWARD);fr["curves"]=Curves(p2);try{fr["profile_parent_mm"]=Matrix((IZSceneElement)p2,false);}catch{}}catch{}fs.Add(fr);}r["features"]=fs;}
catch{}
rows.Add(r);foreach(var c in Children(e))if(c.Type==eZElementType.Z_ELEMENT_PART||c.Type==eZElementType.Z_ELEMENT_ASSEMBLY)Walk(c,path+"/"+c.Id,rows);}
static object State(){var d=App.ActiveDoc;return new{path=d==null?null:d.Name,guid=d==null?null:d.FileGUID,modified=d!=null&&d.Modified};}
static object Inspect(Dictionary<string,object> request){string source=Path.GetFullPath((string)request["source"]);if(Hash(source)!=(string)request["source_sha256"])throw new Exception("Source hash mismatch");string copy=Path.Combine(Folder,"source_copy.ics");File.Copy(source,copy,false);bool already;var doc=App.OpenFile2(copy,false,false,out already);if(already)throw new Exception("Copy already open; ownership refused");Owned.Add(doc);var rows=new List<object>();Walk(((IZSceneDoc)doc).GetTopElement(),"root",rows);Write("inventory.json",new{source=source,source_sha256=Hash(source),copy_path=copy,rows=rows});return new{rows=rows.Count,original_unchanged=Hash(source)==(string)request["source_sha256"]};}
static IZSceneDoc OpenCopy(Dictionary<string,object> request,string prefix) {
 string source=Path.GetFullPath((string)request[prefix]);
 if(Hash(source)!=(string)request[prefix+"_sha256"])throw new Exception("Pinned source changed");
 string copy=Path.Combine(Folder,prefix+"_working.ics"); File.Copy(source,copy,false);
 bool already;var doc=App.OpenFile2(copy,false,false,out already);
 if(already)throw new Exception("Existing document refused"); Owned.Add(doc);return (IZSceneDoc)doc;
}
static string Expr(string text,int depth,Dictionary<string,object> parameters) {
 foreach(var key in parameters.Keys) text=System.Text.RegularExpressions.Regex.Replace(text,"\\b"+key+"\\b",m=>String.Concat(System.Linq.Enumerable.Repeat("Parent\\",depth))+"Params\\"+key);
 return text;
}
static void Bind(IZSceneElement element,Dictionary<string,object> spec,int depth,Dictionary<string,object> pars) {
 var identity=element.GetAnchorTransform();identity.MakeIdentity();element.SetAnchorTransform(identity);
 var matrix=element.GetTransformToParent();matrix.MakeIdentity();
 var rot=(object[])spec["rotation"];var pos=(object[])spec["initial_mm"];
 for(int i=0;i<3;i++){for(int j=0;j<3;j++)matrix.SetValue(i,j,Convert.ToDouble(((object[])rot[i])[j]));matrix.SetValue(3,i,Convert.ToDouble(pos[i])/1000);}
 element.SetTransformToParent(matrix);element.ForceSetupParameterExpression();
 var expressions=(object[])spec["position"];
 for(int i=0;i<3;i++)element.set_PositionTransformComponentExpression((eZTransformComponentType)i,Expr((string)expressions[i],depth,pars));
}
static void Rebuild(IZSceneDoc scene){((IZAssembly)scene.GetTopElement()).RegenerateParts(true);scene.Update();}
static void ValidateBuild(Dictionary<string,object> request) {
 if((string)request["contract"]!="t1-machining-prototype-v2" || Convert.ToInt32(request["schema_version"])!=1)
     throw new Exception("Unsupported machining contract");
 if((string)request["source_sha256"]!="b3b6b2f83a916602a575816663025e954588b4f5112a1e5be610f3c6dd2ad3f5" ||
    (string)request["templates_sha256"]!="e3a1fa951ff6214abf34a4ec2b9dbceb039a06c37311b8dc1d2ea540b3e083a1")
     throw new Exception("Unmeasured source revision");
 var targets=new HashSet<int>{990,996,1002,1008,1014,1020,1026,1032,1044,1146,1152,1170,1176};
 var templates=new HashSet<int>{10353,12447,12451,12455,12459,12932,13198,13202,13218};
 var keys=new HashSet<string>();
 if(((object[])request["cuts"]).Length!=48 || ((object[])request["mounts"]).Length!=20)
     throw new Exception("Incomplete pinned prototype plan");
 foreach(var obj in (object[])request["cuts"]){var c=O(obj);
   if(!targets.Contains(Convert.ToInt32(c["target_id"])) || !templates.Contains(Convert.ToInt32(c["template_id"])) || !keys.Add((string)c["key"]))
     throw new Exception("Unknown or repeated machining target");
 }
}
static object Build(Dictionary<string,object> request) {
 ValidateBuild(request);
 var scene=OpenCopy(request,"source");var templates=OpenCopy(request,"templates");
 if(Children(scene.GetTopElement()).Count!=66)throw new Exception("Pinned prototype root count mismatch");
 var u=(IZSceneDocUtility)scene;var tu=(IZSceneDocUtility)templates;
 var pars=O(request["parameters"]);
 foreach(var kv in pars){IZParameter p=null;try{p=scene.ParameterMgr.GetParameterByName(kv.Key);}catch{}if(p==null)p=scene.ParameterMgr.CreateParameter(eZParamType.Z_PARAMETER_TYPE_LENGTH,kv.Key,Convert.ToDouble(kv.Value)/1000);p.Expression=Convert.ToDouble(kv.Value).ToString(System.Globalization.CultureInfo.InvariantCulture)+" mm";}
 foreach(var obj in (object[])request["mounts"]){var m=O(obj);Bind((IZSceneElement)u.GetElementById(Convert.ToInt32(m["id"])),m,1,pars);}
 var added=new List<object>();
 foreach(var obj in (object[])request["cuts"]){var c=O(obj);int target=Convert.ToInt32(c["target_id"]);var part=(IZPart)u.GetElementById(target);
 int before=((IZBody)part.GetBody(true)).GetFacesCount();
 var original=(IZFeature)tu.GetElementById(Convert.ToInt32(c["template_id"]));
 if(original.OperationType!=eZOperationType.Z_SUBTRACT)throw new Exception("Only measured negative features are accepted");
 var f=original.CopyFeatureTo(part);((IZElement)f).Name="RP_Cut_"+(string)c["key"];
 ((IZExtrudeFeature)f).ExtrudeThroughPart=(bool)c["through_target"];
 if(c.ContainsKey("size")){var size=(object[])c["size"];var box=(IZSizeBox)f;
 box.LengthExpression=Expr((string)size[0],2,pars);box.WidthExpression=Expr((string)size[1],2,pars);box.HeightExpression=Expr((string)size[2],2,pars);}
 Bind((IZSceneElement)f,c,2,pars);part.Regenerate();part.Update();
 int after=((IZBody)part.GetBody(true)).GetFacesCount();
 added.Add(new{key=c["key"],target=target,feature_id=((IZElement)f).Id,faces_before=before,faces_after=after,position=Matrix((IZSceneElement)f,true)});
 }
 Rebuild(scene);var rows=new List<object>();Walk(scene.GetTopElement(),"root",rows);Write("built_inventory.json",new{rows=rows});
 string final=Path.Combine(Folder,"RockPro_T1_machined.ics");scene.SaveAs(final,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
 Write("machining.json",new{features=added,result=final,result_sha256=Hash(final)});
 return new{features=added.Count,result=final,result_sha256=Hash(final)};
}
static object Fit(Dictionary<string,object> request) {
 var scene=OpenCopy(request,"source");var u=(IZSceneDocUtility)scene;var rows=new List<object>();
 foreach(var obj in (object[])request["pairs"]){var pair=O(obj);int part=Convert.ToInt32(pair["part"]),other=Convert.ToInt32(pair["other"]);
 bool interference=((IZPart)u.GetElementById(part)).HasInterference(u.GetElementById(other));rows.Add(new{part=part,other=other,interference=interference});}
 Write("fit.json",new{pairs=rows});return new{pairs=rows};
}
static object Verify(Dictionary<string,object> request) {
 var scene=OpenCopy(request,"source");var results=new List<object>();
 foreach(var o in (object[])request["cases"]){var test=O(o);var pars=O(test["parameters"]);
 foreach(var kv in pars)scene.ParameterMgr.GetParameterByName(kv.Key).Expression=Convert.ToDouble(kv.Value).ToString(System.Globalization.CultureInfo.InvariantCulture)+" mm";
 Rebuild(scene);var u=(IZSceneDocUtility)scene;
 foreach(var q in (object[])test["expected"]){var expected=O(q);int id=Convert.ToInt32(expected["id"]);var e=(IZSceneElement)u.GetElementById(id);var actual=Matrix(e,true);var pos=(object[])expected["position"];
 for(int i=0;i<3;i++)if(Math.Abs(actual[3][i]-Convert.ToDouble(pos[i]))>.01)throw new Exception("Position mismatch "+id+" "+test["name"]+" actual="+J.Serialize(actual[3])+" expected="+J.Serialize(pos));
 if(expected.ContainsKey("size")){var size=(object[])expected["size"];var box=(IZSizeBox)e;double[] dims={box.Length*1000,box.Width*1000,box.Height*1000};
 for(int j=0;j<3;j++)if(Math.Abs(dims[j]-Convert.ToDouble(size[j]))>.01)throw new Exception("Machining size mismatch "+id+" "+test["name"]);}

 }
 var fs=new List<object>();foreach(var q in (object[])request["targets"]){var t=O(q);int id=Convert.ToInt32(t["id"]);var part=(IZPart)u.GetElementById(id);int faces=((IZBody)part.GetBody(true)).GetFacesCount();if(faces!=Convert.ToInt32(t["faces"]))throw new Exception("Machined topology changed on "+id+" faces="+faces);fs.Add(new{id=id,faces=faces});}
 if(request.ContainsKey("fit_pairs"))foreach(var obj in (object[])request["fit_pairs"]){var pair=O(obj);int part=Convert.ToInt32(pair["part"]),other=Convert.ToInt32(pair["other"]);
 if(((IZPart)u.GetElementById(part)).HasInterference(u.GetElementById(other)))throw new Exception("Interference "+part+" / "+other+" in "+test["name"]);}
 results.Add(new{name=test["name"],positions_checked=((object[])test["expected"]).Length,targets=fs});
 if((string)test["name"]=="A-restored"){
 string path=Path.Combine(Folder,"RockPro_T1_wyciecia_parametryczne.ics");scene.SaveAs(path,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
 var doc=(IZDoc)scene;doc.Close();Owned.Remove(doc);bool already;doc=App.OpenFile2(path,false,false,out already);if(already)throw new Exception("Unexpected reopened ownership");Owned.Add(doc);scene=(IZSceneDoc)doc;
 }
 }
 var rows=new List<object>();Walk(scene.GetTopElement(),"root",rows);Write("verified_inventory.json",new{rows=rows});
 string final=Path.Combine(Folder,"RockPro_T1_final.ics");scene.SaveAs(final,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
 Write("verification.json",new{passed=true,cases=results,result=final,result_sha256=Hash(final),production_approved=false});return new{cases=results.Count,result=final,result_sha256=Hash(final)};
}
public static int Run(string folder){Folder=folder;Owned.Clear();Presentation=false;bool passed=false;string error=null,before=null,after=null;object data=null;var cleanup=new List<object>();try{var request=O(J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));if(Convert.ToInt32(request["expected_pid"])!=System.Diagnostics.Process.GetCurrentProcess().Id)throw new Exception("Wrong host PID");dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");App=(IZBaseApp)legacy.ZIronCADApp;if(request.ContainsKey("expected_api_major")&&!App.ApiVersion.StartsWith(Convert.ToString(request["expected_api_major"])+".",StringComparison.Ordinal))throw new Exception("Wrong host API version: "+App.ApiVersion);before=J.Serialize(State());Write("before.json",new{state=State(),api_version=App.ApiVersion});string mode=(string)request["mode"];if(mode=="inspect")data=Inspect(request);else if(mode=="build")data=Build(request);else if(mode=="verify")data=Verify(request);else if(mode=="fit")data=Fit(request);else if(mode=="present"){if(Hash((string)request["source"])!=(string)request["source_sha256"])throw new Exception("Presentation hash mismatch");
 if(request.ContainsKey("close_previous")){string previous=Path.GetFullPath((string)request["close_previous"]);var old=App.GetOpenDocByName(previous);
 if(old!=null){if(!String.Equals(Path.GetFullPath(old.Name),previous,StringComparison.OrdinalIgnoreCase))throw new Exception("Unexpected previous document");
 if(old.Modified)((IZSceneDoc)old).SaveAs(Path.Combine(Folder,"previous_presentation_preserved.ics"),eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);old.Close();}}
 bool already;var finalDoc=App.OpenFile2((string)request["source"],false,true,out already);Presentation=true;((IZSceneDoc)finalDoc).UpdateGraphics(0);((IZSceneDoc)finalDoc).Redraw();data=new{opened=finalDoc.Name};}else throw new Exception("Unknown fixed action");passed=true;}catch(Exception e){error=e.ToString();}finally{foreach(var doc in new List<IZDoc>(Owned)){try{if(doc.Modified)((IZSceneDoc)doc).SaveAs(Path.Combine(Folder,"preserved_"+Guid.NewGuid().ToString("N")+".ics"),eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);if(doc.Modified)throw new Exception("Dirty owned doc");string path=doc.Name;doc.Close();Owned.Remove(doc);cleanup.Add(path);}catch(Exception e){error+=" CLEANUP: "+e;passed=false;}}try{after=J.Serialize(State());if(!Presentation && before!=after){passed=false;error+=" Active user context changed";}}catch(Exception e){passed=false;error+=" STATE: "+e;}Write("result.json",new{passed=passed,error=error,before=before,after=after,remaining_owned=Owned.Count,cleanup=cleanup,data=data});}return passed?0:1;}
}}
