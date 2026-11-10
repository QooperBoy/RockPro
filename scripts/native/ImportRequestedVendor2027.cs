// Import explicitly pinned vendor STEP files into NEW native scenes only.
using System;using System.IO;using System.Linq;using System.Collections.Generic;
using System.Runtime.InteropServices;using System.Web.Script.Serialization;using interop.ICApiIronCAD;
namespace RockPro {public static class LatchInProcess {
static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=64000000};
static string Hash(string p){using(var s=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant();}
static double[] N(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
static IZDoc D(object x){return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));}
static object State(IZBaseApp a){return ((Array)a.GetAllOpenDocs()??new object[0]).Cast<object>().Select(x=>{var d=D(x);return new{path=d.Name,guid=d.FileGUID,modified=d.Modified};}).OrderBy(x=>x.path).ToArray();}
static void Walk(IZElement e,string path,List<object> rows){
 if(e.Type==eZElementType.Z_ELEMENT_PART){var p=(IZPart)e;var b=p.GetBody(true);var m=((IZSceneElement)e).GetTransformToGlobal();var matrix=new List<double>();for(int i=0;i<4;i++)for(int j=0;j<4;j++)matrix.Add(m.GetValue(i,j));rows.Add(new{id=e.Id,name=e.Name,path=path,bounds_local_m=b.GetBoundingBox(),faces=b.GetFacesCount(),matrix_m=matrix});return;}
 int count=e.GetChildrenCount();if(count==0)return;var a=e.GetChildrenZArray();for(int i=0;i<count;i++){object x;a.Get(i,out x);Walk((IZElement)x,path+"/"+((IZElement)x).Id,rows);}
}
public static int Run(string folder){var report=new Dictionary<string,object>();IZDoc owned=null;IZBaseApp app=null;object before=null;bool passed=false;
 try{
  var req=(Dictionary<string,object>)J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json")));
  if((string)req["contract"]!="rockpro-requested-vendor-import-v1"||System.Diagnostics.Process.GetCurrentProcess().Id!=Convert.ToInt32(req["expected_pid"]))throw new Exception("Wrong request/host");
  dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");app=(IZBaseApp)legacy.ZIronCADApp;if(!app.ApiVersion.StartsWith("29."))throw new Exception("2027 required");before=State(app);report["before"]=before;var outputs=new List<object>();
  foreach(object raw in (object[])req["models"]){var r=(Dictionary<string,object>)raw;string input=(string)r["file"],hash=(string)r["sha256"],key=(string)r["key"];
   if(Hash(input)!=hash)throw new Exception("Vendor file changed");owned=app.OpenNewDoc(eZDocType.Z_SCENE,false,true,"");var scene=(IZSceneDoc)owned;
   var node=scene.ImportModel(input,false);if(node==null)throw new Exception("Import failed");var rows=new List<object>();Walk(node,"root",rows);if(rows.Count==0)throw new Exception("Empty imported model");
   string output=Path.Combine(folder,key+".ics");scene.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);owned.Close();owned=null;bool already;
   owned=app.OpenFile2(output,false,false,out already);if(already){owned=null;throw new Exception("Reopen ownership failed");}scene=(IZSceneDoc)owned;
   var reopened=new List<object>();Walk(scene.GetTopElement(),"root",reopened);if(rows.Count!=reopened.Count||reopened.Any(x=>Convert.ToInt32(x.GetType().GetProperty("faces").GetValue(x,null))==0))throw new Exception("Reopened vendor geometry differs");
   scene.AdjustCameraToFitShapeInRect(900,700);scene.ExportImage(Path.Combine(folder,key+".png"),eZImageFormat.Z_IMAGE_PNG,900,700,true);
   owned.Close2(true);owned=null;outputs.Add(new{key=key,input=input,input_sha256=hash,file=output,sha256=Hash(output),parts=reopened});
  }report["outputs"]=outputs;passed=true;
 }catch(Exception e){report["error"]=e.ToString();}
 finally{if(owned!=null)try{owned.Close2(true);}catch(Exception e){report["cleanup_error"]=e.ToString();passed=false;}if(app!=null&&before!=null){report["after"]=State(app);report["existing_documents_preserved"]=J.Serialize(before)==J.Serialize(report["after"]);if(!(bool)report["existing_documents_preserved"])passed=false;}report["passed"]=passed;File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(report));}
 return passed?0:1;
}
}}
