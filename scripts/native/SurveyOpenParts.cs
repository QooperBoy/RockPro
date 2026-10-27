// Read existing scenes in memory. No opening, closing, activating, saving or regenerating.
using System;using System.IO;using System.Linq;using System.Collections.Generic;
using System.Runtime.InteropServices;using System.Web.Script.Serialization;using interop.ICApiIronCAD;
namespace RockPro {public static class LatchInProcess {
static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=64000000};
static string Hash(string p){if(!File.Exists(p))return null;using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
static IZDoc Doc(object raw){var d=raw as IZDoc;return d??(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(raw)));}
static object State(IZBaseApp app){return new{active=app.ActiveDoc==null?null:app.ActiveDoc.FileGUID,documents=((Array)app.GetAllOpenDocs()).Cast<object>().Select(x=>{var d=Doc(x);return new{path=d.Name,guid=d.FileGUID,modified=d.Modified};}).OrderBy(x=>x.path).ToArray()};}
static double[] Numbers(object raw){var a=(Array)raw;return a.Cast<object>().Select(Convert.ToDouble).ToArray();}
static void Walk(IZElement e,string path,List<object> rows,int depth){
 if(depth>50||rows.Count>50000)throw new Exception("Inventory budget exceeded");
 var row=new Dictionary<string,object>{{"id",e.Id},{"name",e.Name},{"type",e.Type.ToString()},{"path",path},{"child_count",e.GetChildrenCount()}};
 try{var m=((IZSceneElement)e).GetTransformToGlobal();var values=new List<double>();for(int i=0;i<4;i++)for(int k=0;k<4;k++)values.Add(m.GetValue(i,k));row["world_matrix_m"]=values;}catch(Exception ex){row["matrix_error"]=ex.Message;}
 if(e.Type==eZElementType.Z_ELEMENT_PART)try{row["bounds_local_m"]=Numbers(((IZPart)e).GetBody(true).GetBoundingBox());}catch(Exception ex){row["bounds_error"]=ex.Message;}
 rows.Add(row);int n=e.GetChildrenCount();if(n==0)return;var children=e.GetChildrenZArray();for(int i=0;i<n;i++){object o;children.Get(i,out o);var child=(IZElement)o;if(child.Type==eZElementType.Z_ELEMENT_PART||child.Type==eZElementType.Z_ELEMENT_ASSEMBLY)Walk(child,path+"/"+child.Id,rows,depth+1);}
}
public static int Run(string folder){var result=new Dictionary<string,object>();bool passed=false;try{
 var req=(Dictionary<string,object>)J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json")));
 if(System.Diagnostics.Process.GetCurrentProcess().Id!=Convert.ToInt32(req["expected_pid"]))throw new Exception("Wrong host PID");
 dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;
 if(!app.ApiVersion.StartsWith(Convert.ToString(req["expected_api_major"])+"."))throw new Exception("Wrong host version");
 var before=State(app);result["before"]=before;var documents=new List<object>();
 foreach(var raw in (Array)app.GetAllOpenDocs()){
  var doc=Doc(raw);var rows=new List<object>();string sourceHash=Hash(doc.Name);var entry=new Dictionary<string,object>{{"path",doc.Name},{"guid",doc.FileGUID},{"modified",doc.Modified},{"disk_sha256",sourceHash},{"memory_disk_equivalence",doc.Modified?"unconfirmed_modified_memory":"unconfirmed_no_geometry_comparison"}};
  try{Walk(((IZSceneDoc)doc).GetTopElement(),"root",rows,0);entry["rows"]=rows;}catch(Exception ex){entry["error"]=ex.Message;}
  entry["disk_unchanged"]=Hash(doc.Name)==sourceHash;documents.Add(entry);
 }
 result["documents"]=documents;result["after"]=State(app);result["context_preserved"]=J.Serialize(before)==J.Serialize(result["after"]);result["api_version"]=app.ApiVersion;
 passed=(bool)result["context_preserved"]&&documents.Cast<Dictionary<string,object>>().All(d=>!d.ContainsKey("error")&&(bool)d["disk_unchanged"]);
}catch(Exception ex){result["error"]=ex.ToString();}
 result["passed"]=passed;result["read_only"]=true;result["saved"]=false;File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(result));return passed?0:1;
}}}
