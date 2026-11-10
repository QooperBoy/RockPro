// Close only references opened by this operation, preserving their readback state.
using System;using System.IO;using System.Linq;using System.Collections.Generic;using System.Runtime.InteropServices;using System.Web.Script.Serialization;using interop.ICApiIronCAD;
namespace RockPro { public static class LatchInProcess {
static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=64000000};
static Dictionary<string,object> O(object x){return (Dictionary<string,object>)x;}
static IZDoc D(object x){return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));}
static string H(string p){using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
public static int Run(string folder){var report=new Dictionary<string,object>();var closed=new List<object>();bool passed=false;
try{var q=O(J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));if((string)q["contract"]!="rockpro-owned-reference-cleanup-v1"||System.Diagnostics.Process.GetCurrentProcess().Id!=Convert.ToInt32(q["expected_pid"]))throw new Exception("Wrong host/contract");
dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;if(!app.ApiVersion.StartsWith("29."))throw new Exception("2027 required");var targets=((object[])q["references"]).Select(O).ToArray();var ids=new HashSet<string>(targets.Select(x=>(string)x["guid"]));
var docs=((Array)app.GetAllOpenDocs()).Cast<object>().Select(D).ToDictionary(d=>d.FileGUID);var before=docs.Where(d=>!ids.Contains(d.Key)).ToDictionary(d=>d.Key,d=>d.Value.Modified);
foreach(var target in targets){string source=Path.GetFullPath((string)target["source"]),checkpoint=Path.GetFullPath((string)target["checkpoint"]);IZDoc doc;if(!docs.TryGetValue((string)target["guid"],out doc)){closed.Add(new{source=source,status="already_closed"});continue;}
if(!String.Equals(doc.Name,source,StringComparison.OrdinalIgnoreCase))throw new Exception("Reference ownership/name changed; refusing to close "+doc.Name);
var srcDir=new DirectoryInfo(Path.GetDirectoryName(source));var dstDir=new DirectoryInfo(Path.GetDirectoryName(checkpoint));if(srcDir.Name!="01_Kopia_zrodla"||dstDir.Name!="04_Snapshoty"||!String.Equals(srcDir.Parent.FullName,dstDir.Parent.FullName,StringComparison.OrdinalIgnoreCase))throw new Exception("Checkpoint outside the owned project");
if(H(source)!=(string)target["sha256"]||File.Exists(checkpoint))throw new Exception("Changed reference or existing checkpoint");
((IZSceneDoc)doc).SaveAs(checkpoint,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);if(!File.Exists(checkpoint))throw new Exception("Readback state was not saved");doc.Close2(true);if(H(source)!=(string)target["sha256"])throw new Exception("Source disk changed");closed.Add(new{source=source,checkpoint=checkpoint,status="saved_and_closed"});}
var after=((Array)app.GetAllOpenDocs()).Cast<object>().Select(D).ToDictionary(d=>d.FileGUID);foreach(var item in before)if(!after.ContainsKey(item.Key)||after[item.Key].Modified!=item.Value)throw new Exception("Unrelated document changed");report["other_documents_preserved"]=true;passed=true;
}catch(Exception ex){report["error"]=ex.ToString();}report["references"]=closed;report["passed"]=passed;File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(report));return passed?0:1;}
}}
