// Development bridge: export a source-bound owned copy without CAD writes/regeneration.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;
namespace RockPro { public static class LatchInProcess {
static readonly JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=128000000};
static string Hash(string path){using(var s=File.OpenRead(path))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant();}
static object State(IZBaseApp app){return new{active=app.ActiveDoc==null?null:app.ActiveDoc.FileGUID,documents=((Array)app.GetAllOpenDocs()??new object[0]).Cast<object>().Select(x=>{var d=x as IZDoc;if(d==null)d=(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));return new{path=d.Name,guid=d.FileGUID,modified=d.Modified};}).OrderBy(x=>x.path,StringComparer.Ordinal).ToArray()};}
public static int Run(string folder){var result=new Dictionary<string,object>();IZBaseApp app=null;IZDoc owned=null,previous=null;bool passed=false;string before=null,source=null,expected=null;
 try{
  var r=(Dictionary<string,object>)J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json")));
  int pid=System.Diagnostics.Process.GetCurrentProcess().Id;result["pid"]=pid;
  if(pid!=Convert.ToInt32(r["expected_pid"]))throw new Exception("Wrong host PID before export");
  dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");app=(IZBaseApp)legacy.ZIronCADApp;
  if(!app.ApiVersion.StartsWith(Convert.ToString(r["expected_api_major"])+"."))throw new Exception("Wrong host API");
  previous=app.ActiveDoc;before=J.Serialize(State(app));
  source=Path.GetFullPath((string)r["source"]);expected=(string)r["source_sha256"];
  if(Hash(source)!=expected)throw new Exception("Source SHA mismatch");
  string copy=Path.Combine(folder,"reference-copy.ics");File.Copy(source,copy,false);
  bool already;owned=app.OpenFile2(copy,true,false,out already);
  if(already){owned=null;throw new Exception("Copy ownership refused");}
  if(owned==null||!String.Equals(Path.GetFullPath(owned.Name),copy,StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong opened document");
  if(owned.Modified)throw new Exception("Read-only copy unexpectedly modified before export");
  string output=Path.Combine(folder,"native-export.zip");((IZSceneDoc)owned).ExportICWebViewerFile(output);
  if(!File.Exists(output)||new FileInfo(output).Length==0)throw new Exception("Missing exported geometry");
  if(owned.Modified)throw new Exception("Export dirtied copy; retained without saving");
  owned.Close();owned=null;
  result["export_sha256"]=Hash(output);result["source_sha256"]=expected;
  result["copy_unchanged"]=Hash(copy)==expected;result["api_version"]=app.ApiVersion;
  passed=(bool)result["copy_unchanged"];
 }catch(Exception e){result["error"]=e.ToString();}
 finally{
  if(owned!=null&&!owned.Modified)try{owned.Close();owned=null;}catch(Exception e){result["cleanup_error"]=e.ToString();passed=false;}
  if(app!=null&&before!=null)try{
   if(previous!=null&&app.ActiveDoc!=previous)app.ActiveDoc=previous;
   result["context_preserved"]=J.Serialize(State(app))==before;
   if(!(bool)result["context_preserved"])passed=false;
  }catch(Exception e){result["context_error"]=e.ToString();passed=false;}
  if(source!=null&&expected!=null){result["source_unchanged"]=Hash(source)==expected;if(!(bool)result["source_unchanged"])passed=false;}
  result["remaining_owned"]=owned==null?0:1;result["saved"]=false;result["passed"]=passed;
  File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(result));
 }
 return passed?0:1;
}
}}
