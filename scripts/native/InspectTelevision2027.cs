// Read-only source-copy inspection. No spline-buffer calls or modifications.
using System;using System.IO;using System.Linq;using System.Collections.Generic;
using System.Runtime.InteropServices;using System.Web.Script.Serialization;using interop.ICApiIronCAD;
namespace RockPro {public static class LatchInProcess {
static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=64000000};
static double[] N(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
static string Hash(string p){using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
static IZDoc Doc(object x){return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));}
static double[] Matrix(IZSceneElement e,bool world){var m=world?e.GetTransformToGlobal():e.GetTransformToParent();return Enumerable.Range(0,16).Select(k=>m.GetValue(k/4,k%4)).ToArray();}
static object[] Parameters(IZParameterMgr mgr){var a=new List<object>();for(int i=0;i<mgr.Count;i++){var p=mgr.GetParameter(i);a.Add(new{name=p.Name,expression=p.Expression,notes=p.Notes});}return a.ToArray();}
static void Walk(IZElement e,int parent,int depth,List<object> rows){
 if(depth>45||rows.Count>20000)throw new Exception("Inventory budget");
 var r=new Dictionary<string,object>{{"id",e.Id},{"parent",parent},{"depth",depth},{"name",e.Name},{"type",e.Type.ToString()},{"children",e.GetChildrenCount()}};
 var se=(IZSceneElement)e;r["local_matrix_m"]=Matrix(se,false);r["world_matrix_m"]=Matrix(se,true);
 if(e.Type==eZElementType.Z_ELEMENT_PART){var p=(IZPart)e;r["bounds_m"]=N(p.GetBody(true).GetBoundingBox());var fm=(IZPartFeatureMgr)p;var fs=new List<object>();
  for(int i=0;i<fm.GetFeaturesCount();i++){try{var f=fm.GetFeatureAt(i);var fe=(IZElement)f;var fr=new Dictionary<string,object>{{"id",fe.Id},{"name",fe.Name},{"operation",f.OperationType.ToString()},{"matrix_m",Matrix((IZSceneElement)f,false)}};var ex=f as IZExtrudeFeature;
   var box=f as IZSizeBox;if(box!=null)fr["expressions"]=new[]{box.LengthExpression,box.WidthExpression,box.HeightExpression};
   if(ex!=null){fr["extrude"]=true;fr["forward_m"]=ex.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_FORWARD);fr["backward_m"]=ex.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_BACKWARD);fr["profile_matrix_m"]=Matrix((IZSceneElement)ex.CrossSection,false);fr["curves"]=((Array)ex.CrossSection.GetCurveIds()).Cast<object>().Select(raw=>ex.CrossSection.GetCurveType(Convert.ToInt32(raw)).ToString()).ToArray();}
   fs.Add(fr);}catch(COMException featureError){fs.Add(new{index=i,error=featureError.Message});}}
  r["features"]=fs;
 }
 rows.Add(r);if(e.Type==eZElementType.Z_ELEMENT_PART)return;
 var children=e.GetChildrenZArray();for(int i=0;i<e.GetChildrenCount();i++){object raw;children.Get(i,out raw);var c=(IZElement)raw;if(c.Type==eZElementType.Z_ELEMENT_PART||c.Type==eZElementType.Z_ELEMENT_ASSEMBLY)Walk(c,e.Id,depth+1,rows);}
}
public static int Run(string folder){var report=new Dictionary<string,object>();IZDoc owned=null;bool passed=false;
 try{var r=(Dictionary<string,object>)J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json")));if((string)r["contract"]!="rockpro-tv-inspect-v1"||System.Diagnostics.Process.GetCurrentProcess().Id!=Convert.ToInt32(r["expected_pid"]))throw new Exception("Wrong request/host");
 dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;if(!app.ApiVersion.StartsWith("29."))throw new Exception("2027 required");
 var before=((Array)app.GetAllOpenDocs()??new object[0]).Cast<object>().Select(Doc).ToDictionary(d=>d.FileGUID,d=>new{path=d.Name,modified=d.Modified});report["before"]=before;
 string source=(string)r["source"];if(Hash(source)!=(string)r["sha256"])throw new Exception("Source changed");bool already;owned=app.OpenFile2(source,false,true,out already);if(already){owned=null;throw new Exception("Reference is already open; ownership refused");}var s=(IZSceneDoc)owned;
 var rows=new List<object>();Walk(s.GetTopElement(),-1,0,rows);report["rows"]=rows;report["parameters"]=Parameters(s.ParameterMgr);report["source"]=source;report["api_version"]=app.ApiVersion;report["source_unchanged"]=Hash(source)==(string)r["sha256"];
 report["reference_modified_after_geometry_read"]=owned.Modified;
 s.AdjustCameraToFitShapeInRect(1400,1100);s.ExportImage(Path.Combine(folder,"original.png"),eZImageFormat.Z_IMAGE_PNG,1400,1100,true);
 var after=((Array)app.GetAllOpenDocs()??new object[0]).Cast<object>().Select(Doc).ToDictionary(d=>d.FileGUID,d=>d);
 foreach(var pair in before)if(!after.ContainsKey(pair.Key)||after[pair.Key].Modified!=pair.Value.modified)throw new Exception("Existing document changed");
 report["existing_documents_preserved"]=true;report["reference_left_open"]=true;report["reference_guid"]=owned.FileGUID;passed=true;
 }catch(Exception ex){report["error"]=ex.ToString();}
 finally{if(!passed&&owned!=null)try{owned.Close2(true);}catch(Exception ex){report["cleanup_error"]=ex.ToString();}report["passed"]=passed;File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(report));}return passed?0:1;
}
}}
