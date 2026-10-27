// Source-pinned machining and assembly-stage organization. No document saves.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using System.Text.RegularExpressions;
using interop.ICApiIronCAD;

namespace RockPro {
public static class LatchInProcess {
    static JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 64000000 };
    static IZSceneDoc Scene;
    static Dictionary<string, IZElement> Nodes = new Dictionary<string, IZElement>();
    static Dictionary<string, IZFeature> Cuts = new Dictionary<string, IZFeature>();
    static Dictionary<string, object> Baseline;

    static IZDoc FindDocument(IZBaseApp app, string guid) {
        var active=app.ActiveDoc;
        if(active!=null && active.FileGUID==guid) return active;
        // Unlike GetOpenDocByGUID, this API includes unsaved documents. Some
        // 2023 wrappers expose the returned IUnknowns as integer addresses.
        foreach(object raw in (Array)app.GetAllOpenDocs()) {
            object instance=raw;
            if(raw is long || raw is ulong)
                instance=Marshal.GetObjectForIUnknown(new IntPtr(unchecked((long)Convert.ToUInt64(raw))));
            var doc=instance as IZDoc;
            if(doc!=null && doc.FileGUID==guid) return doc;
        }
        throw new Exception("Owned prototype is no longer open");
    }

    static Dictionary<string, object> Obj(object x) { return (Dictionary<string, object>)x; }
    static double[] Num(object x) { return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray(); }
    static void Near(double a, double b, string context, double tolerance = .003) {
        if (Double.IsNaN(a) || Math.Abs(a-b) > tolerance)
            throw new Exception(context + ": " + a + " != " + b);
    }
    static string Expr(string text, int depth) {
        foreach (string name in Baseline.Keys)
            text = Regex.Replace(text, "\\b"+name+"\\b", m => String.Concat(Enumerable.Repeat("Parent\\", depth))+"Params\\"+name);
        return text;
    }
    static void SetValues(Dictionary<string, object> values) {
        foreach (var kv in values)
            Scene.ParameterMgr.GetParameterByName(kv.Key).Expression = Convert.ToDouble(kv.Value).ToString(System.Globalization.CultureInfo.InvariantCulture)+" mm";
    }
    static void Update() { ((IZAssembly)Scene.GetTopElement()).RegenerateParts(true); Scene.Update(); }
    static List<IZElement> Children(IZElement node) {
        var list = new List<IZElement>();
        if (node.Type != eZElementType.Z_ELEMENT_ASSEMBLY && (int)node.Type != 0) return list;
        var a = node.GetChildrenZArray();
        for (int i=0; i<node.GetChildrenCount(); i++) { object raw; a.Get(i, out raw); list.Add((IZElement)raw); }
        return list;
    }
    static void Parameter(IZParameterMgr mgr, string name, string expression) {
        IZParameter parameter=null;
        for(int i=0;i<mgr.Count;i++) if(mgr.GetParameter(i).Name==name) parameter=mgr.GetParameter(i);
        if(parameter==null) parameter=mgr.CreateParameter(eZParamType.Z_PARAMETER_TYPE_LENGTH,name,0);
        parameter.Expression=expression;
        parameter.Notes="Parametr techniczny wyliczany z parametrów sceny. Nie zmieniać ręcznie.";
    }
    static void PlaceCut(IZFeature cut, Dictionary<string, object> spec) {
        var se=(IZSceneElement)cut;
        var a=se.GetAnchorTransform(); a.MakeIdentity(); se.SetAnchorTransform(a);
        var m=se.GetTransformToParent(); m.MakeIdentity();
        var r=(object[])spec["rotation"]; var p=Num(spec["initial"]);
        for(int j=0;j<3;j++) {
            for(int k=0;k<3;k++) m.SetValue(k,j,Convert.ToDouble(((object[])r[k])[j]));
            m.SetValue(3,j,p[j]/1000);
        }
        se.SetTransformToParent(m);
        var positions=(object[])spec["position"];
        for(int j=0;j<3;j++) Parameter(se.ParameterMgr,"RP_Polozenie"+"XYZ"[j],Expr((string)positions[j],2));
        se.ForceSetupParameterExpression();
        for(int j=0;j<3;j++) se.set_PositionTransformComponentExpression((eZTransformComponentType)j,"RP_Polozenie"+"XYZ"[j]);
    }
    static IZFeature FindCut(Dictionary<string,object> spec) {
        var mgr=(IZPartFeatureMgr)Nodes[(string)spec["target"]];
        for(int i=0;i<mgr.GetFeaturesCount();i++)
            if(((IZElement)mgr.GetFeatureAt(i)).Name==(string)spec["label"]) return mgr.GetFeatureAt(i);
        return null;
    }
    static void AddCuts(Dictionary<string,object> req, IZBaseApp app, IZDoc target) {
        foreach(object raw in (object[])req["hinge_cuts"]) {
            var spec=Obj(raw);var previous=FindCut(spec);
            if(previous!=null) {
                var allowed=req.ContainsKey("allowed_replacement_ids") ? Num(req["allowed_replacement_ids"]) : new double[0];
                if(!allowed.Contains((double)((IZElement)previous).Id)) throw new Exception("Opening already present; replacement not owned");
                ((IZElement)previous).Remove();
            }
            var template=Obj(spec["template"]);
            if((string)template["revision"]!="27095-opening-v1") throw new Exception("Unknown opening template");
            double w=Convert.ToDouble(template["width_mm"])/1000, h=Convert.ToDouble(template["height_mm"])/1000, r=Convert.ToDouble(template["radius_mm"])/1000;
            var pr=Scene.CreateProfile();
            pr.CreateLine(new[]{r,0.0},new[]{w-r,0.0},1);
            pr.CreateArc(new[]{w-r,r},r,-Math.PI/2,0,2);
            pr.CreateLine(new[]{w,r},new[]{w,h-r},3);
            pr.CreateArc(new[]{w-r,h-r},r,0,Math.PI/2,4);
            pr.CreateLine(new[]{w-r,h},new[]{r,h},5);
            pr.CreateArc(new[]{r,h-r},r,Math.PI/2,Math.PI,6);
            pr.CreateLine(new[]{0.0,h-r},new[]{0.0,r},7);
            pr.CreateArc(new[]{r,r},r,Math.PI,3*Math.PI/2,8);
            var temporary=Scene.CreatePart();
            try {
                var seed=(IZFeature)((IZPartFeatureMgr)temporary).CreateExtrudeFeature(eZOperationType.Z_UNITE,false,.02,0,0,pr,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB);
                // The host template supplies a profile offset (10,10,1 mm).
                // Normalize the section frame; its authored curves already use
                // the lower-left corner of the installation contour as origin.
                var section=(IZSceneElement)((IZExtrudeFeature)seed).CrossSection;
                var identity=section.GetTransformToParent();identity.MakeIdentity();section.SetTransformToParent(identity);
                temporary.Update();
                var part=(IZPart)Nodes[(string)spec["target"]];
                var cut=seed.CopyFeatureTo(part);cut.OperationType=eZOperationType.Z_SUBTRACT;
                ((IZElement)cut).Name=(string)spec["label"];
                ((IZExtrudeFeature)cut).ExtrudeThroughPart=true;
                PlaceCut(cut,spec);part.Regenerate();part.Update();
                Cuts[(string)spec["key"]]=cut;
            } finally {((IZElement)temporary).Remove();}
        }
    }
    static double[][] Matrix(IZElement node) {
        var m=((IZSceneElement)node).GetTransformToGlobal();
        return Enumerable.Range(0,4).Select(i=>Enumerable.Range(0,4).Select(j=>m.GetValue(i,j)*(i==3 && j<3?1000:1)).ToArray()).ToArray();
    }
    static Dictionary<int,double[][]> Capture() {
        var result=new Dictionary<int,double[][]>();
        Action<IZElement> visit=null;
        visit=n=>{ result[n.Id]=Matrix(n); foreach(var child in Children(n)) visit(child); };
        foreach(var n in Nodes.Values) visit(n);
        return result;
    }
    static void CheckCapture(Dictionary<int,double[][]> expected) {
        var actual=Capture(); if(actual.Count!=expected.Count) throw new Exception("Physical hierarchy changed");
        foreach(var row in expected) for(int i=0;i<4;i++) for(int j=0;j<4;j++)
            Near(actual[row.Key][i][j],row.Value[i][j],"Grouping moved node "+row.Key);
    }
    static void BindPose(IZSceneElement element, Dictionary<string,object> spec, int depth) {
        var anchor=element.GetAnchorTransform();anchor.MakeIdentity();element.SetAnchorTransform(anchor);
        var m=element.GetTransformToParent();m.MakeIdentity();
        var r=(object[])spec["rotation"];var initial=Num(spec["initial"]);
        for(int j=0;j<3;j++) {
            for(int k=0;k<3;k++)m.SetValue(k,j,Convert.ToDouble(((object[])r[k])[j]));
            m.SetValue(3,j,initial[j]/1000);
        }
        element.SetTransformToParent(m);
        var positions=(object[])spec["position"];
        for(int j=0;j<3;j++)Parameter(element.ParameterMgr,"RP_Polozenie"+"XYZ"[j],Expr((string)positions[j],depth));
        element.ForceSetupParameterExpression();
        for(int j=0;j<3;j++) {
            element.set_PositionTransformComponentExpression((eZTransformComponentType)j,"RP_Polozenie"+"XYZ"[j]);
            if(String.IsNullOrEmpty(element.get_PositionTransformComponentExpression((eZTransformComponentType)j)))throw new Exception("Position binding rejected");
        }
    }
    static void BindDimensions(IZFeature feature,Dictionary<string,object> spec) {
        var element=(IZSceneElement)feature;var mgr=element.ParameterMgr;var box=(IZSizeBox)feature;
        if(spec.ContainsKey("dimensions")) {
            var dims=(object[])spec["dimensions"];
            for(int j=0;j<3;j++)Parameter(mgr,"RP_Wymiar"+"XYZ"[j],Expr((string)dims[j],3));
            element.ForceSetupParameterExpression();
            box.LengthExpression="RP_WymiarX";box.WidthExpression="RP_WymiarY";box.HeightExpression="RP_WymiarZ";
            if(String.IsNullOrEmpty(box.LengthExpression)||String.IsNullOrEmpty(box.WidthExpression)||String.IsNullOrEmpty(box.HeightExpression))throw new Exception("Dimension binding rejected");
        } else if(spec.ContainsKey("length")) {
            Parameter(mgr,"RP_WymiarZ",Expr((string)spec["length"],3));element.ForceSetupParameterExpression();
            box.HeightExpression="RP_WymiarZ";
            if(String.IsNullOrEmpty(box.HeightExpression))throw new Exception("Profile length binding rejected");
        }
    }
    static void RebindAll(Dictionary<string,object> req) {
        // MoveChild can erase native expression references. Rebuild from the
        // authoritative plan, never from the already-corrupted getter strings.
        foreach(object raw in (object[])req["parts"]) {
            var spec=Obj(raw);var node=Nodes[(string)spec["key"]];BindPose((IZSceneElement)node,spec,2);
            if(spec.ContainsKey("dimensions")||spec.ContainsKey("length"))BindDimensions(((IZPartFeatureMgr)node).GetFeatureAt(0),spec);
        }
        foreach(object raw in ((object[])req["cuts"]).Concat((object[])req["new_cuts"])) {
            var spec=Obj(raw);var mgr=(IZPartFeatureMgr)Nodes[(string)spec["target"]];IZFeature found=null;
            for(int i=0;i<mgr.GetFeaturesCount();i++) {
                string name=((IZElement)mgr.GetFeatureAt(i)).Name;
                if(name.EndsWith(" / "+spec["key"])||name.EndsWith(" | "+spec["key"]))found=mgr.GetFeatureAt(i);
            }
            if(found==null)throw new Exception("Missing original machining during rebind");
            BindPose((IZSceneElement)found,spec,3);
            if(spec.ContainsKey("dimensions"))BindDimensions(found,spec);
        }
        foreach(object raw in (object[])req["hinge_cuts"]) {
            var spec=Obj(raw);BindPose((IZSceneElement)Cuts[(string)spec["key"]],spec,3);
        }
        Update();
    }
    static object Group(Dictionary<string,object> req) {
        var before=Capture();
        var top=(IZAssembly)Scene.GetTopElement();
        var groups=new Dictionary<string,IZAssembly>();
        if(top.GetChildrenCount()==6) {
            var roots=Children((IZElement)top);
            foreach(object raw in (object[])req["groups"]) {
                var spec=Obj(raw);
                var matches=roots.Where(e=>e.Name==(string)spec["label"]).ToArray();
                if(matches.Length!=1) throw new Exception("Unknown existing stage hierarchy");
                groups[(string)spec["id"]]=(IZAssembly)matches[0];
            }
            foreach(object raw in (object[])req["parts"]) {
                var spec=Obj(raw);
                if(Nodes[(string)spec["key"]].GetParent().Id!=((IZElement)groups[(string)spec["group_id"]]).Id)
                    throw new Exception("Part is in the wrong existing stage");
            }
            return groups.ToDictionary(k=>((IZElement)k.Value).Name,v=>v.Value.GetChildrenCount());
        }
        foreach(object raw in (object[])req["groups"]) {
            var spec=Obj(raw); var group=top.CreateSubAssembly();
            ((IZElement)group).Name=(string)spec["label"];
            var se=(IZSceneElement)group; var m=se.GetTransformToParent(); m.MakeIdentity(); se.SetTransformToParent(m);
            groups[(string)spec["id"]]=group;
        }
        foreach(object raw in (object[])req["parts"]) {
            var spec=Obj(raw); var node=Nodes[(string)spec["key"]];
            groups[(string)spec["group_id"]].MoveChild(node,false);

        }
        Update(); CheckCapture(before);
        if(top.GetChildrenCount()!=6) throw new Exception("Expected six stage groups");
        return groups.ToDictionary(k=>((IZElement)k.Value).Name,v=>v.Value.GetChildrenCount());
    }
    static object Check(Dictionary<string,object> req,Dictionary<string,object> test) {
        SetValues(Obj(test["parameters"])); Update();
        foreach(object raw in (object[])test["checks"]) {
            var spec=Obj(raw); var node=Nodes[(string)spec["key"]];var m=Matrix(node);var p=Num(spec["position"]);var r=(object[])spec["rotation"];
            for(int j=0;j<3;j++) {
                Near(m[3][j],p[j],"Position "+spec["key"]);
                for(int k=0;k<3;k++) Near(m[k][j],Convert.ToDouble(((object[])r[k])[j]),"Rotation "+spec["key"]);
            }
            if(spec.ContainsKey("dimensions")) {
                var bb=Num(((IZPart)node).GetBody(true).GetBoundingBox());var d=Num(spec["dimensions"]);
                for(int j=0;j<3;j++) Near((bb[j+3]-bb[j])*1000,d[j],"Size "+spec["key"]);
            }
        }
        foreach(object raw in (object[])test["cut_checks"]) {
            var spec=Obj(raw); var cut=Cuts[(string)spec["key"]];
            var m=((IZSceneElement)cut).GetPositionTransform(); var expected=Num(spec["position"]);
            for(int j=0;j<3;j++) Near(m.GetValue(3,j)*1000,expected[j],"Opening binding "+spec["key"]);
            var box=Num(cut.GetBoundingBox());
            Near(box[0]*1000,0,"Opening X datum");Near(box[1]*1000,0,"Opening Y datum");
            Near((box[3]-box[0])*1000,79,"27095 installation width");
            Near((box[4]-box[1])*1000,82,"27095 installation height");
        }
        int tested=0;
        for(int slot=1;slot<=2;slot++) foreach(string half in new[]{"base","lid"}) {
            var wood=(IZPart)Nodes["plywood/"+half+"/rear"];
            var hinge=Nodes["hinge/"+slot+"/"+half];
            if(wood.HasInterference(hinge)) throw new Exception("Plywood/hinge collision: "+slot+" / "+half);
            var profile=(IZPart)Nodes["profile/"+(half=="base"?"EG-0500_1":"EG-0500_2")+"/rear"];
            if(profile.HasInterference(hinge)) throw new Exception("Profile/hinge collision");
            tested++;
        }
        foreach(object raw in (object[])req["operations"]) {
            var op=Obj(raw);var mgr=(IZPartFeatureMgr)Nodes[(string)op["target"]];string key=(string)op["key"];
            int found=0;
            for(int i=0;i<mgr.GetFeaturesCount();i++) {
                var f=mgr.GetFeatureAt(i);string name=((IZElement)f).Name;
                bool match=key.StartsWith("hinge-panel/") ? Cuts.ContainsKey(key)&&((IZElement)Cuts[key]).Id==((IZElement)f).Id : name.EndsWith(" / "+key)||name.EndsWith(" | "+key);
                if(match && f.OperationType==eZOperationType.Z_SUBTRACT) found++;
            }
            if(found!=1) throw new Exception("Missing/duplicate required machining: "+key);
        }
        return new { name=test["name"], members=Nodes.Count, hinge_openings=Cuts.Count, complete_operations=24, hinge_plywood_pairs=tested, passed=true };
    }
    public static int Run(string folder) {
        var report=new Dictionary<string,object>();bool attached=false;
        try {
            var req=Obj(Json.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));
            if((string)req["contract"]!="rockpro-t1-structure-v1") throw new Exception("Wrong contract");
            dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;
            if(!app.ApiVersion.StartsWith("25.") || app.GetProcessID()!=Convert.ToInt32(req["expected_pid"])) throw new Exception("Wrong host");
            var doc=FindDocument(app,(string)req["guid"]);
            if(doc.Name!=(string)req["document"]||doc.FileGUID!=(string)req["guid"]) throw new Exception("Wrong scene");
            Scene=(IZSceneDoc)doc;Baseline=Obj(req["parameters"]);attached=true;
            if((string)req["phase"]!="cuts" && (string)req["phase"]!="group") throw new Exception("Unknown operation phase");
            int rootCount=Scene.GetTopElement().GetChildrenCount();
            if(rootCount!=((object[])req["parts"]).Length && !((string)req["phase"]=="group" && rootCount==6)) throw new Exception("Unexpected scene contents before grouping");
            var utility=(IZSceneDocUtility)doc;
            foreach(object raw in (object[])req["parts"]) {
                var spec=Obj(raw);var e=utility.GetElementById(Convert.ToInt32(spec["id"]));
                if(e.Name!=(string)spec["label"] && e.Name!="RockPro / "+spec["key"]) throw new Exception("Part identity changed: "+spec["key"]);
                Nodes[(string)spec["key"]]=e;
            }
            if((string)req["phase"]=="cuts") AddCuts(req,app,doc);
            else foreach(object raw in (object[])req["hinge_cuts"]) {
                var spec=Obj(raw);var cut=FindCut(spec);if(cut==null) throw new Exception("Missing hinge opening before grouping");Cuts[(string)spec["key"]]=cut;
            }
            if((string)req["phase"]=="group") {report["groups"]=Group(req);RebindAll(req);}
            var checks=new List<object>();
            try {
                foreach(object raw in (object[])req["check_cases"]) {
                    checks.Add(Check(req,Obj(raw)));
                    File.WriteAllText(Path.Combine(folder,"progress.json"),Json.Serialize(checks));
                }
            } finally { SetValues(Baseline);Update(); }
            report["checks"]=checks;
            foreach(object raw in (object[])req["parts"]) {var spec=Obj(raw);Nodes[(string)spec["key"]].Name=(string)spec["label"];}
            foreach(var node in Nodes.Values) node.SetDirtyFlag(eZDirtyFlag.Z_DIRTY_GRAPHICS);
            try {Scene.UpdateGraphics(0);Scene.Redraw();report["graphics"]="PASS";}
            catch(Exception graphics) {report["graphics"]="NOT RUN";report["graphics_error"]=graphics.Message;}
            report["document"]=doc.Name;report["unsaved"]=doc.Modified;report["passed"]=true;
        } catch(Exception error) {
            report["passed"]=false;report["error"]=error.ToString();
            if(attached) try {SetValues(Baseline);Update();Scene.UpdateGraphics(0);Scene.Redraw();} catch(Exception restore) {report["restore_error"]=restore.ToString();}
        }
        File.WriteAllText(Path.Combine(folder,"result.json"),Json.Serialize(report));
        return report.ContainsKey("passed")&&(bool)report["passed"]?0:1;
    }
}
}
