// Fixed in-process latch POC. Hidden owned documents; no application launch or activation.
// In-process whole-component measurement/save/reopen; closes only owned scenes.
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using IRunningObjectTable = System.Runtime.InteropServices.ComTypes.IRunningObjectTable;
using IBindCtx = System.Runtime.InteropServices.ComTypes.IBindCtx;
using IEnumMoniker = System.Runtime.InteropServices.ComTypes.IEnumMoniker;
using IMoniker = System.Runtime.InteropServices.ComTypes.IMoniker;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;

namespace RockPro { public static class LatchInProcess
{
    [DllImport("ole32.dll")] static extern int GetRunningObjectTable(int reserved,out IRunningObjectTable table);
    [DllImport("ole32.dll")] static extern int CreateBindCtx(int reserved,out IBindCtx context);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint pid);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow(); // Getter only.
    static readonly JavaScriptSerializer Json=new JavaScriptSerializer { MaxJsonLength=16000000 };
    static IZBaseApp App; static string Folder; static string Phase; static int Counter; static readonly List<IZDoc> Owned=new List<IZDoc>();
    static Dictionary<string,object> Obj(object x) { return (Dictionary<string,object>)x; }
    static object[] Arr(object x) { return (object[])x; }
    static double Num(object x) {
        if(x is bool) throw new ArgumentException("Boolean is not numeric");
        double n=Convert.ToDouble(x,System.Globalization.CultureInfo.InvariantCulture);
        if(Double.IsNaN(n)||Double.IsInfinity(n)||Math.Abs(n)>100000) throw new ArgumentException("Invalid number");
        return n;
    }
    static string Full(object x) {
        string p=Convert.ToString(x);if(!Path.IsPathRooted(p)) throw new ArgumentException("Absolute path required");
        return Path.GetFullPath(p).TrimEnd(Path.DirectorySeparatorChar);
    }
    static bool Same(string a,string b) { return String.Equals(Full(a),Full(b),StringComparison.OrdinalIgnoreCase); }
    static void WriteOnce(string path,object value) {
        byte[] data=System.Text.Encoding.UTF8.GetBytes(Json.Serialize(value));
        using(FileStream stream=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read)) { stream.Write(data,0,data.Length);stream.Flush(true); }
    }
    static object Existing(string source) {
        IRunningObjectTable rot;IBindCtx context;
        Marshal.ThrowExceptionForHR(GetRunningObjectTable(0,out rot));Marshal.ThrowExceptionForHR(CreateBindCtx(0,out context));
        IEnumMoniker iterator;rot.EnumRunning(out iterator);IMoniker[] moniker=new IMoniker[1];
        while(iterator.Next(1,moniker,IntPtr.Zero)==0) {
            string name;try { moniker[0].GetDisplayName(context,null,out name); } catch(COMException) { continue; }
            if(!Path.IsPathRooted(name)||!Same(name,source)) continue;
            object value;rot.GetObject(moniker[0],out value);return value;
        }
        throw new InvalidOperationException("Expected existing ROT context; no launch or file activation");
    }
    static string State() {
        IZDoc active=App.ActiveDoc;
        return Json.Serialize(new Dictionary<string,object>{{"foreground_hwnd",GetForegroundWindow().ToInt64()},
            {"active_path",active==null?null:active.Name},{"active_guid",active==null?null:active.FileGUID},{"active_modified",active==null?false:active.Modified}});
    }
    static T Guard<T>(string label,Func<T> action) {
        string prefix=Path.Combine(Folder,Phase+"-guard-"+(++Counter).ToString("D3")+"-"+label);
        string before=State();WriteOnce(prefix+".before.json",Json.DeserializeObject(before));
        try { return action(); }
        finally {
            string after=State();WriteOnce(prefix+".after.json",Json.DeserializeObject(after));
            if(before!=after) throw new InvalidOperationException("Background identity/foreground changed: "+label);
        }
    }
    static void Guard(string label,Action action) { Guard<int>(label,delegate { action();return 0; }); }
    static double[][] Matrix(IZSceneElement element) {
        IZMathMatrix m=element.GetTransformToGlobal();double[][] result=new double[4][];
        for(int i=0;i<4;i++) { result[i]=new double[4];for(int j=0;j<4;j++) result[i][j]=m.GetValue(i,j)*(i==3&&j<3?1000:1); }
        return result;
    }
    static object[] Measure(IZSceneDoc scene) {
        IZElement root=scene.GetTopElement();IZArray array=root.GetChildrenZArray();List<object> rows=new List<object>();
        for(int index=0;index<root.GetChildrenCount();index++) {
            object raw;array.Get(index,out raw);IZElement e=(IZElement)raw;Array box=(Array)((IZPart)e).GetBoundingBox(true);
            double[] bounds=new double[6];for(int j=0;j<6;j++) bounds[j]=Convert.ToDouble(box.GetValue(j))*1000;
            rows.Add(new Dictionary<string,object>{{"id",e.Id},{"name",e.Name},{"matrix_world_mm",Matrix((IZSceneElement)e)},{"local_bounds_mm",bounds}});
        }
        return rows.ToArray();
    }
    static string Hash(string path) { using(var s=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant(); }
    const string SourceSHA="e3a1fa951ff6214abf34a4ec2b9dbceb039a06c37311b8dc1d2ea540b3e083a1";
    static IZDoc OpenOwned(string path,bool ro) {
        return Guard("open-hidden",()=>{bool already;IZDoc d=App.OpenFile2(path,ro,false,out already);if(already)throw new Exception("Already-open doc is not owned");Owned.Add(d);if(ro)WriteOnce(Path.Combine(Folder,"opened_source_identity.json"),new{path=d.Name,guid=d.FileGUID,sdk_readonly=d.IsReadOnly(),os_readonly=(File.GetAttributes(path)&FileAttributes.ReadOnly)!=0,modified=d.Modified,sha256=Hash(path)});if(!Same(d.Name,path))throw new Exception("Opened identity differs");return d;});
    }
    static void CloseOwned(IZDoc doc) { Guard("close-owned",()=>{if(doc.Modified)throw new Exception("Normal close requires clean owned document");doc.Close();Owned.Remove(doc);}); }
    static double[][] MatrixParent(IZSceneElement e) {
        IZMathMatrix m=e.GetTransformToParent();double[][] r=new double[4][];
        for(int i=0;i<4;i++){r[i]=new double[4];for(int j=0;j<4;j++)r[i][j]=m.GetValue(i,j)*(i==3&&j<3?1000:1);}return r;
    }
    static void SetMatrix(IZElement e,object value) {
        object[] rows=Arr(value);IZSceneElement se=(IZSceneElement)e;ZMathMatrix m=se.GetTransformToParent();
        for(int i=0;i<4;i++)for(int j=0;j<4;j++)m.SetValue(i,j,Num(Arr(rows[i])[j])*(i==3&&j<3?.001:1));
        Guard("place-whole",()=>se.SetTransformToParent(m));
    }
    static Dictionary<string,object> Whole(IZElement e) {
        Array box;string kind;try {box=(Array)((IZAssembly)e).GetBoundingBox(true);kind="assembly";}
        catch(InvalidCastException){box=(Array)((IZPart)e).GetBoundingBox(true);kind="part";}
        double[] b=new double[6];for(int i=0;i<6;i++)b[i]=Convert.ToDouble(box.GetValue(i))*1000;
        return new Dictionary<string,object>{{"native_id",e.Id},{"name",e.Name},{"kind",kind},{"children_count",e.GetChildrenCount()},
            {"matrix_world_mm",Matrix((IZSceneElement)e)},{"matrix_parent_mm",MatrixParent((IZSceneElement)e)},{"local_bounds_mm",b}};
    }
    static IZElement Child(IZElement e,int index){object raw;e.GetChildrenZArray().Get(index,out raw);return (IZElement)raw;}
    static void CheckCancel(){if(File.Exists(Path.Combine(Folder,"cancel.marker")))throw new OperationCanceledException("Cancelled at safe boundary");}
    static void Source(Dictionary<string,object> request) {
        string path=Full(request["source_copy"]);if(Hash(path)!=SourceSHA)throw new Exception("Source copy hash differs");
        IZDoc d=OpenOwned(path,true);WriteOnce(Path.Combine(Folder,"source_identity.json"),new{path=d.Name,guid=d.FileGUID,readonly_flag=d.IsReadOnly(),modified=d.Modified,sha256=Hash(path)});if(Guid.Parse(d.FileGUID)!=Guid.Parse("{D6ECD56D-7836-4796-B64A-C63C0699FF96}")||d.Modified)throw new Exception("Read-only source GUID/flags differ");
        List<object> rows=new List<object>();int[] ids={12631,12630,12782,12781};string[] roles={"lid","base","lid","base"},sides={"left","left","right","right"};
        for(int i=0;i<4;i++) {
            CheckCancel();int id=ids[i];IZElement e=(IZElement)((IZSceneDocUtility)d).GetElementById(id);
            var row=Guard("read-whole-root",()=>Whole(e));if(e.Id!=id||(string)row["kind"]!="assembly"||e.Name!=(roles[i]=="lid"?"17251S_1":"17251S"))throw new Exception("Pinned latch root differs");
            row["id"]=id;row["role"]=roles[i];row["side"]=sides[i];string asset=Path.Combine(Folder,"latch_"+id+".ics");
            Guard("export-whole-root",()=>((IZAssembly)e).SaveAs(asset,false));row["asset_path"]=asset;row["asset_sha256"]=Hash(asset);rows.Add(row);
        }
        if(d.Modified||Hash(path)!=SourceSHA||Guid.Parse(d.FileGUID)!=Guid.Parse("{D6ECD56D-7836-4796-B64A-C63C0699FF96}"))throw new Exception("Read/export changed source");WriteOnce(Path.Combine(Folder,"source_identity_after.json"),new{path=d.Name,guid=d.FileGUID,sdk_readonly=d.IsReadOnly(),os_readonly=(File.GetAttributes(path)&FileAttributes.ReadOnly)!=0,source_access_scope="owned getter-only clone; SDK read-only not claimed",modified=d.Modified,sha256=Hash(path)});CloseOwned(d);
        object handleReference=null;
        if(request.ContainsKey("handle_asset")){var h=Obj(request["handle_asset"]);string asset=Full(h["path"]);if(Hash(asset)!=(string)h["sha256"])throw new Exception("H7159 getter-copy hash differs");
            IZDoc hd=OpenOwned(asset,false);IZElement root=((IZSceneDoc)hd).GetTopElement();if(root.Name!="H7159"){if(root.GetChildrenCount()!=1)throw new Exception("H7159 asset root ambiguous");root=Child(root,0);}
            if(root.Name!="H7159"||root.GetChildrenCount()!=13)throw new Exception("Expected known whole H7159 asset");handleReference=Whole(root);
            if(hd.Modified||Hash(asset)!=(string)h["sha256"])throw new Exception("H7159 getter-copy changed");CloseOwned(hd);}
        WriteOnce(Path.Combine(Folder,"source_result.json"),new{passed=true,rows=rows,source_sha256=SourceSHA,handle_reference=handleReference});
    }
    static void Panels(IZSceneDoc scene,object[] parts) {
        if(parts.Length!=10)throw new Exception("Exactly10 panel proxies required");
        foreach(object item in parts){var p=Obj(item);object[] box=Arr(p["local_bounds"]),lo=Arr(box[0]),hi=Arr(box[1]);double[] low=new double[3],high=new double[3];
            for(int j=0;j<3;j++){low[j]=Num(lo[j])*.001;high[j]=Num(hi[j])*.001;if(high[j]<=low[j])throw new Exception("Invalid panel box");}
            IZProfile profile=Guard("profile",()=>scene.CreateProfile());double[][] corners={new[]{low[0],low[1]},new[]{high[0],low[1]},new[]{high[0],high[1]},new[]{low[0],high[1]}};
            for(int j=0;j<4;j++){int k=j;Guard("profile-line",()=>{profile.CreateLine(corners[k],corners[(k+1)%4],k+1);});}
            IZPart part=Guard("panel",()=>scene.CreatePart());ZExtrudeFeature ext=Guard("extrude",()=>((IZPartFeatureMgr)part).CreateExtrudeFeature(eZOperationType.Z_UNITE,false,high[2]-low[2],0,0,profile,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB));
            IZSceneElement f=(IZSceneElement)ext;ZMathMatrix fm=f.GetTransformToParent();fm.SetValue(3,2,low[2]);Guard("extrude-pose",()=>f.SetTransformToParent(fm));
            IZElement e=(IZElement)part;Guard("panel-name",()=>{e.Name="RP:"+Convert.ToString(p["id"]);part.BOMDescription="RECTANGULAR PANEL PROXY; latch POC only";});
            SetMatrix(e,p["native_matrix_mm"]);Guard("panel-update",()=>part.Update());Guard("panel-dirty",()=>e.SetDirtyFlag(eZDirtyFlag.Z_DIRTY_GRAPHICS));
        }
    }
    static Dictionary<string,object> ReadCase(IZSceneDoc scene,Dictionary<int,int> cornerMap,Dictionary<int,int> latchMap,Dictionary<string,int> handleMap,object[] cornerRows) {
        IZElement root=scene.GetTopElement();if(root.GetChildrenCount()!=16+handleMap.Count)throw new Exception("Whole-root inventory differs");
        List<object> panels=new List<object>(),corners=new List<object>(),latches=new List<object>();var util=(IZSceneDocUtility)scene;
        for(int i=0;i<16+handleMap.Count;i++){IZElement e=Child(root,i);if(e.Name.StartsWith("RP:panels-"))panels.Add(Whole(e));}
        foreach(var map in cornerMap){IZElement parent=(IZElement)util.GetElementById(map.Value);if(parent.GetChildrenCount()!=4||parent.Name!="410429")throw new Exception("Corner container changed");
            foreach(object v in cornerRows){var r=Obj(v);if(Convert.ToInt32(r["assembly_id"])!=map.Key)continue;object[] path=Arr(r["occurrence_path"]);var row=Whole(Child(parent,Convert.ToInt32(path[path.Length-1])));row["source_id"]=r["id"];corners.Add(row);}}
        foreach(var map in latchMap){var row=Whole((IZElement)util.GetElementById(map.Value));row["source_id"]=map.Key;latches.Add(row);}
        if(panels.Count!=10||corners.Count!=8||latches.Count!=4)throw new Exception("Family count differs");
        var handles=new List<object>();foreach(var map in handleMap){var h=Whole((IZElement)util.GetElementById(map.Value));h["occurrence_id"]=map.Key;handles.Add(h);}
        return new Dictionary<string,object>{{"panels",panels},{"corners",corners},{"latches",latches},{"handles",handles},{"top_level_roots",16+handleMap.Count}};
    }
    static void Execute(Dictionary<string,object> request) {
        object[] cases=Arr(request["cases"]);if(cases.Length<1||cases.Length>2)throw new Exception("One case or A/B required");
        foreach(object item in cases){CheckCancel();var c=Obj(item);string output=Full(c["output"]);if(File.Exists(output)||!Same(Path.GetDirectoryName(output),Folder))throw new Exception("New owned output required");
            IZDoc d=Guard("create-hidden",()=>{IZDoc x=App.CreateNewDoc(eZDocType.Z_SCENE,false,true,"",false);Owned.Add(x);return x;});IZSceneDoc scene=(IZSceneDoc)d;Panels(scene,Arr(c["panels"]));IZAssembly top=(IZAssembly)scene.GetTopElement();
            var cornerMap=new Dictionary<int,int>();var latchMap=new Dictionary<int,int>();var handleMap=new Dictionary<string,int>();object[] cornerRows=Arr(c["corners"]);
            foreach(object v in Arr(c["corner_assets"])){var a=Obj(v);string path=Full(a["asset_path"]);if(Hash(path)!=(string)a["asset_sha256"])throw new Exception("Corner asset hash differs");
                IZElement e=Guard("import-corners",()=>(IZElement)top.AddChildFromExternalFile(path,false));int id=Convert.ToInt32(a["source_id"]);cornerMap[id]=e.Id;SetMatrix(e,a["matrix_world_mm"]);
                foreach(object r in cornerRows){var row=Obj(r);if(Convert.ToInt32(row["assembly_id"])!=id)continue;object[] p=Arr(row["occurrence_path"]);IZElement child=Child(e,Convert.ToInt32(p[p.Length-1]));SetMatrix(child,row["matrix_parent_mm"]);Guard("corner-update",()=>((IZPart)child).Update());Guard("corner-dirty",()=>child.SetDirtyFlag(eZDirtyFlag.Z_DIRTY_GRAPHICS));}Guard("corner-root-update",()=>((IZAssembly)e).Update());}
            foreach(object v in Arr(c["latches"])){var a=Obj(v);string path=Full(a["asset_path"]);if(Hash(path)!=(string)a["asset_sha256"])throw new Exception("Latch asset hash differs");
                IZElement e=Guard("import-latch",()=>(IZElement)top.AddChildFromExternalFile(path,false));latchMap[Convert.ToInt32(a["id"])]=e.Id;SetMatrix(e,a["matrix_world_mm"]);Guard("latch-update",()=>((IZAssembly)e).Update());Guard("latch-dirty",()=>e.SetDirtyFlag(eZDirtyFlag.Z_DIRTY_GRAPHICS));}
            if(c.ContainsKey("handles"))foreach(object v in Arr(c["handles"])){var h=Obj(v);string path=Full(h["asset_path"]);if(Hash(path)!=(string)h["asset_sha256"])throw new Exception("H7159 asset hash differs");
                IZElement e=Guard("import-whole-H7159",()=>(IZElement)top.AddChildFromExternalFile(path,false));if(e.Name!="H7159"||e.GetChildrenCount()!=13)throw new Exception("H7159 whole assembly identity differs");
                handleMap[(string)h["id"]]=e.Id;SetMatrix(e,h["matrix_world_mm"]);
                for(int i=0;i<13;i++){IZElement child=Child(e,i);Guard("H7159-child-update",()=>((IZPart)child).Update());Guard("H7159-child-dirty",()=>child.SetDirtyFlag(eZDirtyFlag.Z_DIRTY_GRAPHICS));}
                Guard("H7159-update",()=>((IZAssembly)e).Update());Guard("H7159-dirty",()=>e.SetDirtyFlag(eZDirtyFlag.Z_DIRTY_GRAPHICS));}
            Guard("scene-update",()=>scene.Update());string label=(string)c["label"];WriteOnce(Path.Combine(Folder,label+"_before.json"),ReadCase(scene,cornerMap,latchMap,handleMap,cornerRows));
            Guard("save-case",()=>scene.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false));CloseOwned(d);d=OpenOwned(output,false);
            WriteOnce(Path.Combine(Folder,label+"_after.json"),ReadCase((IZSceneDoc)d,cornerMap,latchMap,handleMap,cornerRows));CloseOwned(d);
            WriteOnce(Path.Combine(Folder,label+"_saved.json"),new{output_path=output,output_sha256=Hash(output),corner_map=MapRows(cornerMap),latch_map=MapRows(latchMap)});
        }
    }
    static object[] MapRows(Dictionary<int,int> map){var rows=new List<object>();foreach(var pair in map)rows.Add(new{source_id=pair.Key,native_id=pair.Value});return rows.ToArray();}

    public static int Run(string folder) {
        Folder=Path.GetFullPath(folder).TrimEnd(Path.DirectorySeparatorChar);Counter=0;
        string phase=File.Exists(Path.Combine(Folder,"execute_request.json"))?"execute":"source";Phase=phase;
        string error=null,before=null,source=null,after=null,sourceAfter=null,version=null;bool passed=false,contextWasDirty=false;List<object> cleanup=new List<object>();
        try {
            CheckCancel();
            var request=Obj(Json.DeserializeObject(File.ReadAllText(Path.Combine(Folder,phase+"_request.json"))));
            int expected=Convert.ToInt32(request["expected_pid"]),current=System.Diagnostics.Process.GetCurrentProcess().Id;
            if(expected!=current)throw new Exception("Executing hostPID differs");
            dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");uint legacyPid;
            GetWindowThreadProcessId(new IntPtr(Convert.ToInt64(legacy.HWnd)),out legacyPid);
            if(legacyPid!=current)throw new Exception("Global legacy object belongs to another host; no API cast performed");
            App=(IZBaseApp)legacy.ZIronCADApp;before=State();version=App.ApiVersion;
            source=Full(request["original_source"]);string context=Convert.ToString(request["context"]);
            if(Hash(source)!=SourceSHA)throw new Exception("Original sourcehash differs");
            object allow;bool allowDirty=request.TryGetValue("allow_dirty_context",out allow)&&allow is bool&&(bool)allow;
            IZDoc user;if(context.Length==0){if(!allowDirty)throw new Exception("Unsaved active context requires explicit preserve flag");user=App.ActiveDoc;if(user==null)throw new Exception("Active document required");}
            else{context=Full(context);user=App.GetOpenDocByName(context);if(user==null||!Same(user.Name,context))throw new Exception("Exact existing context required");}
            contextWasDirty=user.Modified;if(contextWasDirty&&!allowDirty)throw new Exception("Dirty context requires explicit preserve flag");
            CheckCancel();if(phase=="source")Source(request);else Execute(request);CheckCancel();
            passed=true;
        }catch(Exception e){error=e.ToString();}
        finally {
            foreach(IZDoc d in new List<IZDoc>(Owned)){
                try {string backup=null;if(d.Modified){backup=Path.Combine(Folder,"preserved_owned_"+Guid.NewGuid().ToString("N")+".ics");((IZSceneDoc)d).SaveAs(backup,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);}
                    if(d.Modified)throw new Exception("Owned doc remains dirty");string path=d.Name;d.Close();Owned.Remove(d);cleanup.Add(new{closed_path=path,backup_path=backup});
                }catch(Exception e){passed=false;error=(error??"")+" CLEANUP: "+e;}
            }
            try {after=App==null?null:State();if(before==null||before!=after)passed=false;}catch(Exception e){passed=false;error=(error??"")+" STATE: "+e;}
            try {sourceAfter=source==null?null:Hash(source);if(sourceAfter!=SourceSHA)passed=false;}catch(Exception e){passed=false;error=(error??"")+" SOURCEHASH: "+e;}
            WriteOnce(Path.Combine(Folder,phase+"_receipt.json"),new{passed=passed,error=error,before=before,after=after,source_sha256_after=sourceAfter,cleanup=cleanup,remaining_owned=Owned.Count,user_context_already_modified=contextWasDirty,context_memory_disk_equivalence="not claimed; user context unchanged",process_id=System.Diagnostics.Process.GetCurrentProcess().Id,api_version=version});
        }
        return passed?0:1;
    }
}}
