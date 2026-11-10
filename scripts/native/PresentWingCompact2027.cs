// Metadata refinement on the exact successful prototype; no layout edits.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;
namespace RockPro { public static class LatchInProcess {
    static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=64000000};
    static Dictionary<string,object> O(object x){return (Dictionary<string,object>)x;}
    static int I(object x){return Convert.ToInt32(x);}
    static IZDoc D(object x){return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));}
    static double[] Matrix(IZSceneElement e){var m=e.GetTransformToGlobal();return Enumerable.Range(0,16).Select(k=>m.GetValue(k/4,k%4)).ToArray();}
    public static int Run(string folder){
        var report=new Dictionary<string,object>();bool passed=false;
        try{
            var q=O(J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));
            if((string)q["contract"]!="rockpro-wing-parametric-v1"||System.Diagnostics.Process.GetCurrentProcess().Id!=I(q["expected_pid"]))throw new Exception("Wrong host/adapter");
            dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;if(!app.ApiVersion.StartsWith("29."))throw new Exception("2027 required");
            string path=(string)q["output"];var doc=((Array)app.GetAllOpenDocs()).Cast<object>().Select(D).Single(d=>String.Equals(d.Name,path,StringComparison.OrdinalIgnoreCase));
            var s=(IZSceneDoc)doc;var u=(IZSceneDocUtility)s;var aliases=O(q["aliases"]);var features=O(q["feature_aliases"]);
            Func<int,IZElement> e=id=>u.GetElementById(aliases.ContainsKey(id.ToString())?I(aliases[id.ToString()]):id);
            var parts=((object[])q["parts"]).Select(O).ToArray();var matrices=parts.ToDictionary(p=>I(p["id"]),p=>Matrix((IZSceneElement)e(I(p["id"]))));
            var expressions=Enumerable.Range(0,s.ParameterMgr.Count).Select(k=>s.ParameterMgr.GetParameter(k)).ToDictionary(p=>p.Name,p=>p.Expression);
            if(expressions.Count!=26)throw new Exception("Expected 26 scene controls");
            foreach(var p in ((object[])q["parameters"]).Select(O)){
                var actual=Enumerable.Range(0,s.ParameterMgr.Count).Select(k=>s.ParameterMgr.GetParameter(k)).Single(x=>x.Name==(string)p["name"]);actual.Notes=(string)p["notes"];
            }
            var names=((object[])q["names"]).Select(O).ToDictionary(n=>I(n["id"]),n=>(string)n["name"]);
            foreach(var n in names)e(n.Key).Name=n.Value;
            foreach(var op in ((object[])q["operations"]).Select(O)){
                int id=I(op["id"]),wanted=features.ContainsKey(id.ToString())?I(features[id.ToString()]):id;var mgr=(IZPartFeatureMgr)e(I(op["part"]));IZFeature f=null;
                for(int k=0;k<mgr.GetFeaturesCount();k++)try{var candidate=mgr.GetFeatureAt(k);if(((IZElement)candidate).Id==wanted)f=candidate;}catch(COMException){}
                if(f==null)throw new Exception("Mapped cut missing "+id);
                ((IZElement)f).Name=(bool)op["reserved"]?"Rezerwowe wycięcie pianki — prawa ściana — bez uchwytu we wzorcu":op["mount"]!=null?"Wycięcie pod "+names[I(op["mount"])]+" — w: "+names[I(op["part"])]:"Wycięcie — "+names[I(op["part"])]+" — ID źródła "+id;
            }
            s.Update();double max=0;foreach(var p in matrices){var m=Matrix((IZSceneElement)e(p.Key));for(int k=0;k<16;k++)max=Math.Max(max,Math.Abs(m[k]-p.Value[k])*1000);}
            foreach(var p in expressions){var actual=Enumerable.Range(0,s.ParameterMgr.Count).Select(k=>s.ParameterMgr.GetParameter(k)).Single(x=>x.Name==p.Key);if(actual.Expression!=p.Value)throw new Exception("Parameter expression changed");}
            if(max>.08)throw new Exception("Naming changed geometry");var camera=(IZCamera)s.CameraMgr.ActiveCamera;camera.Perspective=false;camera.Direction=new double[]{.45,.8,-.5};camera.Up=new double[]{0,0,1};s.AdjustCameraToFitShapeInRect(1400,1100);s.Redraw();s.ExportImage(Path.Combine(folder,"final.png"),eZImageFormat.Z_IMAGE_PNG,1400,1100,true);
            s.SaveAs(path,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);report["labels"]=names.Count;report["cuts_named"]=((object[])q["operations"]).Length;report["pose_error_mm"]=max;passed=true;
        }catch(Exception ex){report["error"]=ex.ToString();}
        report["passed"]=passed;File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(report));return passed?0:1;
    }
}}
