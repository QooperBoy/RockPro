using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;
using RunningTable=System.Runtime.InteropServices.ComTypes.IRunningObjectTable;
using BindContext=System.Runtime.InteropServices.ComTypes.IBindCtx;
using MonikerEnumerator=System.Runtime.InteropServices.ComTypes.IEnumMoniker;
using Moniker=System.Runtime.InteropServices.ComTypes.IMoniker;
class DocumentLifecycle {
 [DllImport("ole32.dll")] static extern int GetRunningObjectTable(int r,out RunningTable t);
 [DllImport("ole32.dll")] static extern int CreateBindCtx(int r,out BindContext c);
 static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=16000000};
 static object Attach(string source){RunningTable r;BindContext c;Marshal.ThrowExceptionForHR(GetRunningObjectTable(0,out r));Marshal.ThrowExceptionForHR(CreateBindCtx(0,out c));MonikerEnumerator e;r.EnumRunning(out e);Moniker[] m=new Moniker[1];while(e.Next(1,m,IntPtr.Zero)==0){string n;try{m[0].GetDisplayName(c,null,out n);}catch{continue;}if(Path.IsPathRooted(n)&&Same(n,source)){object o;r.GetObject(m[0],out o);return o;}}throw new Exception("Explicit source is not already open in ROT");}
 static bool Same(string a,string b){return String.Equals(Path.GetFullPath(a),Path.GetFullPath(b),StringComparison.OrdinalIgnoreCase);}
 static string Hash(string p){using(var f=File.Open(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite)){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}}
 static void Write(string p,object o){using(var f=new FileStream(p,FileMode.CreateNew,FileAccess.Write,FileShare.Read)){using(var w=new StreamWriter(f)){w.Write(J.Serialize(o));w.Flush();f.Flush(true);}}}
 static List<IZDoc> Docs(IZBaseApp a){var result=new List<IZDoc>();var items=a.GetAllOpenDocs() as IEnumerable;if(items==null)throw new Exception("Open document enumeration unavailable");foreach(object v in items){var d=v as IZDoc;if(d==null)throw new Exception("Unrecognized document in API list");result.Add(d);}return result;}
 static Dictionary<string,object> Row(IZDoc d){var r=new Dictionary<string,object>{{"path",d.Name},{"file_guid",d.FileGUID},{"modified",d.Modified},{"read_only",d.IsReadOnly()},{"type",(int)d.Type}};if(d.Name=="Scene1"||d.Name=="Scene2"){var scene=d as IZSceneDoc;if(scene!=null){r["physical_children"]=scene.GetTopElement().GetChildrenCount();}}return r;}
 static string Safe(string s){var invalid=Path.GetInvalidFileNameChars();return new string(s.Where(c=>Array.IndexOf(invalid,c)<0).ToArray());}
 [STAThread]static int Main(string[] args){try{if(args.Length!=2)throw new Exception("request/report arguments required");var q=J.Deserialize<Dictionary<string,object>>(File.ReadAllText(args[0]));if(q.Count!=3||!q.ContainsKey("action")||!q.ContainsKey("source")||!q.ContainsKey("directory"))throw new Exception("Exact request fields required");string action=(string)q["action"],source=Path.GetFullPath((string)q["source"]),folder=Path.GetFullPath((string)q["directory"]);dynamic legacy=Attach(source);IZBaseApp app=(IZBaseApp)legacy.Application.ZIronCADApp;var documents=Docs(app);var before=documents.Select(d=>(object)Row(d)).ToArray();var records=new List<object>();
 if(action=="audit"){Write(args[1],new{passed=true,action=action,count=documents.Count,documents=before});Console.WriteLine(J.Serialize(before));Environment.Exit(0);return 0;}
 if(action=="close_owned_empty"){
  var owned=new Dictionary<string,string>{{"Scene1","{7684DB7D-B0C5-4265-AC43-C560789E1AC3}"},{"Scene2","{151E8EC7-AA5D-44A1-952D-D757A7DEE681}"}};
  var closed=new List<object>();
  foreach(var d in documents){
   if(!owned.ContainsKey(d.Name))continue;
   var scene=d as IZSceneDoc;
   if(scene==null||d.FileGUID!=owned[d.Name]||scene.GetTopElement().GetChildrenCount()!=0)throw new Exception("Refusing to close nonempty or unidentified scene");
   var proof=Row(d);proof["ownership"]="Exact GUID of this agent's failed primitive creation probe; zero physical children";
   d.SetModifiedFlag(false);d.Close();closed.Add(proof);
  }
  Write(args[1],new{passed=true,action=action,closed=closed,remaining=Docs(app).Select(d=>(object)Row(d)).ToArray()});Console.WriteLine("Closed only owned empty probes: "+closed.Count);Environment.Exit(0);return 0;
 }
 if(action=="save_all"){
  if(Directory.Exists(folder))throw new Exception("Unique backup directory must not exist");Directory.CreateDirectory(folder);Write(Path.Combine(folder,"before.json"),new{documents=before,authorization="User explicitly requested save all open documents after tests, then restart"});
  // Capture every dirty/unnamed document before saving any original.
  for(int i=0;i<documents.Count;i++){
   IZDoc d=documents[i];var record=new Dictionary<string,object>{{"before",Row(d)}};records.Add(record);
   string old=d.Name;bool named=Path.IsPathRooted(old)&&File.Exists(old);bool needs=d.Modified||!named;
   record["needed_save_before"]=needs;
   if(needs){
    IZSceneDoc scene=d as IZSceneDoc;if(scene==null)throw new Exception("Cannot back up unsaved non-scene document safely; no original save performed");
    string label=(i+1).ToString("D3")+"_"+Safe(Path.GetFileNameWithoutExtension(old));if(label.EndsWith("_"))label+="unnamed";
    string memory=Path.Combine(folder,label+"_memory_before.ics");scene.SaveAsCopy(memory,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
    record["memory_backup"]=memory;record["memory_backup_sha256"]=Hash(memory);
    if(named){string disk=Path.Combine(folder,label+"_disk_before.ics");File.Copy(old,disk,false);record["disk_backup"]=disk;record["disk_backup_sha256"]=Hash(disk);}
    record["unique_saved_path"]=Path.Combine(folder,label+"_saved.ics");
   }
  }
  Write(Path.Combine(folder,"backups_completed.json"),new{passed=true,original_saves_started=false,documents=records});
  for(int i=0;i<documents.Count;i++){
   IZDoc d=documents[i];var record=(Dictionary<string,object>)records[i];string old=d.Name;bool named=Path.IsPathRooted(old)&&File.Exists(old);bool needs=d.Modified||!named;
   if(needs){
    if(!record.ContainsKey("memory_backup"))throw new Exception("Previously clean document changed during backup; stop before unprotected save");
    if(named&&!d.IsReadOnly()){d.Save();record["save_mode"]="save_existing_user_authorized";if(!Same(d.Name,old))throw new Exception("Save changed existing document path");}
    else{string output=(string)record["unique_saved_path"];((IZSceneDoc)d).SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);record["save_mode"]=named?"read_only_preserved_as_unique_copy":"unnamed_preserved_as_unique_copy";record["saved_path"]=output;if(!Same(d.Name,output))throw new Exception("SaveAs path mismatch");}
   }else record["save_mode"]="already_clean_unchanged";
   if(d.Modified||!Path.IsPathRooted(d.Name)||!File.Exists(d.Name))throw new Exception("Document remains unsaved after save-all");
   record["after"]=Row(d);record["saved_sha256"]=Hash(d.Name);Write(Path.Combine(folder,(i+1).ToString("D3")+"_record.json"),record);Console.WriteLine("SAVED "+d.Name);
  }
  var after=Docs(app);if(after.Count!=documents.Count||after.Any(d=>d.Modified))throw new Exception("Document inventory changed or is dirty after save-all");Write(args[1],new{passed=true,action=action,count=after.Count,backup_directory=folder,documents=records,after=after.Select(d=>(object)Row(d)).ToArray()});Console.WriteLine("SAVE_ALL PASS "+after.Count);Environment.Exit(0);return 0;
 }
 if(action=="save_remaining_verified"){
  var proof=J.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(folder,"backups_completed.json")));
  if(!(bool)proof["passed"])throw new Exception("Backup phase not complete");
  var savedRows=((IEnumerable)proof["documents"]).Cast<Dictionary<string,object>>().ToList();
  if(savedRows.Count!=documents.Count)throw new Exception("Inventory count changed");
  foreach(var r in savedRows){foreach(string kind in new[]{"memory_backup","disk_backup"})if(r.ContainsKey(kind)&&Hash((string)r[kind])!=(string)r[kind+"_sha256"])throw new Exception("Backup hash changed");}
  for(int i=0;i<documents.Count;i++){
   var d=documents[i];var r=savedRows[i];var b=(Dictionary<string,object>)r["before"];
   bool renamedOriginal=i==0&&Same(d.Name,Path.Combine(folder,"001_Showcase_Epson_parametry_saved_readonly.ics"));
   if(d.FileGUID!=(string)b["file_guid"]||(!renamedOriginal&&!Same(d.Name,(string)b["path"])))throw new Exception("Document identity changed");
   r["continuation_before"]=Row(d);
   if(d.Modified){
    if(!r.ContainsKey("memory_backup"))throw new Exception("Dirty document without verified backup");
    string output=(string)r["unique_saved_path"];
    if(File.Exists(output))throw new Exception("Unique save destination exists");
    ((IZSceneDoc)d).SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
    if(!Same(d.Name,output))throw new Exception("SaveAs path mismatch");
    r["save_mode"]="user_authorized_unique_saved_copy";
   }else r["save_mode"]=renamedOriginal?"user_authorized_readonly_saveas_completed":"already_clean";
   if(d.Modified||!File.Exists(d.Name))throw new Exception("Document remains dirty or missing");
   r["after"]=Row(d);r["saved_sha256"]=Hash(d.Name);
   Write(Path.Combine(folder,(i+1).ToString("D3")+"_continued_record.json"),r);Console.WriteLine("CLEAN "+d.Name);
  }
  var after=Docs(app);if(after.Count!=documents.Count||after.Any(d=>d.Modified))throw new Exception("Final inventory dirty or changed");
  Write(args[1],new{passed=true,action=action,count=after.Count,backup_directory=folder,documents=savedRows,after=after.Select(d=>(object)Row(d)).ToArray()});
  Console.WriteLine("SAVE_REMAINING PASS "+after.Count);Environment.Exit(0);return 0;
 }
 if(action=="exit_clean"){
  if(documents.Any(d=>d.Modified||!Path.IsPathRooted(d.Name)||!File.Exists(d.Name)))throw new Exception("Refusing exit with dirty or unnamed documents");Write(args[1],new{passed=true,action="pre_exit_clean",count=documents.Count,documents=before});app.Exit();Console.WriteLine("EXIT_CLEAN requested");Environment.Exit(0);return 0;
 }
 throw new Exception("Unknown fixed lifecycle action");
 }catch(Exception ex){Console.Error.WriteLine(ex);Environment.Exit(1);return 1;}}
}
