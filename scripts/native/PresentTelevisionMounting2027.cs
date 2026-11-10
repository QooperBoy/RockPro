// Presentation-only refinement on the exact generated R002 document.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;
namespace RockPro { public static class LatchInProcess {
    static readonly JavaScriptSerializer Json=new JavaScriptSerializer{MaxJsonLength=64000000};
    static Dictionary<string,object> O(object x){return (Dictionary<string,object>)x;}
    static IZDoc D(object x){return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));}
    static double[] Numbers(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
    static double[] Matrix(IZSceneElement e){var m=e.GetTransformToGlobal();return Enumerable.Range(0,16).Select(k=>m.GetValue(k/4,k%4)).ToArray();}
    public static int Run(string folder) {
        var report=new Dictionary<string,object>();bool passed=false;
        try {
            var q=O(Json.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));
            if(System.Diagnostics.Process.GetCurrentProcess().Id!=Convert.ToInt32(q["expected_pid"]))throw new Exception("Host changed");
            dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;
            if(!app.ApiVersion.StartsWith("29."))throw new Exception("IronCAD 2027 required");
            string output=(string)q["output"];
            var doc=((Array)app.GetAllOpenDocs()).Cast<object>().Select(D).Single(d=>String.Equals(d.Name,output,StringComparison.OrdinalIgnoreCase));
            var s=(IZSceneDoc)doc;var u=(IZSceneDocUtility)s;
            var aliases=O(q["aliases"]);var featureAliases=O(q["feature_aliases"]);
            Func<int,IZElement> element=id=>u.GetElementById(aliases.ContainsKey(id.ToString())?Convert.ToInt32(aliases[id.ToString()]):id);
            var matrices=new Dictionary<int,double[]>();var bounds=new Dictionary<int,double[]>();
            foreach(object raw in (object[])q["parts"]) {
                int id=Convert.ToInt32(O(raw)["id"]);var p=(IZPart)element(id);
                matrices[id]=Matrix((IZSceneElement)p);bounds[id]=Numbers(p.GetBody(true).GetBoundingBox());
            }
            var parameterExpressions=Enumerable.Range(0,s.ParameterMgr.Count).Select(i=>s.ParameterMgr.GetParameter(i)).ToDictionary(p=>p.Name,p=>p.Expression);
            if(parameterExpressions.Count!=34)throw new Exception("Expected 34 effective scene parameters");
            var names=((object[])q["names"]).Select(O).ToDictionary(n=>Convert.ToInt32(n["id"]),n=>(string)n["name"]);
            foreach(var pair in names)element(pair.Key).Name=pair.Value;
            foreach(object raw in (object[])q["operations"]) {
                var op=O(raw);var mgr=(IZPartFeatureMgr)element(Convert.ToInt32(op["part"]));
                int oldId=Convert.ToInt32(op["source_feature"]);IZFeature f=null;
                if(featureAliases.ContainsKey(oldId.ToString())) {
                    int wanted=Convert.ToInt32(featureAliases[oldId.ToString()]);
                    for(int i=0;i<mgr.GetFeaturesCount();i++)if(((IZElement)mgr.GetFeatureAt(i)).Id==wanted)f=mgr.GetFeatureAt(i);
                } else f=mgr.GetFeatureAt(Convert.ToInt32(op["feature_index"]));
                if(f==null)throw new Exception("Mapped cut missing");
                ((IZElement)f).Name="Wycięcie pod "+names[Convert.ToInt32(op["mount"])];
            }
            s.Update();double maximum=0;
            foreach(var pair in matrices) {
                var p=(IZPart)element(pair.Key);var actual=Matrix((IZSceneElement)p);
                var b=Numbers(p.GetBody(true).GetBoundingBox());
                for(int k=0;k<16;k++)maximum=Math.Max(maximum,Math.Abs(actual[k]-pair.Value[k])*1000);
                for(int k=0;k<6;k++)maximum=Math.Max(maximum,Math.Abs(b[k]-bounds[pair.Key][k])*1000);
            }
            if(maximum>.08)throw new Exception("Naming changed geometry");
            var parameters=Enumerable.Range(0,s.ParameterMgr.Count).Select(i=>s.ParameterMgr.GetParameter(i)).ToArray();
            foreach(var p in parameters)if(p.Expression!=parameterExpressions[p.Name])throw new Exception("Naming changed a parameter expression");
            var camera=(IZCamera)s.CameraMgr.ActiveCamera;camera.Perspective=false;camera.Up=new double[]{0,0,1};
            camera.Direction=new double[]{0,1,0};camera.Up=new double[]{0,0,1};s.AdjustCameraToFitShapeInRect(1800,1100);s.Redraw();
            s.ExportImage(Path.Combine(folder,"przod.png"),eZImageFormat.Z_IMAGE_PNG,1800,1100,true);
            camera.Direction=new double[]{.45,.8,-.5};camera.Up=new double[]{0,0,1};s.AdjustCameraToFitShapeInRect(1400,1100);s.Redraw();
            s.ExportImage(Path.Combine(folder,"final.png"),eZImageFormat.Z_IMAGE_PNG,1400,1100,true);
            s.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
            report["parameters"]=parameters.Select(p=>new{name=p.Name,expression=p.Expression,value_mm=p.Value*1000,notes=p.Notes}).ToArray();
            report["labels"]=names.Count;report["cuts_named"]=56;report["geometry_error_after_naming_mm"]=maximum;
            passed=true;
        }catch(Exception ex){report["error"]=ex.ToString();}
        report["passed"]=passed;File.WriteAllText(Path.Combine(folder,"result.json"),Json.Serialize(report));return passed?0:1;
    }
}}
