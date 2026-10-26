// Camera-only review on exact owned copies. User documents are never closed/saved.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;
namespace RockPro {public static class LatchInProcess {
static readonly JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=16000000};
static string Hash(string p){using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
static Dictionary<string,object> O(object a){return (Dictionary<string,object>)a;}
static IZDoc Doc(object raw){var d=raw as IZDoc;return d??(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(raw)));}
static object[] Snapshot(IZBaseApp app,HashSet<string> own){return ((Array)app.GetAllOpenDocs()).Cast<object>().Select(Doc).Where(d=>!own.Contains(d.Name)).Select(d=>(object)new{path=d.Name,guid=d.FileGUID,modified=d.Modified}).OrderBy(d=>J.Serialize(d)).ToArray();}
public static int Run(string folder){var result=new Dictionary<string,object>();bool passed=false;var outputs=new List<object>();IZBaseApp app=null;IZDoc previous=null;var own=new HashSet<string>(StringComparer.OrdinalIgnoreCase);string before=null;
 try{
  var request=O(J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));
  if(Convert.ToInt32(request["expected_pid"])!=System.Diagnostics.Process.GetCurrentProcess().Id)throw new Exception("Wrong PID");
  dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");app=(IZBaseApp)legacy.ZIronCADApp;
  if(!app.ApiVersion.StartsWith("29."))throw new Exception("2027 review only");
  string review=Path.GetFullPath((string)request["review_folder"]);var models=(object[])request["models"];
  foreach(var item in models){var row=O(item);own.Add(Path.Combine(review,(string)row["key"]+"_"+Path.GetFileName((string)row["source"])));}
  previous=app.ActiveDoc;before=J.Serialize(Snapshot(app,own));
  if(!(request.ContainsKey("audit_only")&&(bool)request["audit_only"]))foreach(var item in models){var row=O(item);string key=(string)row["key"],source=(string)row["source"],expected=(string)row["sha256"],path=Path.Combine(review,key+"_"+Path.GetFileName(source));
   if(Hash(source)!=expected||Hash(path)!=expected)throw new Exception("Revision changed before camera-only review");
   var doc=app.GetOpenDocByName(path);if(doc==null||!String.Equals(doc.Name,path,StringComparison.OrdinalIgnoreCase)||doc.Modified)throw new Exception("Owned unchanged review document required by exact full path");
   app.ActiveDoc=doc;var scene=(IZSceneDoc)doc;scene.AdjustCameraToFitShapeInRect(1200,900);scene.Redraw();
   string image=Path.Combine(folder,key+".bmp");scene.ExportImage(image,eZImageFormat.Z_IMAGE_BMP,1200,900,false);
   if(Hash(source)!=expected||Hash(path)!=expected)throw new Exception("Unexpected disk write");
   outputs.Add(new{key=key,image=image,camera_only=true,saved=false});
  }
  foreach(var doc in ((Array)app.GetAllOpenDocs()).Cast<object>().Select(Doc).Where(d=>own.Contains(d.Name)).ToArray())doc.Close();
  // Restore an existing user document by full path, never by shared FileGUID.
  var preferred=app.GetOpenDocByName((string)request["restore_user_path"]);if(preferred!=null)app.ActiveDoc=preferred;
  passed=before==J.Serialize(Snapshot(app,own));result["user_documents_preserved"]=passed;result["review_copies_closed"]=!((Array)app.GetAllOpenDocs()).Cast<object>().Select(Doc).Any(d=>own.Contains(d.Name));
  if(!(bool)result["review_copies_closed"])passed=false;
 }catch(Exception x){passed=false;result["error"]=x.ToString();if(app!=null&&previous!=null)try{app.ActiveDoc=previous;}catch{}}
 result["images"]=outputs;result["passed"]=passed;result["saved"]=false;File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(result));return passed?0:1;
}
}}
