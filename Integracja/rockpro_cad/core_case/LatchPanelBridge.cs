// Latch POC panel producer. Hidden documents; no application launch or activation.
// Python measures the final case after save/reopen; this helper closes its own scene.
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

internal static class LatchPanelBridge
{
    [DllImport("ole32.dll")] static extern int GetRunningObjectTable(int reserved,out IRunningObjectTable table);
    [DllImport("ole32.dll")] static extern int CreateBindCtx(int reserved,out IBindCtx context);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow(); // Getter only.
    static readonly JavaScriptSerializer Json=new JavaScriptSerializer { MaxJsonLength=16000000 };
    static IZBaseApp App; static string Folder; static int Counter; static IZDoc Owned;
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
        return Path.GetFullPath(p);
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
        string prefix=Path.Combine(Folder,"guard-"+(++Counter).ToString("D3")+"-"+label);
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
    [STAThread] static int Main(string[] args) {
        if(args.Length!=2)return 2;
        try {
            Folder=Path.GetDirectoryName(Full(args[1]));var input=Obj(Json.DeserializeObject(File.ReadAllText(args[0])));
            if(input.Count!=3||!input.ContainsKey("source")||!input.ContainsKey("output")||!input.ContainsKey("parts"))throw new ArgumentException("Unexpected fields");
            string source=Full(input["source"]),output=Full(input["output"]);
            if(!File.Exists(source)||File.Exists(output)||Same(source,output))throw new ArgumentException("Source/output guard");
            dynamic legacy=Existing(source);App=(IZBaseApp)legacy.Application.ZIronCADApp;
            IZDoc context=App.GetOpenDocByName(source);string guid=context.FileGUID;bool modified=context.Modified;
            if(!Same(context.Name,source))throw new InvalidOperationException("Context identity mismatch");
            object[] parts=Arr(input["parts"]);
            if(parts.Length<1||parts.Length>10)throw new ArgumentException("One to ten explicit POC panels required");
            HashSet<string> preflightIds=new HashSet<string>();
            foreach(object item in parts) {
                var p=Obj(item);object[] box=Arr(p["local_bounds"]);
                string id=Convert.ToString(p["id"]);
                if(String.IsNullOrEmpty(id)||id.Length>160||!preflightIds.Add(id))throw new ArgumentException("Unique panel ID required");
                if(box.Length!=2||Arr(box[0]).Length!=3||Arr(box[1]).Length!=3||Arr(p["native_matrix_mm"]).Length!=4)throw new ArgumentException("Panel geometry schema");
                for(int j=0;j<3;j++)if(Num(Arr(box[1])[j])<=Num(Arr(box[0])[j]))throw new ArgumentException("Invalid panel box");
                foreach(object row in Arr(p["native_matrix_mm"])) { if(Arr(row).Length!=4)throw new ArgumentException("Matrix4x4");foreach(object v in Arr(row))Num(v); }
            }
            IZDoc created=Guard("create-hidden",()=>{ Owned=App.CreateNewDoc(eZDocType.Z_SCENE,false,true,"",false);return Owned; });
            IZSceneDoc scene=(IZSceneDoc)created;
            HashSet<string> ids=new HashSet<string>();
            foreach(object item in parts) {
                var p=Obj(item);string id=Convert.ToString(p["id"]);
                if(String.IsNullOrEmpty(id)||id.Length>160||!ids.Add(id))throw new ArgumentException("Unique panel ID required");
                object[] b=Arr(p["local_bounds"]);object[] lo=Arr(b[0]),hi=Arr(b[1]);double[] minimum=new double[3],maximum=new double[3];
                for(int j=0;j<3;j++) { minimum[j]=Num(lo[j])*.001;maximum[j]=Num(hi[j])*.001;if(maximum[j]<=minimum[j])throw new ArgumentException("Invalid panel box"); }
                IZProfile profile=Guard("profile",()=>scene.CreateProfile());
                double[][] corners={new[]{minimum[0],minimum[1]},new[]{maximum[0],minimum[1]},new[]{maximum[0],maximum[1]},new[]{minimum[0],maximum[1]}};
                for(int edge=0;edge<4;edge++) { int k=edge;Guard("profile-line",()=>{profile.CreateLine(corners[k],corners[(k+1)%4],k+1);}); }
                IZPart part=Guard("part",()=>scene.CreatePart());
                ZExtrudeFeature extrusion=Guard("extrude",()=>((IZPartFeatureMgr)part).CreateExtrudeFeature(eZOperationType.Z_UNITE,false,maximum[2]-minimum[2],0,0,profile,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB));
                IZSceneElement feature=(IZSceneElement)extrusion;ZMathMatrix featureMatrix=feature.GetTransformToParent();featureMatrix.SetValue(3,2,minimum[2]);
                Guard("feature-pose",()=>feature.SetTransformToParent(featureMatrix));
                IZElement element=(IZElement)part;Guard("name",()=>{element.Name="RP:"+id;});
                Guard("description",()=>{part.BOMDescription="RECTANGULAR PANEL PROXY; latch POC only";});
                IZSceneElement se=(IZSceneElement)element;ZMathMatrix m=se.GetTransformToParent();object[] matrix=Arr(p["native_matrix_mm"]);
                for(int i=0;i<4;i++)for(int j=0;j<4;j++)m.SetValue(i,j,Num(Arr(matrix[i])[j])*(i==3&&j<3?.001:1));
                Guard("panel-pose",()=>se.SetTransformToParent(m));Guard("part-update",()=>part.Update());
                Guard("graphics-dirty",()=>element.SetDirtyFlag(eZDirtyFlag.Z_DIRTY_GRAPHICS));
            }
            // Hidden scenes have no renderer: UpdateGraphics returns E_FAIL.
            // Keep graphics dirty for the user's future visible open; this run
            // proves BRep/poses/persistence only, never visual QA.
            Guard("scene-update",()=>scene.Update());
            object[] before=Guard("measure-before",()=>Measure(scene));
            Guard("save",()=>scene.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false));
            if(!Same(created.Name,output)||created.Modified)throw new InvalidOperationException("Saved scene not clean");
            if(!Same(context.Name,source)||context.FileGUID!=guid||context.Modified!=modified)throw new InvalidOperationException("Context changed");
            WriteOnce(args[1],new Dictionary<string,object>{{"passed",true},{"before",before},{"background_guard",true},{"no_redraw_or_activation",true}});
            Console.WriteLine("Hidden panel producer PASS "+parts.Length);return 0;
        } catch(Exception e) { Console.Error.WriteLine(e);return 1; }
        finally {
            if(Owned!=null) {
                try {
                    long fg=GetForegroundWindow().ToInt64();string backup=null;
                    if(Owned.Modified) {
                        backup=Path.Combine(Folder,"panel_cleanup_"+Guid.NewGuid().ToString("N")+".ics");
                        ((IZSceneDoc)Owned).SaveAs(backup,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
                    }
                    if(Owned.Modified)throw new InvalidOperationException("Owned panel scene remains modified");
                    string path=Owned.Name;Owned.Close();Owned=null;
                    long after=GetForegroundWindow().ToInt64();
                    WriteOnce(Path.Combine(Folder,"panel_cleanup.json"),new {closed_path=path,backup_path=backup,foreground_before=fg,foreground_after=after,passed=fg==after});
                    if(fg!=after)throw new InvalidOperationException("Foreground changed during owned cleanup");
                } catch(Exception e) { Console.Error.WriteLine("CLEANUP FAILURE: "+e);Environment.ExitCode=1; }
            }
        }
    }
}
