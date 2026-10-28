// Extract exactly one complete, source-bound H2026. No scene manufacturing claim.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;
namespace RockPro { public static class LatchInProcess {
static readonly JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=64000000};
static string Hash(string p){using(var s=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant();}
static IZDoc Doc(object x){return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));}
static object State(IZBaseApp a){return ((Array)a.GetAllOpenDocs()).Cast<object>().Select(x=>{var d=Doc(x);return new{path=d.Name,guid=d.FileGUID,modified=d.Modified};}).OrderBy(x=>x.path).ToArray();}
static List<IZElement> Leaves(IZElement e){var result=new List<IZElement>();if(e.Type==eZElementType.Z_ELEMENT_PART){result.Add(e);return result;}var n=e.GetChildrenCount();if(n>0){var children=e.GetChildrenZArray();for(int i=0;i<n;i++){object x;children.Get(i,out x);result.AddRange(Leaves((IZElement)x));}}return result;}
public static int Run(string folder){
 var result=new Dictionary<string,object>();IZDoc owned=null;IZBaseApp app=null;object before=null;bool passed=false;string source=null,expected=null;
 try{
  var r=(Dictionary<string,object>)J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json")));
  if((string)r["contract"]!="rockpro-requested-h2026-extract-v1")throw new Exception("Wrong extraction contract");
  if(System.Diagnostics.Process.GetCurrentProcess().Id!=Convert.ToInt32(r["expected_pid"]))throw new Exception("Wrong host PID");
  dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");app=(IZBaseApp)legacy.ZIronCADApp;
  if(!app.ApiVersion.StartsWith("29."))throw new Exception("IronCAD 2027 required");before=State(app);result["before"]=before;
  source=Path.GetFullPath((string)r["source"]);expected=(string)r["source_sha256"];
  if(expected!="59c93dc0d9c927bb036d3ce45615c4ec6fbda1c175ec8c33581e432ab32f510b"||Hash(source)!=expected)throw new Exception("Unrecognized source");
  string copy=Path.Combine(folder,"source-copy.ics");File.Copy(source,copy,false);bool already;
  owned=app.OpenFile2(copy,false,false,out already);if(already){owned=null;throw new Exception("Copy ownership refused");}
  var scene=(IZSceneDoc)owned;var node=((IZSceneDocUtility)scene).GetElementById(3886);
  if(node.Name!="H2026"||node.Type!=eZElementType.Z_ELEMENT_ASSEMBLY)throw new Exception("H2026 identity differs");
  var leaves=Leaves(node);if(!leaves.Select(e=>e.Id).OrderBy(x=>x).SequenceEqual(new int[]{3887,3889}))throw new Exception("Incomplete or different source handle");
  var matrix=((IZSceneElement)node).GetTransformToGlobal();var values=new List<double>();for(int i=0;i<4;i++)for(int k=0;k<4;k++)values.Add(matrix.GetValue(i,k));
  string output=Path.Combine(folder,"H2026_complete_source.ics");((IZAssembly)node).SaveAs(output,false);
  if(!File.Exists(output)||new FileInfo(output).Length==0)throw new Exception("Missing native handle file");
  result["source_world_matrix_m"]=values;result["source_sha256"]=expected;result["source_ids"]=leaves.Select(e=>e.Id).ToArray();
  result["source_modified_after_export"]=owned.Modified;
  // The operation owns this byte-identical input copy only. Discard any SDK
  // export metadata, never write the original or an already-open document.
  owned.Close2(true);owned=null;
  owned=app.OpenFile2(output,false,false,out already);if(already){owned=null;throw new Exception("Extracted file was already open");}
  var reopened=Leaves(((IZSceneDoc)owned).GetTopElement());if(reopened.Count!=2)throw new Exception("Extracted handle lost a physical body");
  var extents=new List<object>();foreach(var leaf in reopened){var body=((IZPart)leaf).GetBody(true);if(body.GetFacesCount()==0)throw new Exception("Empty exported body");extents.Add(new{name=leaf.Name,faces=body.GetFacesCount(),bounds_local_m=body.GetBoundingBox()});}
  result["bodies_after_reopen"]=extents;result["asset_file"]=output;owned.Close();owned=null;result["asset_sha256"]=Hash(output);
  result["source_unchanged"]=Hash(source)==expected;result["owned_input_copy_unchanged"]=Hash(copy)==expected;
  if(!(bool)result["source_unchanged"]||!(bool)result["owned_input_copy_unchanged"])throw new Exception("Source integrity mismatch");passed=true;
 }catch(Exception e){result["error"]=e.ToString();}
 finally{
  if(owned!=null)try{owned.Close2(true);owned=null;}catch(Exception e){result["cleanup_error"]=e.ToString();passed=false;}
  if(app!=null&&before!=null){result["after"]=State(app);result["existing_documents_preserved"]=J.Serialize(before)==J.Serialize(result["after"]);if(!(bool)result["existing_documents_preserved"])passed=false;}
  result["mounting_approved"]=false;result["cutout_approved"]=false;result["production_approved"]=false;result["passed"]=passed;
  File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(result));
 }
 return passed?0:1;
}
}}
