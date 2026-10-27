// Read-only kernel tessellation on an explicitly owned source copy. No regeneration.
using System;using System.IO;using System.Linq;using System.Collections.Generic;using System.Runtime.InteropServices;using System.Web.Script.Serialization;using interop.ICApiIronCAD;
namespace RockPro {public static class LatchInProcess {
static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=256000000};
[DllImport("ole32.dll")]static extern int GetRunningObjectTable(int reserved,out System.Runtime.InteropServices.ComTypes.IRunningObjectTable table);
[DllImport("ole32.dll")]static extern int CreateBindCtx(int reserved,out System.Runtime.InteropServices.ComTypes.IBindCtx context);
static object ExactContext(string path){System.Runtime.InteropServices.ComTypes.IRunningObjectTable rot;System.Runtime.InteropServices.ComTypes.IBindCtx bind;Marshal.ThrowExceptionForHR(GetRunningObjectTable(0,out rot));Marshal.ThrowExceptionForHR(CreateBindCtx(0,out bind));System.Runtime.InteropServices.ComTypes.IEnumMoniker it;rot.EnumRunning(out it);var item=new System.Runtime.InteropServices.ComTypes.IMoniker[1];while(it.Next(1,item,IntPtr.Zero)==0){string name;try{item[0].GetDisplayName(bind,null,out name);}catch(COMException){continue;}if(!Path.IsPathRooted(name)||!String.Equals(Path.GetFullPath(name),Path.GetFullPath(path),StringComparison.OrdinalIgnoreCase))continue;object value;rot.GetObject(item[0],out value);return value;}throw new Exception("Exact existing document context required");}
static string Hash(string p){using(var s=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant();}
static double[] Num(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
static object State(IZBaseApp app){return new{active=app.ActiveDoc==null?null:app.ActiveDoc.FileGUID,documents=((Array)app.GetAllOpenDocs()).Cast<object>().Select(x=>{var d=x as IZDoc;if(d==null)d=(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));return new{path=d.Name,guid=d.FileGUID,modified=d.Modified};}).OrderBy(x=>x.path).ToArray()};}
public static int Run(string folder){var result=new Dictionary<string,object>();var files=new List<object>();IZDoc owned=null,previous=null;IZBaseApp app=null;string before=null,source=null,sourceHash=null;bool passed=false;
try{
 var r=(Dictionary<string,object>)J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json")));
 if(System.Diagnostics.Process.GetCurrentProcess().Id!=Convert.ToInt32(r["expected_pid"]))throw new Exception("Wrong host PID");
 dynamic legacy=r.ContainsKey("context_path")?((dynamic)ExactContext((string)r["context_path"])).Application:Marshal.GetActiveObject("IronCAD.Application");app=(IZBaseApp)legacy.ZIronCADApp;if(!app.ApiVersion.StartsWith(Convert.ToString(r["expected_api_major"])+"."))throw new Exception("Wrong API version");previous=app.ActiveDoc;before=J.Serialize(State(app));
 source=(string)r["source"];sourceHash=(string)r["source_sha256"];if(Hash(source)!=sourceHash)throw new Exception("Source hash mismatch");
 string copy=Path.Combine(folder,"kernel-copy.ics");File.Copy(source,copy,false);bool already;owned=app.OpenFile2(copy,true,false,out already);if(already){owned=null;throw new Exception("Copy ownership refused");}
 var utility=(IZSceneDocUtility)owned;Directory.CreateDirectory(Path.Combine(folder,"meshes"));int sequence=0;
 foreach(var item in (object[])r["parts"]){
  if(File.Exists(Path.Combine(folder,"cancel")))throw new OperationCanceledException("Cancelled before next part");var spec=(Dictionary<string,object>)item;int id=Convert.ToInt32(spec["node_id"]),meshId=Convert.ToInt32(spec["mesh_id"]);var part=(IZPart)utility.GetElementById(id);var element=(IZElement)part;
  if(element.Name!=(string)spec["name"])throw new Exception("Part identity mismatch");
  object faceIdsRaw;var meshes=(Array)part.GetSpecifiedPolyMeshes(0.0001f,15f,10f,true,out faceIdsRaw);var faceIds=Num(faceIdsRaw);
  var vertices=new List<double>();var normals=new List<double>();var colors=new List<object>();var body=part.GetBody(true);var bounds=Num(body.GetBoundingBox());int partColor=part.SurfaceFinish.Color;uint partTriangles=0;
  for(int face=0;face<meshes.Length;face++){
   var mesh=(IZPolyMesh)meshes.GetValue(face);uint vertexCount,triCount;object coords,norms,vertexColors,uv,uvw,triangles;
   mesh.GetAllTriangulatedFacetInfo(out triCount);partTriangles+=triCount;if(partTriangles>2000000)throw new Exception("Preview triangle budget exceeded: "+id);mesh.GetAllVertexData(out vertexCount,out coords,out norms,out vertexColors,out uv,out uvw);mesh.GetAllTriangulatedFacetData(out triCount,out triangles);
   if(triCount==0)continue;var points=Num(coords);var indices=Num(triangles);if(points.Length!=vertexCount*3||indices.Length!=triCount*3)throw new Exception("Unsupported kernel mesh layout");
   int color=partColor;try{color=((IZBodyFace)body).GetSurfaceFinish((int)faceIds[face],true).Color;}catch(Exception){}
   int start=vertices.Count;
   for(int t=0;t<indices.Length;t+=3){var points3=new double[3][];
    for(int corner=0;corner<3;corner++){int at=checked((int)indices[t+corner])*3;points3[corner]=new[]{points[at],points[at+1],points[at+2]};}
    var a=points3[0];var b=points3[1];var c=points3[2];var u=new[]{b[0]-a[0],b[1]-a[1],b[2]-a[2]};var v=new[]{c[0]-a[0],c[1]-a[1],c[2]-a[2]};var normal=new[]{u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]};double length=Math.Sqrt(normal.Sum(x=>x*x));if(length<1e-20)continue;
    for(int corner=0;corner<3;corner++)for(int axis=0;axis<3;axis++){double value=points3[corner][axis];if(Double.IsNaN(value)||Double.IsInfinity(value)||value<bounds[axis]-.0003||value>bounds[axis+3]+.0003)throw new Exception("Kernel vertex outside native body bounds");vertices.Add(value);normals.Add(normal[axis]/length);}
   }
   if(vertices.Count>start)colors.Add(new{t=(vertices.Count-start)/3,c=(color&0xffffff).ToString("x6")});
  }
  if(vertices.Count==0)throw new Exception("Kernel returned empty part: "+id);
  var matrix=((IZSceneElement)part).GetTransformToGlobal();var transform=new List<double>();for(int i=0;i<4;i++)for(int k=0;k<4;k++)transform.Add(matrix.GetValue(i,k));
  string name=meshId+".json",path=Path.Combine(folder,"meshes",name);File.WriteAllText(path,J.Serialize(new{id=meshId,v=vertices,n=normals,p=transform,c=colors}));files.Add(new{file=name,node_id=id,sha256=Hash(path),triangles=vertices.Count/9});sequence++;
  File.WriteAllText(Path.Combine(folder,"progress.json"),J.Serialize(new{completed=sequence,total=((object[])r["parts"]).Length}));
 }
 owned.Close2(true);owned=null;if(Hash(copy)!=sourceHash)throw new Exception("Disk copy changed");passed=true;
}catch(Exception e){result["error"]=e.ToString();}
finally{
 if(owned!=null)try{owned.Close2(true);owned=null;}catch(Exception e){result["cleanup_error"]=e.ToString();passed=false;}
 if(app!=null&&before!=null){try{if(previous!=null)app.ActiveDoc=previous;result["context_preserved"]=J.Serialize(State(app))==before;if(!(bool)result["context_preserved"])passed=false;}catch(Exception e){result["context_error"]=e.ToString();passed=false;}}
 result["source_unchanged"]=source!=null&&Hash(source)==sourceHash;if(!(bool)result["source_unchanged"])passed=false;
 result["passed"]=passed;result["source_sha256"]=sourceHash;result["files"]=files;result["saved"]=false;result["method"]="ICAPI.GetSpecifiedPolyMeshes";result["normal_deviation_degrees"]=15;result["surface_deviation_m"]=0.0001;result["remaining_owned"]=owned==null?0:1;File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(result));
}return passed?0:1;
}}}
