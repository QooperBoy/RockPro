// Pinned constructor model adapter. All mutations are confined to a new copy.
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
    static JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=64000000};
    static Dictionary<string,object> Q;
    static IZSceneDoc S; static IZSceneDocUtility U;
    static Dictionary<int,int> Aliases=new Dictionary<int,int>(),Features=new Dictionary<int,int>();
    static Dictionary<int,Dictionary<string,object>> Rows;
    static Dictionary<int,double[]> PartMatrices=new Dictionary<int,double[]>(),Bounds=new Dictionary<int,double[]>(),CutMatrices=new Dictionary<int,double[]>(),Lengths=new Dictionary<int,double[]>();
    static Dictionary<string,string> Defaults=new Dictionary<string,string>();
    static string Progress;
    static Dictionary<string,object> O(object x){return (Dictionary<string,object>)x;}
    static double[] N(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
    static object[] A(string key){return (object[])Q[key];}
    static int I(object x){return Convert.ToInt32(x);}
    static string F(double x){return x.ToString("G16",CultureInfo.InvariantCulture);}
    static void Mark(string x){File.AppendAllText(Progress,DateTime.UtcNow.ToString("o")+" "+x+Environment.NewLine);}
    static string Hash(string p){using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
    static IZDoc Doc(object x){return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(Convert.ToInt64(x)));}
    static IZElement E(int id){return U.GetElementById(Aliases.ContainsKey(id)?Aliases[id]:id);}
    static double[] Matrix(IZSceneElement e,bool world){var m=world?e.GetTransformToGlobal():e.GetTransformToParent();return Enumerable.Range(0,16).Select(k=>m.GetValue(k/4,k%4)).ToArray();}
    static void Transform(IZSceneElement e,double[] a){var m=e.GetTransformToParent();for(int k=0;k<16;k++)m.SetValue(k/4,k%4,a[k]);e.SetTransformToParent(m);}
    static IZParameter P(IZParameterMgr m,string n){for(int k=0;k<m.Count;k++)if(m.GetParameter(k).Name==n)return m.GetParameter(k);return null;}
    static void Param(IZParameterMgr m,string n,string expr,string note){var p=P(m,n)??m.CreateParameter(eZParamType.Z_PARAMETER_TYPE_LENGTH,n,0);p.Expression=expr;p.Notes=note;}
    static string SceneExpr(string s,int depth){string prefix=String.Concat(Enumerable.Repeat("Parent\\",depth))+"Params\\";return Regex.Replace(s,@"\bRP_[A-Za-z0-9_]+\b",m=>prefix+m.Value);}
    static IZFeature Feature(int part,int id){var m=(IZPartFeatureMgr)E(part);int wanted=Features.ContainsKey(id)?Features[id]:id;for(int k=0;k<m.GetFeaturesCount();k++)try{var f=m.GetFeatureAt(k);if(((IZElement)f).Id==wanted)return f;}catch(COMException){}throw new Exception("Missing mapped feature "+part+"/"+id);}
    static double[] Curves(IZProfile p){return ((Array)p.GetCurveIds()??new object[0]).Cast<object>().Select(x=>p.GetCurveLength(I(x))).OrderBy(x=>x).ToArray();}
    static void Capture(){
        foreach(var p in A("parts").Select(O)){int id=I(p["id"]);PartMatrices[id]=Matrix((IZSceneElement)E(id),true);Bounds[id]=N(((IZPart)E(id)).GetBody(true).GetBoundingBox());}
        foreach(var op in A("operations").Select(O)){int id=I(op["id"]);var profile=((IZExtrudeFeature)Feature(I(op["part"]),id)).CrossSection;CutMatrices[id]=Matrix((IZSceneElement)profile,true);Lengths[id]=Curves(profile);}
    }
    static void Rebuild(){
        foreach(object raw in A("rebuild")){
            int id=I(raw);var old=(IZPart)E(id);var oe=(IZElement)old;var parent=(IZAssembly)oe.GetParent();var pose=Matrix((IZSceneElement)old,false);
            var fresh=S.CreatePart();parent.MoveChild((IZElement)fresh,false);Transform((IZSceneElement)fresh,pose);
            var src=(IZPartFeatureMgr)old;var target=(IZPartFeatureMgr)fresh;
            for(int k=0;k<src.GetFeaturesCount();k++){
                var f=src.GetFeatureAt(k);var ex=(IZExtrudeFeature)f;var profile=S.CreateProfile();ex.CrossSection.CopyCurvesTo(profile);
                var nf=target.CreateExtrudeFeature(f.OperationType,false,ex.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_FORWARD),ex.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_BACKWARD),0,profile,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB);
                Transform((IZSceneElement)((IZExtrudeFeature)nf).CrossSection,Matrix((IZSceneElement)ex.CrossSection,false));
                var ne=(IZSceneElement)nf;var anchor=ne.GetAnchorTransform();anchor.MakeIdentity();ne.SetAnchorTransform(anchor);Transform(ne,Matrix((IZSceneElement)f,false));
                ((IZExtrudeFeature)nf).ExtrudeThroughPart=ex.ExtrudeThroughPart;((IZElement)nf).Name=((IZElement)f).Name;
                Features[((IZElement)f).Id]=((IZElement)nf).Id;((IZElement)nf).SetSuppressState(((IZElement)f).GetStateStatus(eZElementState.Z_SUPPRESSED));
            }
            fresh.SurfaceFinish.Color=new[]{1459,1463,1471,1479,1483,1648}.Contains(id)?0x808040:old.SurfaceFinish.Color;
            fresh.BOMDescription=old.BOMDescription;((IZElement)fresh).Name=oe.Name;
            var a=((IZSceneElement)fresh).GetAnchorTransform();a.MakeIdentity();((IZSceneElement)fresh).SetAnchorTransform(a);Transform((IZSceneElement)fresh,pose);
            ((IZSceneElement)fresh).AnchorBehavior=eZAnchorBehavior.Z_ANCHOR_BEHAVIOR_FIXED_POSITION;
            Aliases[id]=((IZElement)fresh).Id;oe.Remove();fresh.Update();Mark("rebuilt "+id);
        }
    }
    static void BindSize(Dictionary<string,object> d){
        int id=I(d["part"]);var row=Rows[id];int first=I(O(((object[])row["features"])[0])["id"]);var f=Feature(id,first);var e=(IZSceneElement)f;var pose=Matrix(e,false);
        // Body generation must precede Reset: a fresh extrude otherwise exposes a cube.
        ((IZPart)E(id)).Update();var b=(IZSizeBox)f;b.Reset(false);double[] size={b.Length*1000,b.Width*1000,b.Height*1000};
        var anchor=e.GetAnchorTransform();anchor.MakeIdentity();e.SetAnchorTransform(anchor);Transform(e,pose);
        b.LengthResizeBehavior=b.WidthResizeBehavior=b.HeightResizeBehavior=eZResizeBehaviorType.Z_RESIZE_ABOUT_ANCHOR;b.KeepAnchorFixedInSpace=true;
        var coeff=(object[])d["coefficients"];var primary=A("primary");var baseline=N(Q["primary_base"]);
        for(int k=0;k<3;k++){string expr=F(size[k])+" mm";var c=N(coeff[k]);for(int j=0;j<3;j++)if(Math.Abs(c[j])>1e-9)expr+=" + ("+F(c[j])+")*("+primary[j]+" - "+F(baseline[j])+" mm)";
            Param(e.ParameterMgr,"RP_Wymiar"+"XYZ"[k],SceneExpr(expr,I(row["depth"])+1),"Wynikowy wymiar materiału. Grubość sklejki i przekrój profilu są stałe.");}
        e.ForceSetupParameterExpression();b.LengthExpression="RP_WymiarX";b.WidthExpression="RP_WymiarY";b.HeightExpression="RP_WymiarZ";
    }
    static void BindPose(IZSceneElement e,IZSceneElement parent,object[] shifts,int depth,bool parentBound){
        var local=Matrix(e,false);var r=Matrix(parent,true);var anchor=e.GetAnchorTransform();anchor.MakeIdentity();e.SetAnchorTransform(anchor);Transform(e,local);e.AnchorBehavior=eZAnchorBehavior.Z_ANCHOR_BEHAVIOR_FIXED_POSITION;
        for(int k=0;k<3;k++)Param(e.ParameterMgr,"RP_RuchProjekt"+"XYZ"[k],SceneExpr((string)shifts[k],depth),"Wynikowe przesunięcie w osiach projektu; sterowane parametrami sceny. Nie edytować tutaj.");
        for(int axis=0;axis<3;axis++){
            string expr=F(local[12+axis]*1000)+" mm";
            for(int k=0;k<3;k++)if(Math.Abs(r[axis*4+k])>1e-9)expr+=" + ("+F(r[axis*4+k])+")*(RP_RuchProjekt"+"XYZ"[k]+(parentBound?" - Parent\\Params\\RP_RuchProjekt"+"XYZ"[k]:"")+")";
            Param(e.ParameterMgr,"RP_Polozenie"+"XYZ"[axis],expr,"Położenie lokalne, wynik wspólnej kotwy części i jej wycięcia.");
        }
        e.ForceSetupParameterExpression();for(int k=0;k<3;k++)e.set_PositionTransformComponentExpression((eZTransformComponentType)k,"RP_Polozenie"+"XYZ"[k]);
    }
    static double[] Shift(IZSceneElement e){return Enumerable.Range(0,3).Select(k=>P(e.ParameterMgr,"RP_RuchProjekt"+"XYZ"[k]).Value*1000).ToArray();}
    static double Value(string n){return P(S.ParameterMgr,n).Value*1000;}
    static void Update(){((IZAssembly)S.GetTopElement()).RegenerateParts(true);S.Update();}
    static void Values(Dictionary<string,object> values){foreach(var kv in Defaults)P(S.ParameterMgr,kv.Key).Expression=kv.Value;foreach(var kv in values)P(S.ParameterMgr,kv.Key).Expression=F(Convert.ToDouble(kv.Value))+" mm";Update();}
    static Dictionary<string,object> Check(string name){
        var errors=new List<object>();double poseMax=0,sizeMax=0,cutMax=0;var delta=A("primary").Select((x,k)=>Value((string)x)-N(Q["primary_base"])[k]).ToArray();
        foreach(var p in A("parts").Select(O)){
            int id=I(p["id"]);var e=(IZSceneElement)E(id);var a=Matrix(e,true);var old=PartMatrices[id];var move=Shift((IZSceneElement)E(I(p["owner"])));double pose=0,size=0;
            for(int k=0;k<3;k++)pose=Math.Max(pose,Math.Abs((a[12+k]-old[12+k])*1000-move[k]));
            for(int k=0;k<12;k++)pose=Math.Max(pose,Math.Abs(a[k]-old[k])*1000);
            var bounds=N(((IZPart)e).GetBody(true).GetBoundingBox());var initial=Bounds[id];var growth=(object[])p["growth"];
            for(int axis=0;axis<3;axis++){
                double expected=(initial[axis+3]-initial[axis])*1000;
                for(int j=0;j<3;j++)expected+=Math.Abs(old[axis*4+j])*Enumerable.Range(0,3).Sum(k=>N(growth[j])[k]*delta[k]);
                size=Math.Max(size,Math.Abs((bounds[axis+3]-bounds[axis])*1000-expected));
            }
            if(delta.All(x=>Math.Abs(x)<1e-6))for(int k=0;k<6;k++)size=Math.Max(size,Math.Abs(bounds[k]-initial[k])*1000);
            if(pose>.08||size>.08)errors.Add(new{part=id,pose_mm=pose,size_mm=size});poseMax=Math.Max(poseMax,pose);sizeMax=Math.Max(sizeMax,size);
        }
        foreach(var op in A("operations").Select(O)){
            int id=I(op["id"]),part=I(op["part"]);var f=Feature(part,id);var profile=((IZExtrudeFeature)f).CrossSection;var a=Matrix((IZSceneElement)profile,true);var old=CutMatrices[id];
            int owner=I(A("parts").Select(O).First(p=>I(p["id"])==part)["owner"]);
            var move=Shift((bool)op["bind"]?(IZSceneElement)f:(IZSceneElement)E(owner));double error=0;
            for(int k=0;k<3;k++)error=Math.Max(error,Math.Abs((a[12+k]-old[12+k])*1000-move[k]));for(int k=0;k<12;k++)error=Math.Max(error,Math.Abs(a[k]-old[k])*1000);
            var lengths=Curves(profile);if(lengths.Length!=Lengths[id].Length)error=1e6;else for(int k=0;k<lengths.Length;k++)error=Math.Max(error,Math.Abs(lengths[k]-Lengths[id][k])*1000);
            if(f.OperationType!=eZOperationType.Z_SUBTRACT||((IZElement)f).GetStateStatus(eZElementState.Z_SUPPRESSED))error=1e6;
            if(error>.08)errors.Add(new{cut=id,error_mm=error});cutMax=Math.Max(cutMax,error);
        }
        // Device is rigid; check its full oriented bounding box fits plywood interior.
        int device=I(Q["device_id"]);var dm=Matrix((IZSceneElement)E(device),true);var db=N(((IZPart)E(device)).GetBody(true).GetBoundingBox());var points=Enumerable.Range(0,8).Select(v=>Enumerable.Range(0,3).Select(j=>1000*(dm[12+j]+Enumerable.Range(0,3).Sum(k=>db[k+3*((v>>k)&1)]*dm[k*4+j]))).ToArray()).ToArray();
        var origin=N(Q["case_origin"]);double[] lo={origin[0]+6.8,origin[1]+6.8,Convert.ToDouble(Q["floor_top"])},hi={origin[0]+Value("RP_SzerokoscSkrzyni")-6.8,origin[1]+Value("RP_GlebokoscSkrzyni")-6.8,origin[2]+Value("RP_WysokoscCzapki")-6.8+Value("RP_UniesienieCzapki")};
        for(int k=0;k<3;k++)if(points.Min(p=>p[k])<lo[k]-.08||points.Max(p=>p[k])>hi[k]+.08)errors.Add(new{device_axis=k,error="Device exceeds plywood interior"});
        return new Dictionary<string,object>{{"name",name},{"passed",errors.Count==0},{"parts",PartMatrices.Count},{"cuts",CutMatrices.Count},{"pose_error_mm",poseMax},{"size_error_mm",sizeMax},{"cut_error_mm",cutMax},{"errors",errors}};
    }
    static void Picture(string path){var c=(IZCamera)S.CameraMgr.ActiveCamera;c.Perspective=false;c.Direction=new double[]{.45,.8,-.5};c.Up=new double[]{0,0,1};S.AdjustCameraToFitShapeInRect(1400,1100);S.Redraw();S.ExportImage(path,eZImageFormat.Z_IMAGE_PNG,1400,1100,true);}
    public static int Run(string folder){
        var result=new Dictionary<string,object>();var checks=new List<object>();IZDoc owned=null;bool passed=false;Progress=Path.Combine(folder,"progress.txt");
        try{
            Q=O(J.DeserializeObject(File.ReadAllText(Path.Combine(folder,"request.json"))));
            if((string)Q["contract"]!="rockpro-wing-parametric-v1"||System.Diagnostics.Process.GetCurrentProcess().Id!=I(Q["expected_pid"]))throw new Exception("Wrong source adapter or host");
            dynamic legacy=Marshal.GetActiveObject("IronCAD.Application");var app=(IZBaseApp)legacy.ZIronCADApp;if(!app.ApiVersion.StartsWith("29."))throw new Exception("2027 required");
            var before=((Array)app.GetAllOpenDocs()).Cast<object>().Select(Doc).ToDictionary(d=>d.FileGUID,d=>d.Modified);
            string source=(string)Q["source"],output=(string)Q["output"];if(Hash(source)!=(string)Q["sha256"])throw new Exception("Source hash mismatch");if(File.Exists(output))throw new Exception("Output exists");
            string copy=Path.Combine(folder,"WingCompact_working.ics");File.Copy(source,copy,false);bool already;owned=app.OpenFile2(copy,false,true,out already);if(already){owned=null;throw new Exception("Copy already open");}
            S=(IZSceneDoc)owned;U=(IZSceneDocUtility)S;S.ConstraintSolver=false;Rows=A("inventory").Select(O).ToDictionary(r=>I(r["id"]));Capture();Mark("captured original");
            Rebuild();Mark("material histories rebuilt");
            foreach(var p in A("parameters").Select(O)){Param(S.ParameterMgr,(string)p["name"],(string)p["expression"],(string)p["notes"]);Defaults[(string)p["name"]]=(string)p["expression"];}
            foreach(var d in A("dimensions").Select(O))BindSize(d);Mark("dimensions bound");
            foreach(var n in A("nodes").Select(O))BindPose((IZSceneElement)E(I(n["id"])),(IZSceneElement)E(I(n["parent"])),(object[])n["shift"],I(n["depth"]),I(n["parent"])!=1);
            Mark("nodes bound");
            foreach(var op in A("operations").Select(O)){
                var f=Feature(I(op["part"]),I(op["id"]));if((bool)op["bind"])BindPose((IZSceneElement)f,(IZSceneElement)E(I(op["part"])),(object[])op["shift"],I(op["depth"]),true);
                ((IZElement)f).Name=(bool)op["reserved"]?"Rezerwowe wycięcie pianki — prawa ściana — bez uchwytu we wzorcu":"Wycięcie montażowe — "+(string)Rows[I(op["part"])]["name"]+" — ID źródła "+op["id"];
            }
            Update();Mark("cuts bound");var initial=Check("poczatkowy");checks.Add(initial);if(!(bool)initial["passed"])throw new Exception("Initial check failed");
            foreach(var t in A("tests").Select(O)){Mark("test "+t["name"]);Values(O(t["values"]));var check=Check((string)t["name"]);checks.Add(check);Picture(Path.Combine(folder,(string)t["name"]+".png"));if(!(bool)check["passed"])throw new Exception("Test failed "+t["name"]);}
            Values(new Dictionary<string,object>());foreach(var n in A("names").Select(O))E(I(n["id"])).Name=(string)n["name"];
            foreach(int id in new[]{3249,1456,1646})((IZAssembly)E(id)).IsHidden=false;
            var restored=Check("powrot_i_nazwy");checks.Add(restored);if(!(bool)restored["passed"])throw new Exception("Restore failed");
            Picture(Path.Combine(folder,"final.png"));S.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);owned.Close2(true);owned=null;Mark("saved, reopening");
            owned=app.OpenFile2(output,false,true,out already);if(already){owned=null;throw new Exception("Final already open");}S=(IZSceneDoc)owned;U=(IZSceneDocUtility)S;
            var reopened=Check("ponowne_otwarcie");checks.Add(reopened);if(!(bool)reopened["passed"])throw new Exception("Reopen failed");
            Values(O(O(A("tests")[1])["values"]));var edited=Check("montaz_po_otwarciu");checks.Add(edited);if(!(bool)edited["passed"])throw new Exception("Reopened edit failed");
            Values(new Dictionary<string,object>());Picture(Path.Combine(folder,"final.png"));S.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);
            var after=((Array)app.GetAllOpenDocs()).Cast<object>().Select(Doc).ToDictionary(d=>d.FileGUID);
            foreach(var kv in before)if(!after.ContainsKey(kv.Key)||after[kv.Key].Modified!=kv.Value)throw new Exception("Preexisting document changed");if(Hash(source)!=(string)Q["sha256"])throw new Exception("Source changed");
            result["output"]=output;result["output_sha256"]=Hash(output);result["aliases"]=Aliases.ToDictionary(k=>k.Key.ToString(),k=>k.Value);result["feature_aliases"]=Features.ToDictionary(k=>k.Key.ToString(),k=>k.Value);
            result["source_unchanged"]=true;result["existing_documents_preserved"]=true;result["scene_parameters"]=Defaults.Keys.Select(n=>new{name=n,value_mm=Value(n),expression=P(S.ParameterMgr,n).Expression,notes=P(S.ParameterMgr,n).Notes}).ToArray();passed=true;
        }catch(Exception ex){result["error"]=ex.ToString();}
        finally{if(!passed&&owned!=null)try{((IZSceneDoc)owned).SaveAs(Path.Combine(folder,"FAILED_DO_NOT_USE_IC2027.ics"),eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);owned.Close2(true);}catch(Exception ex){result["cleanup_error"]=ex.ToString();}result["checks"]=checks;result["passed"]=passed;File.WriteAllText(Path.Combine(folder,"result.json"),J.Serialize(result));}
        return passed?0:1;
    }
}
}
