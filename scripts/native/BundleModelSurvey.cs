// Read-only survey on hidden, owned copies. No Save/Update/regeneration calls.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;
namespace RockPro { public static class LatchInProcess {
static readonly JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=128000000};
static IZBaseApp App;
[DllImport("ole32.dll")] static extern int GetRunningObjectTable(int reserved,out System.Runtime.InteropServices.ComTypes.IRunningObjectTable table);
[DllImport("ole32.dll")] static extern int CreateBindCtx(int reserved,out System.Runtime.InteropServices.ComTypes.IBindCtx context);
static object Existing(string source){
 System.Runtime.InteropServices.ComTypes.IRunningObjectTable rot;System.Runtime.InteropServices.ComTypes.IBindCtx bind;
 Marshal.ThrowExceptionForHR(GetRunningObjectTable(0,out rot));Marshal.ThrowExceptionForHR(CreateBindCtx(0,out bind));
 System.Runtime.InteropServices.ComTypes.IEnumMoniker iterator;rot.EnumRunning(out iterator);var moniker=new System.Runtime.InteropServices.ComTypes.IMoniker[1];
 while(iterator.Next(1,moniker,IntPtr.Zero)==0){string name;try{moniker[0].GetDisplayName(bind,null,out name);}catch(COMException){continue;}
  if(!Path.IsPathRooted(name)||!String.Equals(Path.GetFullPath(name),Path.GetFullPath(source),StringComparison.OrdinalIgnoreCase))continue;
  object value;rot.GetObject(moniker[0],out value);return value;
 }throw new Exception("Exact existing context required");
}
static System.Diagnostics.Stopwatch Clock;
static Dictionary<string,object> O(object x){return (Dictionary<string,object>)x;}
static string Hash(string p){using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
static void Write(string p,object x){File.WriteAllText(p,J.Serialize(x));}
static double[] Numbers(object raw){return ((Array)raw).Cast<object>().Select(Convert.ToDouble).ToArray();}
static double[][] Matrix(IZSceneElement e,bool world){var m=world?e.GetTransformToGlobal():e.GetTransformToParent();return Enumerable.Range(0,4).Select(i=>Enumerable.Range(0,4).Select(k=>m.GetValue(i,k)*(i==3&&k<3?1000:1)).ToArray()).ToArray();}
static object State(){return new{active=App.ActiveDoc==null?null:App.ActiveDoc.FileGUID,documents=((Array)App.GetAllOpenDocs()??new object[0]).Cast<object>().Select(x=>{
 IZDoc d=x as IZDoc;if(d==null){long address=Convert.ToInt64(x);d=(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(address));}
 return new{path=d.Name,guid=d.FileGUID,modified=d.Modified};}).OrderBy(x=>x.path,StringComparer.Ordinal).ToArray()};}
static void Walk(IZElement e,string path,List<object> rows,List<object> errors,int depth){
 if(rows.Count>=20000||depth>40||Clock.Elapsed.TotalSeconds>180)throw new Exception("Cooperative traversal limit reached");
 var r=new Dictionary<string,object>{{"id",e.Id},{"name",e.Name},{"type",e.Type.ToString()},{"path",path}};
 try{r["world_mm"]=Matrix((IZSceneElement)e,true);r["parent_mm"]=Matrix((IZSceneElement)e,false);}catch(Exception x){errors.Add(new{id=e.Id,field="matrix",error=x.Message});}
 if(e.Type==eZElementType.Z_ELEMENT_PART){
  try{r["bounds_local_m"]=Numbers(((IZPart)e).GetBody(true).GetBoundingBox());}catch(Exception x){errors.Add(new{id=e.Id,field="body_bounds",error=x.Message});}
  try{var fm=(IZPartFeatureMgr)e;var fs=new List<object>();for(int i=0;i<fm.GetFeaturesCount();i++){
   var f=fm.GetFeatureAt(i);var fe=(IZElement)f;fs.Add(new{id=fe.Id,name=fe.Name,type=f.Type.ToString(),operation=f.OperationType.ToString()});
  }r["features"]=fs;}catch(Exception x){errors.Add(new{id=e.Id,field="feature_metadata",error=x.Message});}
 }
 rows.Add(r);var children=e.GetChildrenZArray();for(int i=0;i<e.GetChildrenCount();i++){object child;children.Get(i,out child);var c=(IZElement)child;if(c.Type==eZElementType.Z_ELEMENT_PART||c.Type==eZElementType.Z_ELEMENT_ASSEMBLY)Walk(c,path+"/"+c.Id,rows,errors,depth+1);}
}
public static int Run(string folder){var result=new Dictionary<string,object>();var jobs=new List<object>();bool passed=false,keep=false,openFailure=false;IZDoc owned=null,previous=null;string before=null;
 try{
  var req=O(J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));
  keep=req.ContainsKey("keep_open")&&(bool)req["keep_open"];
  if(Convert.ToInt32(req["expected_pid"])!=System.Diagnostics.Process.GetCurrentProcess().Id)throw new Exception("Wrong host PID");
  dynamic legacy=req.ContainsKey("context_path")?((dynamic)Existing((string)req["context_path"])).Application:Marshal.GetActiveObject("IronCAD.Application");App=(IZBaseApp)legacy.ZIronCADApp;
  if(!App.ApiVersion.StartsWith(Convert.ToString(req["expected_api_major"])+"."))throw new Exception("Wrong API version");
  previous=App.ActiveDoc;before=J.Serialize(State());Write(Path.Combine(folder,"before.json"),State());result["api_version"]=App.ApiVersion;
  foreach(object item in (object[])req["models"]){var spec=O(item);string source=Path.GetFullPath((string)spec["source"]),sha=(string)spec["sha256"],key=(string)spec["key"];
   if(key.Length!=3||key[0]!='M'||!key.Skip(1).All(Char.IsDigit))throw new Exception("Unsafe output key");
   if(Hash(source)!=sha)throw new Exception("Source hash mismatch");
   string target=Path.Combine(folder,keep?key+"_"+Path.GetFileName(source):key+".ics");File.Copy(source,target,false);var errors=new List<object>();var rows=new List<object>();bool already;
   bool readOnly=!(req.ContainsKey("writable_copy")&&(bool)req["writable_copy"]);
   try{owned=App.OpenFile2(target,readOnly,keep,out already);}catch(COMException x){if(!keep)throw;openFailure=true;jobs.Add(new{key=key,opened=false,error=x.ToString(),source_unchanged=Hash(source)==sha});Write(Path.Combine(folder,"progress.json"),jobs);continue;}
   if(already){owned=null;throw new Exception("Copy ownership refused");}if(owned==null)throw new Exception("Open returned null");
   Clock=System.Diagnostics.Stopwatch.StartNew();
   if(req.ContainsKey("preview_only")&&(bool)req["preview_only"]){
    try{((IZSceneDoc)owned).ExportImage(Path.Combine(folder,key+".png"),eZImageFormat.Z_IMAGE_PNG,1200,900,true);}catch(Exception x){errors.Add(new{id=0,field="preview",error=x.Message});}
   }else Walk(((IZSceneDoc)owned).GetTopElement(),"root",rows,errors,0);
   Clock.Stop();
   bool dirty=owned.Modified;Write(Path.Combine(folder,key+"-inventory.json"),new{source=source,source_sha256=sha,copy=target,api_version=App.ApiVersion,rows=rows,errors=errors,modified_after_read=dirty,elapsed_ms=Clock.Elapsed.TotalMilliseconds});
   if(!keep)owned.Close();owned=null;if(!keep&&previous!=null)App.ActiveDoc=previous;
   if(Hash(source)!=sha||Hash(target)!=sha)throw new Exception("Disk integrity check failed");
   jobs.Add(new{key=key,opened=true,copy_path=target,rows=rows.Count,errors=errors.Count,modified_after_read=dirty,source_unchanged=true,owned_copy_closed=!keep,left_open_for_user=keep});
   Write(Path.Combine(folder,"progress.json"),jobs);
  }
  passed=!openFailure;
 }catch(Exception x){result["error"]=x.ToString();}
 finally{
  if(owned!=null)try{owned.Close();owned=null;}catch(Exception x){result["cleanup_error"]=x.ToString();passed=false;}
  try{if(App!=null){if(!keep&&previous!=null)App.ActiveDoc=previous;var after=J.Serialize(State());result["context_preserved"]=before==after;result["context_change_expected"]=keep;Write(Path.Combine(folder,"after.json"),State());
   if(keep&&before!=null){var oldDocs=(object[])O(J.DeserializeObject(before))["documents"];var newDocs=(object[])O(J.DeserializeObject(after))["documents"];bool preserved=oldDocs.All(a=>newDocs.Any(b=>J.Serialize(a)==J.Serialize(b)));result["previous_documents_preserved"]=preserved;if(!preserved)passed=false;}
   else if(before!=after)passed=false;}}catch(Exception x){result["state_error"]=x.ToString();passed=false;}
  result["models"]=jobs;result["passed"]=passed;result["saved"]=false;result["remaining_owned"]=owned==null?0:1;result["production_approved"]=false;Write(Path.Combine(folder,"result.json"),result);
 }
 return passed?0:1;
}
}}
