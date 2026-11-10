// Source-pinned native mounting revision. Never edits the source or another open document.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;

namespace RockPro {
public static class LatchInProcess {
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength=64000000 };
    static Dictionary<string,object> Request;
    static IZSceneDoc Scene;
    static IZSceneDocUtility Utility;
    static Dictionary<int,int> Aliases;
    static Dictionary<int,int> FeatureAliases;
    static Dictionary<int,Dictionary<string,object>> Inventory;
    static Dictionary<int,double[]> InitialMatrices,InitialBounds,InitialCutMatrices;
    static Dictionary<int,double[]> InitialCurveLengths;
    static Dictionary<string,string> Defaults;
    static Dictionary<int,Dictionary<string,object>> Mounts;
    static readonly string[] Primary={"RP_SzerokoscSkrzyni","RP_GlebokoscSkrzyni","RP_WysokoscDolu","RP_WysokoscCzapki","RP_UniesienieCzapki","RP_OdsuniecieWkladow"};
    static double[] PrimaryBase;
    static string Progress;
    static Dictionary<string,object> Obj(object x) { return (Dictionary<string,object>)x; }
    static double[] Num(object x) { return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray(); }
    static string Format(double x) { return x.ToString("G16",CultureInfo.InvariantCulture); }
    static void Mark(string x) { File.AppendAllText(Progress,DateTime.UtcNow.ToString("o")+" "+x+Environment.NewLine); }
    static string Hash(string path) {
        using(var f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
        using(var h=System.Security.Cryptography.SHA256.Create())
            return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();
    }
    static IZDoc Doc(object x) { return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x))); }
    static IZElement Element(int sourceId) { return Utility.GetElementById(Aliases.ContainsKey(sourceId)?Aliases[sourceId]:sourceId); }
    static double[] Matrix(IZSceneElement e,bool world) {
        var m=world?e.GetTransformToGlobal():e.GetTransformToParent();
        return Enumerable.Range(0,16).Select(k=>m.GetValue(k/4,k%4)).ToArray();
    }
    static void Transform(IZSceneElement e,double[] values) {
        var m=e.GetTransformToParent();
        for(int k=0;k<16;k++)m.SetValue(k/4,k%4,values[k]);
        e.SetTransformToParent(m);
    }
    static void Param(IZParameterMgr mgr,string name,string expression,string note) {
        IZParameter found=null;
        for(int i=0;i<mgr.Count;i++)if(mgr.GetParameter(i).Name==name)found=mgr.GetParameter(i);
        if(found==null)found=mgr.CreateParameter(eZParamType.Z_PARAMETER_TYPE_LENGTH,name,0);
        found.Expression=expression;found.Notes=note;
    }
    static IZParameter FindParam(IZParameterMgr mgr,string name) {
        for(int i=0;i<mgr.Count;i++)if(mgr.GetParameter(i).Name==name)return mgr.GetParameter(i);
        return null;
    }
    static void CopyParameters(IZParameterMgr from,IZParameterMgr to) {
        for(int i=0;i<from.Count;i++) {
            var p=from.GetParameter(i);
            if(p.Type!=eZParamType.Z_PARAMETER_TYPE_LENGTH)throw new Exception("Unexpected profile parameter type "+p.Name);
            Param(to,p.Name,String.IsNullOrEmpty(p.Expression)?Format(p.Value*1000)+" mm":p.Expression,p.Notes);
        }
    }
    static void RestorePoseBindings(IZSceneElement e) {
        e.ForceSetupParameterExpression();
        for(int k=0;k<3;k++)if(FindParam(e.ParameterMgr,"RP_Polozenie"+"XYZ"[k])!=null)
            e.set_PositionTransformComponentExpression((eZTransformComponentType)k,"RP_Polozenie"+"XYZ"[k]);
    }
    static IZFeature Feature(Dictionary<string,object> op) {
        int partId=Convert.ToInt32(op["part"]);
        var mgr=(IZPartFeatureMgr)Element(partId);
        if(((object[])Request["rebuild_profiles"]).Any(x=>Convert.ToInt32(x)==partId)) {
            int sourceId=Convert.ToInt32(op["source_feature"]);
            int wanted=FeatureAliases.ContainsKey(sourceId)?FeatureAliases[sourceId]:sourceId;
            for(int i=0;i<mgr.GetFeaturesCount();i++)if(((IZElement)mgr.GetFeatureAt(i)).Id==wanted)return mgr.GetFeatureAt(i);
            throw new Exception("Missing mapped profile feature "+sourceId);
        }
        return mgr.GetFeatureAt(Convert.ToInt32(op["feature_index"]));
    }
    static void RebuildJointProfiles() {
        foreach(object raw in (object[])Request["rebuild_profiles"]) {
            int id=Convert.ToInt32(raw);
            var old=(IZPart)Element(id);var oldElement=(IZElement)old;
            var parent=(IZAssembly)oldElement.GetParent();
            var originalMatrix=Matrix((IZSceneElement)old,false);
            var fresh=Scene.CreatePart();
            parent.MoveChild((IZElement)fresh,false);
            Transform((IZSceneElement)fresh,originalMatrix);
            CopyParameters(((IZSceneElement)old).ParameterMgr,((IZSceneElement)fresh).ParameterMgr);
            RestorePoseBindings((IZSceneElement)fresh);
            var original=(IZPartFeatureMgr)old;var target=(IZPartFeatureMgr)fresh;
            for(int i=0;i<original.GetFeaturesCount();i++) {
                var f=original.GetFeatureAt(i);var ex=f as IZExtrudeFeature;
                if(ex==null)throw new Exception("Unsupported joint-profile history "+id);
                var p=Scene.CreateProfile();ex.CrossSection.CopyCurvesTo(p);
                var nf=target.CreateExtrudeFeature(f.OperationType,false,
                    ex.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_FORWARD),
                    ex.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_BACKWARD),
                    0,p,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB);
                var ne=(IZSceneElement)nf;var oe=(IZSceneElement)f;
                Transform((IZSceneElement)((IZExtrudeFeature)nf).CrossSection,Matrix((IZSceneElement)ex.CrossSection,false));
                Transform(ne,Matrix(oe,false));
                var anchor=ne.GetAnchorTransform();anchor.MakeIdentity();ne.SetAnchorTransform(anchor);
                Transform(ne,Matrix(oe,false));
                CopyParameters(oe.ParameterMgr,ne.ParameterMgr);
                var a=(IZSizeBox)f;var b=(IZSizeBox)nf;
                // A new extrude exposes a provisional cube until its owning
                // part has generated its body. Reset before that point silently
                // leaves the cube; assigning widths then scales the section.
                fresh.Update();
                b.Reset(false);
                anchor=ne.GetAnchorTransform();anchor.MakeIdentity();ne.SetAnchorTransform(anchor);
                Transform(ne,Matrix(oe,false));
                b.LengthResizeBehavior=a.LengthResizeBehavior;b.WidthResizeBehavior=a.WidthResizeBehavior;
                b.HeightResizeBehavior=a.HeightResizeBehavior;b.KeepAnchorFixedInSpace=a.KeepAnchorFixedInSpace;
                ne.ForceSetupParameterExpression();
                if(!String.IsNullOrEmpty(a.LengthExpression))b.LengthExpression=a.LengthExpression;
                if(!String.IsNullOrEmpty(a.WidthExpression))b.WidthExpression=a.WidthExpression;
                if(!String.IsNullOrEmpty(a.HeightExpression))b.HeightExpression=a.HeightExpression;
                RestorePoseBindings(ne);
                ((IZExtrudeFeature)nf).ExtrudeThroughPart=ex.ExtrudeThroughPart;
                ((IZElement)nf).Name=((IZElement)f).Name;
                FeatureAliases[((IZElement)f).Id]=((IZElement)nf).Id;
                ((IZElement)nf).SetSuppressState(((IZElement)f).GetStateStatus(eZElementState.Z_SUPPRESSED));
            }
            fresh.SurfaceFinish.Color=old.SurfaceFinish.Color;
            fresh.BOMDescription=old.BOMDescription;((IZElement)fresh).Name=oldElement.Name;
            var partAnchor=((IZSceneElement)fresh).GetAnchorTransform();partAnchor.MakeIdentity();
            ((IZSceneElement)fresh).SetAnchorTransform(partAnchor);
            ((IZSceneElement)fresh).AnchorBehavior=eZAnchorBehavior.Z_ANCHOR_BEHAVIOR_FIXED_POSITION;
            Transform((IZSceneElement)fresh,originalMatrix);RestorePoseBindings((IZSceneElement)fresh);
            Aliases[id]=((IZElement)fresh).Id;oldElement.Remove();fresh.Update();
        }
    }
    static string SceneExpression(string text,int depth) {
        string prefix=String.Concat(Enumerable.Repeat("Parent\\",depth))+"Params\\";
        return Regex.Replace(text,@"\bRP_[A-Za-z0-9_]+\b",m=>prefix+m.Value);
    }
    static void AugmentPose(IZSceneElement e,Dictionary<string,object> mount,int depth,IZSceneElement parent) {
        var local=Matrix(e,false);var anchor=e.GetAnchorTransform();anchor.MakeIdentity();e.SetAnchorTransform(anchor);
        Transform(e,local);e.AnchorBehavior=eZAnchorBehavior.Z_ANCHOR_BEHAVIOR_FIXED_POSITION;
        var expressions=(object[])mount["delta"];
        for(int k=0;k<3;k++)Param(e.ParameterMgr,"RP_RuchGlobalny"+"XYZ"[k],SceneExpression((string)expressions[k],depth),
            "Wynikowe przesunięcie montażowe w osiach projektu, związane z parametrami sceny. Nie edytować tutaj.");
        var rotation=parent.GetTransformToGlobal();
        for(int axis=0;axis<3;axis++) {
            string name="RP_Polozenie"+"XYZ"[axis];var existing=FindParam(e.ParameterMgr,name);
            string expression=existing==null?Format(local[12+axis]*1000)+" mm":existing.Expression;
            if(String.IsNullOrEmpty(expression))expression=Format(local[12+axis]*1000)+" mm";
            for(int k=0;k<3;k++)if(Math.Abs(rotation.GetValue(axis,k))>1e-9)
                expression+=" + ("+Format(rotation.GetValue(axis,k))+")*RP_RuchGlobalny"+"XYZ"[k];
            Param(e.ParameterMgr,name,expression,"Położenie części lub wycięcia, powiązane z parametrami montażu. Nie zmieniać ręcznie.");
        }
        RestorePoseBindings(e);
    }
    static void Update() { ((IZAssembly)Scene.GetTopElement()).RegenerateParts(true);Scene.Update(); }
    static double SceneValue(string n) { return FindParam(Scene.ParameterMgr,n).Value*1000; }
    static double[] Delta(int id) {
        var m=((IZSceneElement)Element(id)).ParameterMgr;
        return Enumerable.Range(0,3).Select(k=>FindParam(m,"RP_RuchGlobalny"+"XYZ"[k]).Value*1000).ToArray();
    }
    static int Owner(int sourceId) {
        int i=sourceId;
        while(i>=0) { if(Mounts.ContainsKey(i))return i;i=Convert.ToInt32(Inventory[i]["parent"]); }
        return -1;
    }
    static void Capture() {
        InitialMatrices=new Dictionary<int,double[]>();InitialBounds=new Dictionary<int,double[]>();
        InitialCutMatrices=new Dictionary<int,double[]>();
        InitialCurveLengths=new Dictionary<int,double[]>();
        foreach(object raw in (object[])Request["parts"]) {
            int id=Convert.ToInt32(Obj(raw)["id"]);var e=Element(id);
            InitialMatrices[id]=Matrix((IZSceneElement)e,true);
            InitialBounds[id]=Num(((IZPart)e).GetBody(true).GetBoundingBox());
        }
        foreach(object raw in (object[])Request["operations"]) {
            var op=Obj(raw);int id=Convert.ToInt32(op["source_feature"]);
            var profile=((IZExtrudeFeature)Feature(op)).CrossSection;
            InitialCutMatrices[id]=Matrix((IZSceneElement)profile,true);
            InitialCurveLengths[id]=((Array)profile.GetCurveIds()).Cast<object>().Select(x=>profile.GetCurveLength(Convert.ToInt32(x))).OrderBy(x=>x).ToArray();
        }
    }
    static Dictionary<string,object> Check(string name) {
        var errors=new List<object>();double poseMax=0,sizeMax=0,cutMax=0;
        var primary=Primary.Select(SceneValue).ToArray();
        foreach(object raw in (object[])Request["parts"]) {
            var p=Obj(raw);int id=Convert.ToInt32(p["id"]);var part=(IZPart)Element(id);
            var actual=Matrix((IZSceneElement)part,true);var initial=InitialMatrices[id];
            var shift=(object[])p["shift"];int owner=Owner(id);var mount=owner<0?new double[3]:Delta(owner);
            double pose=0,size=0;
            for(int k=0;k<3;k++) {
                var coeff=Num(shift[k]);double expected=initial[12+k]*1000+mount[k]+
                    Enumerable.Range(0,6).Sum(j=>coeff[j]*(primary[j]-PrimaryBase[j]));
                pose=Math.Max(pose,Math.Abs(actual[12+k]*1000-expected));
            }
            for(int k=0;k<12;k++)pose=Math.Max(pose,Math.Abs(actual[k]-initial[k])*1000);
            var bounds=Num(part.GetBody(true).GetBoundingBox());var old=InitialBounds[id];var growth=(object[])p["local_growth"];
            for(int k=0;k<3;k++) {
                var coeff=Num(growth[k]);double expected=(old[k+3]-old[k])*1000+
                    Enumerable.Range(0,6).Sum(j=>coeff[j]*(primary[j]-PrimaryBase[j]));
                size=Math.Max(size,Math.Abs((bounds[k+3]-bounds[k])*1000-expected));
            }
            if(primary.Zip(PrimaryBase,(a,b)=>Math.Abs(a-b)).Max()<.001)
                for(int k=0;k<6;k++)size=Math.Max(size,Math.Abs(bounds[k]-old[k])*1000);
            if(pose>.08||size>.08)errors.Add(new{part=id,pose_mm=pose,size_mm=size,actual_bounds=bounds,initial_bounds=old});
            poseMax=Math.Max(poseMax,pose);sizeMax=Math.Max(sizeMax,size);
        }
        foreach(object raw in (object[])Request["operations"]) {
            var op=Obj(raw);int key=Convert.ToInt32(op["source_feature"]);var feature=Feature(op);
            var actual=Matrix((IZSceneElement)((IZExtrudeFeature)feature).CrossSection,true);
            var old=InitialCutMatrices[key];var move=Delta(Convert.ToInt32(op["mount"]));
            double error=0;
            int owner=Convert.ToInt32(op["mount"]);
            var ownerPart=((object[])Request["parts"]).Select(Obj).First(p=>Owner(Convert.ToInt32(p["id"]))==owner);
            var ownerShift=(object[])ownerPart["shift"];
            for(int k=0;k<3;k++) {
                var c=Num(ownerShift[k]);double sizeShift=Enumerable.Range(0,6).Sum(j=>c[j]*(primary[j]-PrimaryBase[j]));
                error=Math.Max(error,Math.Abs(actual[12+k]*1000-old[12+k]*1000-move[k]-sizeShift));
            }
            for(int k=0;k<12;k++)error=Math.Max(error,Math.Abs(actual[k]-old[k])*1000);
            var profile=((IZExtrudeFeature)feature).CrossSection;
            var lengths=((Array)profile.GetCurveIds()).Cast<object>().Select(x=>profile.GetCurveLength(Convert.ToInt32(x))).OrderBy(x=>x).ToArray();
            var originalLengths=InitialCurveLengths[key];
            if(lengths.Length!=originalLengths.Length)error=1e6;
            else for(int k=0;k<lengths.Length;k++)error=Math.Max(error,Math.Abs(lengths[k]-originalLengths[k])*1000);
            if(feature.OperationType!=eZOperationType.Z_SUBTRACT||((IZElement)feature).GetStateStatus(eZElementState.Z_SUPPRESSED))error=1e6;
            if(error>.08)errors.Add(new{cut=key,error_mm=error});
            cutMax=Math.Max(cutMax,error);
        }
        return new Dictionary<string,object>{{"name",name},{"passed",errors.Count==0},{"parts",383},{"cuts",56},
            {"pose_error_mm",poseMax},{"size_error_mm",sizeMax},{"cut_error_mm",cutMax},{"errors",errors}};
    }
    static void DefaultsAndValues(Dictionary<string,object> values) {
        foreach(var pair in Defaults)FindParam(Scene.ParameterMgr,pair.Key).Expression=pair.Value;
        foreach(var pair in values)FindParam(Scene.ParameterMgr,pair.Key).Expression=Format(Convert.ToDouble(pair.Value))+" mm";
        Update();
    }
    static void Reveal(IZElement e) {
        e.SetSuppressState(false);
        if(e.Type==eZElementType.Z_ELEMENT_PART){((IZPart)e).IsHidden=false;return;}
        if(e.Type==eZElementType.Z_ELEMENT_ASSEMBLY)((IZAssembly)e).IsHidden=false;
        var a=e.GetChildrenZArray();for(int i=0;i<e.GetChildrenCount();i++){object raw;a.Get(i,out raw);Reveal((IZElement)raw);}
    }
    static void Picture(string file) {
        var camera=(IZCamera)Scene.CameraMgr.ActiveCamera;camera.Perspective=false;
        camera.Direction=new double[]{.45,.8,-.5};camera.Up=new double[]{0,0,1};
        Scene.AdjustCameraToFitShapeInRect(1400,1100);Scene.Redraw();
        Scene.ExportImage(file,eZImageFormat.Z_IMAGE_PNG,1400,1100,true);
    }
    public static int Run(string folder) {
        var result=new Dictionary<string,object>();var checks=new List<object>();bool passed=false;IZDoc owned=null;
        Progress=Path.Combine(folder,"progress.txt");
        try {
            Request=Obj(Json.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));
            if((string)Request["contract"]!="rockpro-tv-mounting-v2"||System.Diagnostics.Process.GetCurrentProcess().Id!=Convert.ToInt32(Request["expected_pid"]))throw new Exception("Wrong request or host");
            dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;
            if(!app.ApiVersion.StartsWith("29."))throw new Exception("IronCAD 2027 required");
            var before=((Array)app.GetAllOpenDocs()).Cast<object>().Select(Doc).ToDictionary(d=>d.FileGUID,d=>d.Modified);
            string source=(string)Request["source"],output=(string)Request["output"];
            if(Hash(source)!=(string)Request["sha256"])throw new Exception("Snapshot changed");
            if(File.Exists(output))throw new Exception("Refusing to overwrite an existing revision");
            string working=Path.Combine(folder,"Television_mounting_working.ics");File.Copy(source,working,false);
            bool already;owned=app.OpenFile2(working,false,true,out already);
            if(already){owned=null;throw new Exception("Working file already open");}
            Scene=(IZSceneDoc)owned;Utility=(IZSceneDocUtility)Scene;Scene.ConstraintSolver=false;
            Aliases=Obj(Request["aliases"]).ToDictionary(x=>Int32.Parse(x.Key),x=>Convert.ToInt32(x.Value));
            FeatureAliases=new Dictionary<int,int>();
            Inventory=((object[])Request["inventory"]).Select(Obj).ToDictionary(x=>Convert.ToInt32(x["id"]));
            Mounts=((object[])Request["mounts"]).Select(Obj).ToDictionary(x=>Convert.ToInt32(x["id"]));
            PrimaryBase=Primary.Select(SceneValue).ToArray();Capture();Mark("source captured");
            RebuildJointProfiles();Mark("four joint profiles rebuilt");
            foreach(object raw in (object[])Request["parameters"]) {
                var p=Obj(raw);Param(Scene.ParameterMgr,(string)p["name"],(string)p["expression"],(string)p["notes"]);
            }
            foreach(var pair in Mounts) {
                var row=Inventory[pair.Key];var e=(IZSceneElement)Element(pair.Key);
                AugmentPose(e,pair.Value,Convert.ToInt32(row["depth"]),(IZSceneElement)Element(Convert.ToInt32(row["parent"])));
            }
            foreach(object raw in (object[])Request["operations"]) {
                var op=Obj(raw);var feature=Feature(op);var mount=Mounts[Convert.ToInt32(op["mount"])];
                AugmentPose((IZSceneElement)feature,mount,Convert.ToInt32(op["depth"]),(IZSceneElement)Element(Convert.ToInt32(op["part"])));
                ((IZElement)feature).Name="Wycięcie — "+(string)mount["kind"]+" — "+(string)mount["side"]+" — ID źródła "+op["source_feature"];
            }
            Defaults=new Dictionary<string,string>();
            foreach(string n in Primary.Concat(((object[])Request["parameters"]).Select(x=>(string)Obj(x)["name"])))Defaults[n]=FindParam(Scene.ParameterMgr,n).Expression;
            Update();Mark("mounting parameters bound");
            var baseline=Check("montaz_poczatkowy");checks.Add(baseline);
            if(!(bool)baseline["passed"])throw new Exception("Initial mounting check failed");
            foreach(object raw in (object[])Request["tests"]) {
                var test=Obj(raw);Mark("test "+test["name"]);DefaultsAndValues(Obj(test["values"]));
                var check=Check((string)test["name"]);checks.Add(check);
                Picture(Path.Combine(folder,(string)test["name"]+".png"));
                if(!(bool)check["passed"])throw new Exception("Mounting test failed: "+test["name"]);
            }
            DefaultsAndValues(new Dictionary<string,object>());
            foreach(object raw in (object[])Request["names"]) {var n=Obj(raw);Element(Convert.ToInt32(n["id"])).Name=(string)n["name"];}
            Reveal(Element(115));Scene.Update();
            var restored=Check("powrot_i_nazwy");checks.Add(restored);
            if(!(bool)restored["passed"])throw new Exception("Restore or naming broke bindings");
            Picture(Path.Combine(folder,"final.png"));Scene.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
            owned.Close2(true);owned=null;Mark("saved, reopening");
            owned=app.OpenFile2(output,false,true,out already);
            if(already){owned=null;throw new Exception("Final revision already open");}
            Scene=(IZSceneDoc)owned;Utility=(IZSceneDocUtility)Scene;
            var reopened=Check("ponowne_otwarcie");checks.Add(reopened);
            if(!(bool)reopened["passed"])throw new Exception("Reopen changed geometry");
            DefaultsAndValues(Obj(Obj(((object[])Request["tests"])[0])["values"]));
            var edited=Check("montaz_po_otwarciu");checks.Add(edited);
            if(!(bool)edited["passed"])throw new Exception("Reopened mounting parameters failed");
            DefaultsAndValues(new Dictionary<string,object>());Picture(Path.Combine(folder,"final.png"));
            Scene.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
            var after=((Array)app.GetAllOpenDocs()).Cast<object>().Select(Doc).ToDictionary(d=>d.FileGUID);
            foreach(var pair in before)if(!after.ContainsKey(pair.Key)||after[pair.Key].Modified!=pair.Value)throw new Exception("Preexisting document changed");
            if(Hash(source)!=(string)Request["sha256"])throw new Exception("Source changed");
            result["aliases"]=Aliases.ToDictionary(x=>x.Key.ToString(),x=>x.Value);
            result["feature_aliases"]=FeatureAliases.ToDictionary(x=>x.Key.ToString(),x=>x.Value);
            result["output"]=output;result["output_sha256"]=Hash(output);
            result["source_unchanged"]=true;result["existing_documents_preserved"]=true;
            result["scene_parameters"]=Defaults.Keys.Select(n=>new{name=n,expression=FindParam(Scene.ParameterMgr,n).Expression,value_mm=SceneValue(n),notes=FindParam(Scene.ParameterMgr,n).Notes}).ToArray();
            passed=true;
        } catch(Exception ex) { result["error"]=ex.ToString(); }
        finally {
            if(!passed&&owned!=null)try {
                ((IZSceneDoc)owned).SaveAs(Path.Combine(folder,"FAILED_DO_NOT_USE_IC2027.ics"),eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
                owned.Close2(true);
            }catch(Exception ex){result["cleanup_error"]=ex.ToString();}
            result["checks"]=checks;result["passed"]=passed;
            File.WriteAllText(Path.Combine(folder,"result.json"),Json.Serialize(result));
        }
        return passed?0:1;
    }
}
}
