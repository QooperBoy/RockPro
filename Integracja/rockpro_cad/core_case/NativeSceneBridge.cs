// Fixed native prototype bridge using the installed IronCAD 2027 SDK.
// No registration, arbitrary calls, scripting or ActiveDoc fallback.
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using RunningTable = System.Runtime.InteropServices.ComTypes.IRunningObjectTable;
using BindContext = System.Runtime.InteropServices.ComTypes.IBindCtx;
using MonikerEnumerator = System.Runtime.InteropServices.ComTypes.IEnumMoniker;
using Moniker = System.Runtime.InteropServices.ComTypes.IMoniker;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;

internal static class NativeSceneBridge
{
    [DllImport("ole32.dll")] static extern int GetRunningObjectTable(int reserved, out RunningTable table);
    [DllImport("ole32.dll")] static extern int CreateBindCtx(int reserved, out BindContext context);
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 16000000 };
    static Dictionary<string, object> Obj(object value) { return (Dictionary<string, object>)value; }
    static object[] Arr(object value) { return (object[])value; }
    static double Num(object value) {
        if (value is bool) throw new ArgumentException("Boolean is not numeric");
        double n = Convert.ToDouble(value, System.Globalization.CultureInfo.InvariantCulture);
        if (Double.IsNaN(n) || Double.IsInfinity(n) || Math.Abs(n)>100000) throw new ArgumentException("Invalid finite number");
        return n;
    }
    static double[] Vector(object value, double scale) {
        object[] input = Arr(value);
        if (input.Length != 3) throw new ArgumentException("Expected vector3");
        return new double[] { Num(input[0])*scale, Num(input[1])*scale, Num(input[2])*scale };
    }
    static string FullPath(object path) {
        string value = Convert.ToString(path);
        if (!Path.IsPathRooted(value)) throw new ArgumentException("Absolute path required");
        return Path.GetFullPath(value);
    }
    static bool Same(string a, string b) { return String.Equals(Path.GetFullPath(a), Path.GetFullPath(b), StringComparison.OrdinalIgnoreCase); }
    static object ExistingDocument(string source) {
        RunningTable rot; BindContext context;
        Marshal.ThrowExceptionForHR(GetRunningObjectTable(0,out rot));
        Marshal.ThrowExceptionForHR(CreateBindCtx(0,out context));
        MonikerEnumerator iterator; rot.EnumRunning(out iterator); Moniker[] moniker=new Moniker[1];
        while(iterator.Next(1,moniker,IntPtr.Zero)==0) {
            string name;
            try { moniker[0].GetDisplayName(context,null,out name); }
            catch(COMException) { continue; }
            if(!Path.IsPathRooted(name) || !Same(name,source)) continue;
            object existing; rot.GetObject(moniker[0],out existing); return existing;
        }
        throw new InvalidOperationException("Expected source is not already open in ROT; refusing file-moniker activation");
    }
    static Dictionary<string, object> Provenance(IZDoc doc) {
        return new Dictionary<string, object> { {"path", doc.Name}, {"file_guid", doc.FileGUID}, {"modified", doc.Modified} };
    }
    static void AssertSource(IZDoc doc, string path, string guid, bool modified) {
        if (!Same(doc.Name,path) || doc.FileGUID != guid || doc.Modified != modified)
            throw new InvalidOperationException("Source identity or Modified flag changed");
    }
    static double[][] Matrix(IZSceneElement element) {
        IZMathMatrix m = element.GetTransformToGlobal();
        double[][] result = new double[4][];
        for (int i=0;i<4;i++) {
            result[i] = new double[4];
            for (int j=0;j<4;j++) result[i][j] = m.GetValue(i,j)*(i==3 && j<3?1000.0:1.0);
        }
        return result;
    }
    static double[] Bounds(IZPart part, double[][] m) {
        Array raw = (Array)part.GetBoundingBox(true);
        if (raw.Length!=6) throw new InvalidOperationException("Native bbox unavailable");
        double[] b = new double[6];
        for(int i=0;i<6;i++) {
            b[i]=Convert.ToDouble(raw.GetValue(i))*1000.0;
            if(Double.IsNaN(b[i]) || Double.IsInfinity(b[i]) || Math.Abs(b[i])>=1e29)
                throw new InvalidOperationException("Native bbox invalid");
        }
        for(int axis=0;axis<3;axis++) if(b[axis+3]<=b[axis]) throw new InvalidOperationException("Native bbox reversed or degenerate");
        double[] result={Double.PositiveInfinity,Double.PositiveInfinity,Double.PositiveInfinity,
                         Double.NegativeInfinity,Double.NegativeInfinity,Double.NegativeInfinity};
        for(int corner=0;corner<8;corner++) for(int j=0;j<3;j++) {
            double x=m[3][j];
            for(int k=0;k<3;k++) x+=b[k+((corner&(1<<k))==0?0:3)]*m[k][j];
            result[j]=Math.Min(result[j],x); result[j+3]=Math.Max(result[j+3],x);
        }
        return result;
    }
    static object[] Measure(IZSceneDoc scene) {
        IZElement root=scene.GetTopElement(); IZArray array=root.GetChildrenZArray();
        List<object> rows = new List<object>(); HashSet<string> ids=new HashSet<string>();
        for(int index=0;index<root.GetChildrenCount();index++) {
            object raw; array.Get(index,out raw); IZElement e=(IZElement)raw;
            if(!e.Name.StartsWith("RP:") || !ids.Add(e.Name.Substring(3))) throw new InvalidOperationException("Unexpected or duplicate native stable ID");
            double[][] m=Matrix((IZSceneElement)e);
            rows.Add(new Dictionary<string,object>{{"occurrence_id",e.Name.Substring(3)}, {"cad_node_id",e.Id},
                {"matrix_world_mm",m},{"bbox_world_mm",Bounds((IZPart)e,m)}});
        }
        return rows.ToArray();
    }
    [STAThread]
    static int Main(string[] args) {
        if(args.Length!=2) return 2;
        try {
            var input=Obj(Json.DeserializeObject(File.ReadAllText(args[0])));
            if(input.Count!=3 || !input.ContainsKey("source") || !input.ContainsKey("output") || !input.ContainsKey("parts"))
                throw new ArgumentException("Unexpected bridge request fields");
            string source=FullPath(input["source"]), output=FullPath(input["output"]);
            if(!File.Exists(source) || !source.EndsWith(".ics",StringComparison.OrdinalIgnoreCase) || Same(source,output) || File.Exists(output))
                throw new InvalidOperationException("Source or destination guard failed");
            dynamic legacy=ExistingDocument(source);
            IZBaseApp app=(IZBaseApp)legacy.Application.ZIronCADApp;
            IZDoc original=app.GetOpenDocByName(source);
            string guid=original.FileGUID; bool modified=original.Modified;
            AssertSource(original,source,guid,modified);
            IZDoc created=app.OpenNewDoc(eZDocType.Z_SCENE,false,true,"");
            IZSceneDoc scene=(IZSceneDoc)created;
            object[] parts=Arr(input["parts"]);
            if(parts.Length<1 || parts.Length>1000) throw new ArgumentException("Bounded parts required");
            HashSet<string> ids=new HashSet<string>();
            foreach(object item in parts) {
                var p=Obj(item); string id=Convert.ToString(p["id"]);
                if(String.IsNullOrEmpty(id) || id.Length>160 || !ids.Add(id)) throw new ArgumentException("Unique IDs required");
                object[] bounds=Arr(p["local_bounds"]);
                double[] minimum=Vector(bounds[0],0.001), maximum=Vector(bounds[1],0.001);
                IZProfile profile=scene.CreateProfile();
                double[][] corners={new double[]{minimum[0],minimum[1]},new double[]{maximum[0],minimum[1]},
                    new double[]{maximum[0],maximum[1]},new double[]{minimum[0],maximum[1]}};
                for(int edge=0;edge<4;edge++) profile.CreateLine(corners[edge],corners[(edge+1)%4],edge+1);
                IZPart part=scene.CreatePart();
                ZExtrudeFeature extrusion=((IZPartFeatureMgr)part).CreateExtrudeFeature(eZOperationType.Z_UNITE,false,
                    maximum[2]-minimum[2],0,0,profile,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB);
                IZSceneElement feature=(IZSceneElement)extrusion;
                ZMathMatrix featureMatrix=feature.GetTransformToParent(); featureMatrix.SetValue(3,2,minimum[2]);
                feature.SetTransformToParent(featureMatrix); part.Update();
                IZElement element=(IZElement)part;
                element.Name="RP:"+id;
                part.BOMDescription="SYNTHETIC PROXY; not approved catalog geometry; "+Convert.ToString(p["family"]);
                IZSceneElement se=(IZSceneElement)element;
                ZMathMatrix m=se.GetTransformToParent(); object[] matrix=Arr(p["native_matrix_mm"]);
                for(int i=0;i<4;i++) for(int j=0;j<4;j++) {
                    object[] row=Arr(matrix[i]); double v=Num(row[j]);
                    m.SetValue(i,j,v*(i==3 && j<3?0.001:1.0));
                }
                se.SetTransformToParent(m);
            }
            scene.Update(); object[] before=Measure(scene);
            scene.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
            if(!Same(created.Name,output) || created.Modified) throw new InvalidOperationException("Saved output not clean");
            // Only this newly created clean document is closed.
            created.Close(); IZDoc reopened=app.OpenFile(output,false);
            if(!Same(reopened.Name,output)) throw new InvalidOperationException("Reopened wrong document");
            object[] after=Measure((IZSceneDoc)reopened);
            AssertSource(original,source,guid,modified);
            var result=new Dictionary<string,object>{{"passed",true},{"before",before},{"reopened",after},
                {"source",Provenance(original)},{"bridge","IronCAD 2027 official .NET SDK interop"}};
            File.WriteAllText(args[1],Json.Serialize(result));
            Console.WriteLine("Native bridge PASS: "+parts.Length+" proxy occurrences");
            // IronCAD marshals foreground COM helper threads into this client.
            // All writes and readback are complete; avoid waiting on RCW shutdown.
            Environment.Exit(0); return 0;
        } catch(Exception ex) {
            Console.Error.WriteLine(ex.ToString()); Environment.Exit(1); return 1;
        }
    }
}
