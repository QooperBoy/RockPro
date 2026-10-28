// ROC-46: source-pinned parts and machining in a NEW IronCAD 2027 scene.
// Never regenerate opaque catalogue subtrees or overwrite a source document.
using System;
using System.IO;
using System.Linq;
using System.Globalization;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;

namespace RockPro { public static class LatchInProcess {
    [ComImport,Guid("3DE05001-922D-11CF-AC2E-00A024581E5C"),InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
    interface LegacyApp { [DispId(42)] object ZIronCADApp { [return:MarshalAs(UnmanagedType.IDispatch)] get; } }
    static JavaScriptSerializer J = new JavaScriptSerializer { MaxJsonLength=64000000 };
    static IZBaseApp App; static IZSceneDoc Scene; static IZDoc ResultDoc;
    static string Folder;
    static Dictionary<string,object> Parameters;
    static Dictionary<string,object> Derived=new Dictionary<string,object>();
    static HashSet<string> Dimensionless=new HashSet<string>();
    static string[] GroupIds,GroupLabels;
    static void Step(string message) {File.AppendAllText(Path.Combine(Folder,"progress.log"),DateTime.UtcNow.ToString("o")+" "+message+Environment.NewLine);}
    static readonly Dictionary<string,IZSceneDoc> Sources=new Dictionary<string,IZSceneDoc>();
    static readonly Dictionary<string,IZElement> Nodes=new Dictionary<string,IZElement>();
    static readonly Dictionary<string,IZFeature> Cuts=new Dictionary<string,IZFeature>();
    static readonly Dictionary<string,IZAssembly> Groups=new Dictionary<string,IZAssembly>();
    static readonly Dictionary<string,int> ExpectedLeafCounts=new Dictionary<string,int>();
    static readonly List<IZDoc> OwnedSources=new List<IZDoc>();
    static readonly HashSet<string> UpdatedParts=new HashSet<string>();
    static readonly string[] StageIds={"plywood","profiles","corners","closures","handles","wheels"};
    static readonly string[] StageLabels={"1. Sklejka","2. Profile aluminiowe","3. Narożniki i wzmocnienia","4. Zamki i zawiasy","5. Uchwyty","6. Koła i gniazda"};
    static Dictionary<string,object> O(object x) { return (Dictionary<string,object>)x; }
    static object[] A(object x) { return ((Array)x).Cast<object>().ToArray(); }
    static double[] N(object x) { var r=A(x).Select(Convert.ToDouble).ToArray(); if(r.Any(v=>Double.IsNaN(v)||Double.IsInfinity(v)))throw new Exception("Non-finite geometry");return r; }
    static double[] V(object x) { var r=N(x);if(r.Length!=3)throw new Exception("Expected vector3");return r; }
    static string F(double x) { if(Double.IsNaN(x)||Double.IsInfinity(x))throw new Exception("Non-finite parameter");return x.ToString("R",CultureInfo.InvariantCulture); }
    static string Hash(string path) { using(var f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant(); }
    static IZDoc Doc(object x) { return x is IZDoc?(IZDoc)x:(IZDoc)Marshal.GetObjectForIUnknown(new IntPtr(unchecked((long)Convert.ToUInt64(x)))); }
    static List<IZDoc> Docs() { return A(App.GetAllOpenDocs()).Select(Doc).ToList(); }
    static string DocumentKey(IZDoc d) { return d.Name+"\n"+d.FileGUID; }
    static List<string> State(IEnumerable<IZDoc> docs) { return docs.Select(d=>J.Serialize(new{path=d.Name,guid=d.FileGUID,modified=d.Modified})).OrderBy(x=>x,StringComparer.Ordinal).ToList(); }
    static IZDoc OpenOwned(string path,bool readOnly,bool visible) {
        bool already;var doc=App.OpenFile2(path,readOnly,visible,out already);
        if(already||!String.Equals(Path.GetFullPath(doc.Name),Path.GetFullPath(path),StringComparison.OrdinalIgnoreCase))throw new Exception("Document path ownership refused");
        return doc;
    }
    static List<IZElement> Children(IZElement e) {
        var rows=new List<IZElement>();if(e.Type!=eZElementType.Z_ELEMENT_ASSEMBLY && (int)e.Type!=0)return rows;
        var a=e.GetChildrenZArray();for(int i=0;i<e.GetChildrenCount();i++){object x;a.Get(i,out x);rows.Add((IZElement)x);}return rows;
    }
    static int LeafCount(IZElement e) { return e.Type==eZElementType.Z_ELEMENT_PART?1:Children(e).Sum(x=>LeafCount(x)); }
    static string Name(Dictionary<string,object> s) { return (string)s["label"]+" | "+(string)s["id"]; }
    static string CutName(Dictionary<string,object> s) { return "RockPro | Obróbka | "+(string)s["id"]; }
    static string GroupKey(Dictionary<string,object> s) {return (string)s[s.ContainsKey("physical_group")?"physical_group":"stage_id"];}
    static string LocalPath(string name) {
        if(String.IsNullOrWhiteSpace(name)||name!=Path.GetFileName(name)||name.IndexOfAny(Path.GetInvalidFileNameChars())>=0||name=="."||name=="..")throw new Exception("Expected a local basename");
        var p=Path.Combine(Folder,name);if(File.Exists(p)||Directory.Exists(p))throw new Exception("Refusing overwrite");return p;
    }
    static string Expr(string text,int depth) {
        if(String.IsNullOrWhiteSpace(text)||text.Length>2048||text.Contains("\\")||text.Contains(":"))throw new Exception("Invalid expression");
        return Regex.Replace(text,@"\b[A-Za-z_][A-Za-z_0-9]*\b",m=>{
            if(m.Value=="mm")return "mm";
            if(!Parameters.ContainsKey(m.Value))throw new Exception("Unknown parameter in expression");
            return String.Concat(Enumerable.Repeat("Parent\\",depth))+"Params\\"+m.Value;
        });
    }
    static void Parameter(IZParameterMgr mgr,string name,string expr,string notes,bool scalar=false) {
        IZParameter p=null;for(int i=0;i<mgr.Count;i++)if(mgr.GetParameter(i).Name==name)p=mgr.GetParameter(i);
        if(p==null)p=mgr.CreateParameter(scalar?eZParamType.Z_PARAMETER_TYPE_SCALAR:eZParamType.Z_PARAMETER_TYPE_LENGTH,name,0);
        p.Expression=expr;p.Notes=notes;
    }
    static double[][] Rotation(Dictionary<string,object> s) {
        var r=s.ContainsKey("rotation")?A(s["rotation"]).Select(V).ToArray():new[]{new[]{1.0,0.0,0.0},new[]{0.0,1.0,0.0},new[]{0.0,0.0,1.0}};
        if(r.Length!=3)throw new Exception("Expected rotation3x3");
        for(int i=0;i<3;i++)for(int k=0;k<3;k++)Near(r[i].Zip(r[k],(a,b)=>a*b).Sum(),i==k?1:0,"Rotation orthogonality",1e-6);
        double det=r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1])-r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0])+r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0]);
        Near(s.ContainsKey("feature_id")&&s.ContainsKey("owner_id")?Math.Abs(det):det,1,"Mirrored catalogue placement refused",1e-6);return r;
    }
    static void Near(double actual,double expected,string context,double tolerance=.015) {
        if(Double.IsNaN(actual)||Double.IsInfinity(actual)||Math.Abs(actual-expected)>tolerance)throw new Exception(context+": "+F(actual)+" != "+F(expected));
    }
    static void BindPose(IZSceneElement e,Dictionary<string,object> s,int depth) {
        var anchor=e.GetAnchorTransform();anchor.MakeIdentity();e.SetAnchorTransform(anchor);
        var m=e.GetTransformToParent();m.MakeIdentity();var r=Rotation(s);var p=V(s["position_mm"]);
        for(int k=0;k<3;k++){for(int j=0;j<3;j++)m.SetValue(k,j,r[k][j]);m.SetValue(3,k,p[k]/1000);}
        e.SetTransformToParent(m);
        var expressions=A(s["position_expressions"]);if(expressions.Length!=3)throw new Exception("Expected three position expressions");
        for(int k=0;k<3;k++)Parameter(e.ParameterMgr,"RP_Polozenie"+"XYZ"[k],Expr((string)expressions[k],depth),"Położenie wyliczone z parametrów sceny. Nie zmieniać ręcznie.");
        e.ForceSetupParameterExpression();
        for(int k=0;k<3;k++){
            e.set_PositionTransformComponentExpression((eZTransformComponentType)k,Expr((string)expressions[k],depth));
            if(String.IsNullOrEmpty(e.get_PositionTransformComponentExpression((eZTransformComponentType)k)))throw new Exception("Position expression rejected");
        }
    }
    static void AnchorSize(IZFeature feature) {
        var e=(IZSceneElement)feature;var anchor=e.GetAnchorTransform();anchor.MakeIdentity();e.SetAnchorTransform(anchor);
        var box=(IZSizeBox)feature;box.ResizeAspectLock=0;box.LengthResizeBehavior=eZResizeBehaviorType.Z_RESIZE_ABOUT_ANCHOR;
        box.WidthResizeBehavior=eZResizeBehaviorType.Z_RESIZE_ABOUT_ANCHOR;box.HeightResizeBehavior=eZResizeBehaviorType.Z_RESIZE_ABOUT_ANCHOR;
        box.KeepAnchorFixedInSpace=false;
    }
    static void BindSize(IZFeature feature,object expressions,int depth) {
        var a=A(expressions);if(a.Length!=3)throw new Exception("Expected three size expressions");
        var e=(IZSceneElement)feature;var box=(IZSizeBox)feature;AnchorSize(feature);
        for(int k=0;k<3;k++)Parameter(e.ParameterMgr,"RP_Wymiar"+"XYZ"[k],Expr((string)a[k],depth),"Wymiar lokalny wyliczany z parametrów sceny.");
        e.ForceSetupParameterExpression();box.LengthExpression=Expr((string)a[0],depth);box.WidthExpression=Expr((string)a[1],depth);box.HeightExpression=Expr((string)a[2],depth);
    }
    static void BuildPanel(Dictionary<string,object> s) {
        Step("panel "+s["id"]);
        var dims=V(s["size_mm"]);if(dims.Any(x=>x<=0))throw new Exception("Panel size must be positive");
        var profile=Scene.CreateProfile();double[][] pts={new[]{0.0,0.0},new[]{dims[0]/1000,0.0},new[]{dims[0]/1000,dims[1]/1000},new[]{0.0,dims[1]/1000}};
        for(int k=0;k<4;k++)profile.CreateLine(pts[k],pts[(k+1)%4],k+1);
        var part=Scene.CreatePart();var node=(IZElement)part;node.Name=Name(s);Nodes.Add((string)s["id"],node);
        var f=(IZFeature)((IZPartFeatureMgr)part).CreateExtrudeFeature(eZOperationType.Z_UNITE,false,dims[2]/1000,0,0,profile,eZFeatureProfileRelType.Z_FEATURE_PROFILE_ABSORB);
        var cross=(IZSceneElement)((IZExtrudeFeature)f).CrossSection;var identity=cross.GetTransformToParent();identity.MakeIdentity();cross.SetTransformToParent(identity);
        var fe=(IZSceneElement)f;identity=fe.GetTransformToParent();identity.MakeIdentity();fe.SetTransformToParent(identity);
        part.Update();Step("panel before bind "+s["id"]+" "+J.Serialize(N(part.GetBody(true).GetBoundingBox())));((IZSizeBox)f).Reset(false);AnchorSize(f);
        Groups[GroupKey(s)].MoveChild(node,false);
        BindPose((IZSceneElement)part,s,2);Step("panel after pose "+s["id"]+" "+J.Serialize(N(part.GetBody(true).GetBoundingBox())));BindSize(f,s["size_expressions"],3);
        for(int axis=0;axis<3;axis++)fe.set_PositionTransformComponentExpression((eZTransformComponentType)axis,"0 mm");
        part.SurfaceFinish.Color=0x808040;part.BOMDescription="RockPro Studio: model prototypowy; odbiór produkcyjny nie został potwierdzony.";
        part.Update();Step("panel body "+s["id"]+" "+J.Serialize(N(part.GetBody(true).GetBoundingBox()))+" feature="+J.Serialize(Matrix((IZElement)f))+" cross="+J.Serialize(Matrix((IZElement)((IZExtrudeFeature)f).CrossSection)));ExpectedLeafCounts.Add((string)s["id"],1);UpdatedParts.Add((string)s["id"]);
    }
    static void ImportPart(Dictionary<string,object> s,Dictionary<string,string> cache) {
        Step("part "+s["id"]);
        string key=(string)s["source_key"]+":"+s["source_id"],path;
        var source=Sources[(string)s["source_key"]];var original=((IZSceneDocUtility)source).GetElementById(Convert.ToInt32(s["source_id"]));
        if(original==null||(original.Type!=eZElementType.Z_ELEMENT_PART&&original.Type!=eZElementType.Z_ELEMENT_ASSEMBLY))throw new Exception("Unknown catalogue root");
        if(!cache.TryGetValue(key,out path)){
            path=LocalPath("asset-"+cache.Count.ToString("D4")+".ics");
            if(original.Type==eZElementType.Z_ELEMENT_PART)((IZPart)original).SaveAs(path,false);else ((IZAssembly)original).SaveAs(path,false);
            if(!File.Exists(path))throw new Exception("Catalogue extraction failed");cache.Add(key,path);
        }
        Step("import "+s["id"]);var node=Groups[GroupKey(s)].AddChildFromExternalFile(path,false);node.Name=Name(s);
        int expected=LeafCount(original);if(expected<1||LeafCount(node)!=expected)throw new Exception("Incomplete catalogue subtree");
        Nodes.Add((string)s["id"],node);ExpectedLeafCounts.Add((string)s["id"],expected);
        Step("pose "+s["id"]);BindPose((IZSceneElement)node,s,2);
        if(s.ContainsKey("profile_length_mm")){
            if(node.Type!=eZElementType.Z_ELEMENT_PART)throw new Exception("Profile must be one part");
            bool linked;((IZPart)node).HasInternalLinks(out linked);Step("profile linked="+linked+" "+s["id"]);((IZPart)node).Unlink();
            var mgr=(IZPartFeatureMgr)node;if(mgr.GetFeaturesCount()!=1)throw new Exception("Only clean single-extrusion profiles can be resized");
            var f=mgr.GetFeatureAt(0);var extrusion=(IZExtrudeFeature)f;((IZSizeBox)f).Reset(false);AnchorSize(f);
            int axis=s.ContainsKey("profile_axis")?Convert.ToInt32(s["profile_axis"]):2;if(axis<0||axis>2)throw new Exception("Invalid profile axis");
            Parameter(((IZSceneElement)f).ParameterMgr,"RP_DlugoscProfilu",Expr((string)s["profile_length_expression"],3),"Długość profilu; przekrój katalogowy pozostaje stały.");
            ((IZSceneElement)f).ForceSetupParameterExpression();var box=(IZSizeBox)f;
            string lengthExpression=Expr((string)s["profile_length_expression"],3);
            if(axis==0)box.LengthExpression=lengthExpression;else if(axis==1)box.WidthExpression=lengthExpression;else box.HeightExpression=lengthExpression;
            for(int k=0;k<3;k++)((IZSceneElement)f).set_PositionTransformComponentExpression((eZTransformComponentType)k,"0 mm");
            Step("profile update "+s["id"]);((IZPart)node).Update();UpdatedParts.Add((string)s["id"]);
            var b=N(((IZPart)node).GetBody(true).GetBoundingBox());Near((b[axis+3]-b[axis])*1000,Convert.ToDouble(s["profile_length_mm"]),"Profile axial length");
        }
    }
    static void AddCut(Dictionary<string,object> s) {
        Step("cut "+s["id"]);
        if(!Nodes.ContainsKey((string)s["owner_id"]))throw new Exception("Machining owner is absent");
        var target=Nodes[(string)s["target_id"]];if(target.Type!=eZElementType.Z_ELEMENT_PART)throw new Exception("Machining target must be a part");
        var original=(IZFeature)((IZSceneDocUtility)Sources[(string)s["source_key"]]).GetElementById(Convert.ToInt32(s["feature_id"]));
        if(original.OperationType!=eZOperationType.Z_SUBTRACT)throw new Exception("Only source subtraction features are allowed");
        // CopyFeatureTo evaluates a subtraction at its OLD location before its
        // mounting transform can be assigned. In a differently sized new scene
        // that may not intersect anything. Copy the exact source profile first,
        // place it, then enable the subtraction; no bounding-box contour.
        var sourceExtrude=(IZExtrudeFeature)original;
        var cut=(IZFeature)((IZPartFeatureMgr)target).CreateExtrudeFeature(eZOperationType.Z_UNITE,false,
            sourceExtrude.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_FORWARD),
            sourceExtrude.get_ExtrudeDistance(eZExtrudeDirectionType.Z_EXTRUDE_DIRECTION_BACKWARD),0,
            sourceExtrude.CrossSection,eZFeatureProfileRelType.Z_FEATURE_PROFILE_COPY);
        ((IZElement)cut).Name=CutName(s);
        var cp=(IZSceneElement)((IZExtrudeFeature)cut).CrossSection;
        cp.SetTransformToParent(((IZSceneElement)sourceExtrude.CrossSection).GetTransformToParent());
        BindPose((IZSceneElement)cut,s,3);
        if(s.ContainsKey("size_expressions")){
            // A newly created extrusion's size box still has factory defaults.
            // Materialise it before resetting/binding, otherwise a 9.8-mm seed
            // is incorrectly treated as 9.8 mm in ALL three axes.
            ((IZPart)target).Update();((IZSizeBox)cut).Reset(false);
            BindSize(cut,s["size_expressions"],3);
        }
        cut.OperationType=eZOperationType.Z_SUBTRACT;
        if((bool)s["through_target"])((IZExtrudeFeature)cut).ExtrudeThroughPart=true;
        ((IZPart)target).Update();Cuts.Add((string)s["id"],cut);UpdatedParts.Add((string)s["target_id"]);
        Step("cut result "+s["id"]+" feature="+J.Serialize(N(cut.GetBoundingBox()))+" body="+J.Serialize(N(((IZPart)target).GetBody(true).GetBoundingBox())));
    }
    static void Refresh() {
        // Deliberately no top.RegenerateParts: imported hardware stays opaque.
        Scene.Update();
        // Regenerate only the new panels and clean profiles whose features we
        // authored. Update alone does not rebuild their expression-driven BRep.
        foreach(var key in UpdatedParts){((IZPart)Nodes[key]).Regenerate();((IZPart)Nodes[key]).Update();}
        Scene.Update();foreach(var node in Nodes.Values)node.SetDirtyFlag(eZDirtyFlag.Z_DIRTY_GRAPHICS);
        Scene.UpdateGraphics(0);Scene.Redraw();
    }
    static void FinalBindings(Dictionary<string,object> req) {
        // Importing another subtree can replace imported feature parameter
        // records. Bind only after ALL imports and the final hierarchy exist.
        foreach(object raw in A(req["panels"])){
            var s=O(raw);var part=(IZPart)Nodes[(string)s["id"]];BindPose((IZSceneElement)part,s,2);
            var f=((IZPartFeatureMgr)part).GetFeatureAt(0);BindSize(f,s["size_expressions"],3);
            for(int k=0;k<3;k++)((IZSceneElement)f).set_PositionTransformComponentExpression((eZTransformComponentType)k,"0 mm");
        }
        foreach(object raw in A(req["parts"])){
            var s=O(raw);var node=Nodes[(string)s["id"]];BindPose((IZSceneElement)node,s,2);
            if(s.ContainsKey("profile_length_expression")){
                var f=((IZPartFeatureMgr)node).GetFeatureAt(0);var e=(IZSceneElement)f;
                Parameter(e.ParameterMgr,"RP_DlugoscProfilu",Expr((string)s["profile_length_expression"],3),"Długość profilu; przekrój katalogowy pozostaje stały.");
                e.ForceSetupParameterExpression();((IZSizeBox)f).HeightExpression=Expr((string)s["profile_length_expression"],3);
                for(int k=0;k<3;k++)e.set_PositionTransformComponentExpression((eZTransformComponentType)k,"0 mm");
            }
        }
        foreach(object raw in A(req["cuts"])){
            var s=O(raw);var cut=Cuts[(string)s["id"]];BindPose((IZSceneElement)cut,s,3);
            if(s.ContainsKey("size_expressions"))BindSize(cut,s["size_expressions"],3);
        }
    }
    static void Values(Dictionary<string,object> values) {
        if(!new HashSet<string>(Parameters.Keys).SetEquals(values.Keys))throw new Exception("Check parameters are incomplete");
        foreach(var p in values)if(!Derived.ContainsKey(p.Key))Scene.ParameterMgr.GetParameterByName(p.Key).Expression=F(Convert.ToDouble(p.Value))+(Dimensionless.Contains(p.Key)?"":" mm");
        Step("parameters "+J.Serialize(values));
        Refresh();
        MeasureParameters(values);
        if(Nodes.ContainsKey("structure/bottom/front")){
            var f=((IZPartFeatureMgr)Nodes["structure/bottom/front"]).GetFeatureAt(0);var box=(IZSizeBox)f;var p=((IZSceneElement)f).ParameterMgr.GetParameterByName("RP_DlugoscProfilu");
            Step("profile evaluated height="+F(box.Height*1000)+" expr="+box.HeightExpression+" parameter="+p.Expression+" value="+J.Serialize(p.Value));
        }
    }
    static object MeasureParameters(Dictionary<string,object> expected) {
        var rows=new List<object>();
        foreach(var p in expected){var native=Scene.ParameterMgr.GetParameterByName(p.Key);double actual=Convert.ToDouble(native.Value)*(Dimensionless.Contains(p.Key)?1:1000);
            Near(actual,Convert.ToDouble(p.Value),"Scene parameter "+p.Key,Dimensionless.Contains(p.Key)?1e-7:.015);
            rows.Add(new{name=p.Key,value=actual,expression=native.Expression,notes=native.Notes,derived=Derived.ContainsKey(p.Key)});
        }return rows;
    }
    static double[][] Matrix(IZElement e) {
        var m=((IZSceneElement)e).GetTransformToGlobal();return Enumerable.Range(0,4).Select(i=>Enumerable.Range(0,4).Select(k=>m.GetValue(i,k)*(i==3&&k<3?1000:1)).ToArray()).ToArray();
    }
    static object Measure(object[] poses,object[] panels,object[] cuts,bool checkCutPoses=true) {
        if(Scene.GetTopElement().GetChildrenCount()!=Groups.Count)throw new Exception("Unexpected physical group count");
        if(Groups.Values.Sum(g=>g.GetChildrenCount())!=Nodes.Count)throw new Exception("Unexpected occurrence count");
        foreach(var n in Nodes)if(LeafCount(n.Value)!=ExpectedLeafCounts[n.Key])throw new Exception("Catalogue subtree count changed");
        var measured=new List<object>();
        foreach(object raw in poses){var s=O(raw);string id=(string)s["id"];var node=Nodes[id];var m=Matrix(node);var p=V(s["position_mm"]);var r=Rotation(s);
            for(int k=0;k<3;k++){Near(m[3][k],p[k],"Position "+id);for(int j=0;j<3;j++)Near(m[k][j],r[k][j],"Rotation "+id,1e-6);}
            if(node.GetParent().Id!=((IZElement)Groups[GroupKey(s)]).Id)throw new Exception("Wrong occurrence physical group");
            if(s.ContainsKey("profile_length_mm")){
                int axis=s.ContainsKey("profile_axis")?Convert.ToInt32(s["profile_axis"]):2;
                var bound=N(((IZPart)node).GetBody(true).GetBoundingBox());
                Near((bound[axis+3]-bound[axis])*1000,Convert.ToDouble(s["profile_length_mm"]),"Profile length "+id);
                Near(bound[axis]*1000,0,"Profile origin "+id);
            }
            measured.Add(new{id=id,native_id=node.Id,world_mm=m,physical_parts=LeafCount(node)});
        }
        var panelMeasurements=new List<object>();
        foreach(object raw in panels){var s=O(raw);string id=(string)s["id"];var part=(IZPart)Nodes[id];var b=N(part.GetBody(true).GetBoundingBox());var d=V(s.ContainsKey("expected_body_size_mm")?s["expected_body_size_mm"]:s["size_mm"]);
            if(b.Length!=6)throw new Exception("Invalid native bounds");for(int k=0;k<3;k++)Near((b[k+3]-b[k])*1000,d[k],"Panel size "+id);
            if(s.ContainsKey("expected_body_bounds_local_mm")){var expected=N(s["expected_body_bounds_local_mm"]);if(expected.Length!=6)throw new Exception("Expected bounds6");for(int k=0;k<6;k++)Near(b[k]*1000,expected[k],"Panel boundary "+id);}
            panelMeasurements.Add(new{id=id,native_id=((IZElement)part).Id,bounds_local_m=b,faces=part.GetBody(true).GetFacesCount()});
        }
        var machining=new List<object>();
        foreach(object raw in cuts){var s=O(raw);string id=(string)s["id"];var cut=Cuts[id];var target=Nodes[(string)s["target_id"]];var mgr=(IZPartFeatureMgr)target;
            bool found=false;for(int i=0;i<mgr.GetFeaturesCount();i++)if(((IZElement)mgr.GetFeatureAt(i)).Id==((IZElement)cut).Id)found=true;
            if(!found||cut.OperationType!=eZOperationType.Z_SUBTRACT||((IZExtrudeFeature)cut).ExtrudeThroughPart!=(bool)s["through_target"])throw new Exception("Required subtraction is absent");
            var cutBounds=N(cut.GetBoundingBox());
            if(s.ContainsKey("size_mm")){var dims=V(s["size_mm"]);for(int axis=0;axis<3;axis++)Near((cutBounds[axis+3]-cutBounds[axis])*1000,dims[axis],"Cut size "+id);}
            var local=((IZSceneElement)cut).GetTransformToParent();var p=V(s["position_mm"]);var r=Rotation(s);
            if(checkCutPoses)for(int k=0;k<3;k++){Near(local.GetValue(3,k)*1000,p[k],"Cut local position "+id);for(int j=0;j<3;j++)Near(local.GetValue(k,j),r[k][j],"Cut local rotation "+id,1e-6);}
            var lm=Enumerable.Range(0,4).Select(i=>Enumerable.Range(0,4).Select(k=>local.GetValue(i,k)*(i==3&&k<3?1000:1)).ToArray()).ToArray();
            machining.Add(new{id=id,native_id=((IZElement)cut).Id,owner_id=s["owner_id"],target_id=s["target_id"],target_native_id=target.Id,operation="subtract",bounds_local_m=cutBounds,world_mm=Matrix((IZElement)cut),target_local_mm=lm,local_pose_checked=checkCutPoses});
        }
        return new{passed=true,occurrences=measured,panels=panelMeasurements,machining=machining,physical_parts=ExpectedLeafCounts.Values.Sum()};
    }
    static void Reindex(Dictionary<string,object> req) {
        Nodes.Clear();Cuts.Clear();Groups.Clear();var roots=Children(Scene.GetTopElement());
        for(int i=0;i<GroupIds.Length;i++)Groups.Add(GroupIds[i],(IZAssembly)roots.Single(e=>e.Name==GroupLabels[i]));
        foreach(object raw in A(req["panels"]).Concat(A(req["parts"]))){var s=O(raw);Nodes.Add((string)s["id"],Children((IZElement)Groups[GroupKey(s)]).Single(e=>e.Name==Name(s)));}
        foreach(object raw in A(req["cuts"])){var s=O(raw);var mgr=(IZPartFeatureMgr)Nodes[(string)s["target_id"]];var found=new List<IZFeature>();for(int i=0;i<mgr.GetFeaturesCount();i++)if(((IZElement)mgr.GetFeatureAt(i)).Name==CutName(s))found.Add(mgr.GetFeatureAt(i));Cuts.Add((string)s["id"],found.Single());}
    }
    static object ResizeChecks(Dictionary<string,object> req) {
        var result=new List<object>();if(!req.ContainsKey("check_cases"))return new{status="NOT RUN",cases=result};
        try {foreach(object raw in A(req["check_cases"])){var c=O(raw);Values(O(c["parameters"]));result.Add(Measure(A(c["expectedposes"]),A(c["expectedpanels"]),c.ContainsKey("expectedcuts")?A(c["expectedcuts"]):A(req["cuts"]),c.ContainsKey("expectedcuts")));}}
        finally {Values(Parameters);}
        return new{status="PASS",cases=result};
    }
    static void CopyMeasuredModel(Dictionary<string,object> req) {
        var src=O(A(req["sources"]).Single());string path=(string)src["path"];
        if(Hash(path)!=(string)src["sha256"])throw new Exception("Model source SHA mismatch");
        string copy=LocalPath("input-copy.ics");File.Copy(path,copy,false);
        ResultDoc=OpenOwned(copy,false,true);Scene=(IZSceneDoc)ResultDoc;
        var roots=Children(Scene.GetTopElement());var utility=(IZSceneDocUtility)Scene;
        if(req.ContainsKey("input_groups")){
            var expected=A(req["input_groups"]).Select(Convert.ToString).ToArray();
            if(roots.Count!=expected.Length||!new HashSet<string>(roots.Select(g=>g.Name)).SetEquals(expected))throw new Exception("Source physical groups mismatch");
        }else if(roots.Count!=6)throw new Exception("Expected measured legacy Studio hierarchy");
        foreach(object raw in A(req["panels"]).Concat(A(req["parts"]))){
            var s=O(raw);var node=utility.GetElementById(Convert.ToInt32(s["source_native_id"]));
            if(node==null||node.Name!=(string)s["source_name"]||!roots.Any(g=>g.Id==node.GetParent().Id))throw new Exception("Source occurrence identity mismatch");
            Nodes.Add((string)s["id"],node);ExpectedLeafCounts.Add((string)s["id"],LeafCount(node));
            if(s.ContainsKey("size_expressions")||s.ContainsKey("profile_length_expression"))UpdatedParts.Add((string)s["id"]);
        }
        foreach(object raw in A(req["cuts"])){
            var s=O(raw);var mgr=(IZPartFeatureMgr)Nodes[(string)s["target_id"]];var fs=new List<IZFeature>();
            for(int i=0;i<mgr.GetFeaturesCount();i++)if(((IZElement)mgr.GetFeatureAt(i)).Name==CutName(s))fs.Add(mgr.GetFeatureAt(i));
            Cuts.Add((string)s["id"],fs.Single());UpdatedParts.Add((string)s["target_id"]);
        }
        var top=(IZAssembly)Scene.GetTopElement();
        for(int i=0;i<GroupIds.Length;i++){var group=top.CreateSubAssembly();((IZElement)group).Name=GroupLabels[i];Groups.Add(GroupIds[i],group);}
        foreach(object raw in A(req["panels"]).Concat(A(req["parts"]))){var s=O(raw);var node=Nodes[(string)s["id"]];Groups[GroupKey(s)].MoveChild(node,false);node.Name=Name(s);}
        foreach(var group in roots){if(group.GetChildrenCount()!=0)throw new Exception("Unmapped legacy children");group.Remove();}
    }
    public static int Run(string folder) {
        Folder=Path.GetFullPath(folder);var report=new Dictionary<string,object>{{"passed",false},{"production_approved",false}};
        Dictionary<string,object> req=null;List<string> before=null;HashSet<string> existingKeys=null;bool success=false,show=false;IZDoc priorActive=null;
        Sources.Clear();Nodes.Clear();Cuts.Clear();Groups.Clear();ExpectedLeafCounts.Clear();OwnedSources.Clear();UpdatedParts.Clear();ResultDoc=null;
        try {
            req=O(J.DeserializeObject(File.ReadAllText(Path.Combine(Folder,"request.json"))));
            if((string)req["contract"]!="roc46-native-v1")throw new Exception("Unknown native contract");
            if(!(bool)req["save_output"])throw new Exception("Explicit new-file save authorization is required");
            string output=LocalPath((string)req["output_filename"]);if(!output.EndsWith(".ics",StringComparison.OrdinalIgnoreCase))throw new Exception("Expected ICS output");
            show=req.ContainsKey("show_final")&&(bool)req["show_final"];
            bool copyModel=req.ContainsKey("mode")&&(string)req["mode"]=="accessory-update";
            GroupIds=req.ContainsKey("physical_groups")?A(req["physical_groups"]).Select(x=>(string)O(x)["id"]).ToArray():StageIds;
            GroupLabels=req.ContainsKey("physical_groups")?A(req["physical_groups"]).Select(x=>(string)O(x)["label"]).ToArray():StageLabels;
            Derived=req.ContainsKey("derived_parameters")?O(req["derived_parameters"]):new Dictionary<string,object>();
            Dimensionless=req.ContainsKey("dimensionless_parameters")?new HashSet<string>(A(req["dimensionless_parameters"]).Select(Convert.ToString)):new HashSet<string>();
            var legacy=(LegacyApp)Marshal.GetActiveObject("IronCAD.Application");App=(IZBaseApp)legacy.ZIronCADApp;
            if(!App.ApiVersion.StartsWith("29.")||App.GetProcessID()!=Convert.ToInt32(req["expected_pid"]))throw new Exception("Expected pinned IronCAD 2027 process");
            priorActive=App.ActiveDoc;var priorDocs=Docs();before=State(priorDocs);existingKeys=new HashSet<string>(priorDocs.Select(DocumentKey));
            report["before"]=before;report["api_version"]=App.ApiVersion;
            if(copyModel)CopyMeasuredModel(req);
            else {
            int si=0;foreach(object raw in A(req["sources"])){var s=O(raw);string path=Path.GetFullPath((string)s["path"]);if(Hash(path)!=(string)s["sha256"])throw new Exception("Source SHA mismatch");
                string copy=LocalPath("source-"+(si++).ToString("D3")+".ics");File.Copy(path,copy,false);if(Hash(copy)!=(string)s["sha256"])throw new Exception("Copied source mismatch");
                var doc=OpenOwned(copy,true,false);
                OwnedSources.Add(doc);Sources.Add((string)s["key"],(IZSceneDoc)doc);
            }
            var created=App.OpenNewDoc(eZDocType.Z_SCENE,false,true,"");
            if(existingKeys.Contains(DocumentKey(created)))throw new Exception("New scene ownership refused");
            ResultDoc=created;Scene=(IZSceneDoc)ResultDoc;
            }
            Parameters=O(req["parameters"]);foreach(var p in Parameters){if(!Regex.IsMatch(p.Key,@"^RP_[A-Za-z0-9_]+$"))throw new Exception("Invalid parameter name");Parameter(Scene.ParameterMgr,p.Key,F(Convert.ToDouble(p.Value))+(Dimensionless.Contains(p.Key)?"":" mm"),req.ContainsKey("parameter_notes")?(string)O(req["parameter_notes"])[p.Key]:"Parametr RockPro Studio w milimetrach. Wymiary i położenia części wynikają z tego parametru.",Dimensionless.Contains(p.Key));}
            foreach(var p in Derived)Parameter(Scene.ParameterMgr,p.Key,Expr((string)p.Value,0),(string)O(req["parameter_notes"])[p.Key]);
            if(!copyModel){
            var top=(IZAssembly)Scene.GetTopElement();for(int i=0;i<GroupIds.Length;i++){var g=top.CreateSubAssembly();((IZElement)g).Name=GroupLabels[i];var m=((IZSceneElement)g).GetTransformToParent();m.MakeIdentity();((IZSceneElement)g).SetTransformToParent(m);Groups.Add(GroupIds[i],g);}
            var cache=new Dictionary<string,string>();
            foreach(string stage in StageIds){
                Step("stage "+stage);
                foreach(object raw in A(req["panels"]))if((string)O(raw)["stage_id"]==stage)BuildPanel(O(raw));
                foreach(object raw in A(req["parts"]))if((string)O(raw)["stage_id"]==stage)ImportPart(O(raw),cache);
                foreach(object raw in A(req["cuts"]))if((string)O(raw)["stage_id"]==stage)AddCut(O(raw));
            }
            }
            FinalBindings(req);App.ActiveDoc=ResultDoc;Refresh();var poses=A(req["panels"]).Concat(A(req["parts"])).ToArray();
            Step("baseline measurements");report["parameter_table"]=MeasureParameters(Parameters);report["baseline"]=Measure(poses,A(req["panels"]),A(req["cuts"]));Step("resize checks");report["resize"]=ResizeChecks(req);
            report["restored"]=Measure(poses,A(req["panels"]),A(req["cuts"]));
            if(File.Exists(output)||Directory.Exists(output))throw new Exception("Output appeared during build; refusing overwrite");
            Step("save new output");Scene.SaveAs(output,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);if(ResultDoc.Modified||!File.Exists(output))throw new Exception("Save failed");
            ResultDoc.Close();ResultDoc=null;ResultDoc=OpenOwned(output,false,true);
            Scene=(IZSceneDoc)ResultDoc;Reindex(req);App.ActiveDoc=ResultDoc;Refresh();report["reopened"]=Measure(poses,A(req["panels"]),A(req["cuts"]));
            report["resize_after_reopen"]=ResizeChecks(req);report["restored_after_reopen"]=Measure(poses,A(req["panels"]),A(req["cuts"]));
            var camera=Scene.CameraMgr.ActiveCamera;camera.Direction=new double[]{-1,1,-.8};camera.Up=new double[]{0,0,1};
            Scene.AdjustCameraToFitShapeInRect(1200,900);Scene.UpdateGraphics(0);Scene.Redraw();
            if(ResultDoc.Modified){
                string restored=LocalPath("baseline-restored-"+Guid.NewGuid().ToString("N")+".ics");Scene.SaveAs(restored,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);output=restored;
                if(ResultDoc.Modified||!File.Exists(output))throw new Exception("Restored save failed");
                ResultDoc.Close();ResultDoc=null;ResultDoc=OpenOwned(output,false,true);Scene=(IZSceneDoc)ResultDoc;Reindex(req);App.ActiveDoc=ResultDoc;Refresh();
                report["final_file_reopened"]=Measure(poses,A(req["panels"]),A(req["cuts"]));
            }
            string imagePath=LocalPath("RockPro_Studio_T1.png");Scene.ExportImage(imagePath,eZImageFormat.Z_IMAGE_PNG,1200,900,false);report["preview_path"]=imagePath;
            report["output_path"]=output;report["output_sha256"]=Hash(output);report["parameters"]=Parameters;
            report["final_parameter_table"]=MeasureParameters(Parameters);report["physical_groups"]=GroupLabels;
            if(req.ContainsKey("plan_sha256"))report["plan_sha256"]=req["plan_sha256"];
            success=true;
        } catch(Exception e) {report["error"]=e.ToString();File.WriteAllText(Path.Combine(Folder,"failure-before-cleanup.json"),J.Serialize(report));}
        finally {
            if(ResultDoc!=null&&(!success||!show))try{
                if(ResultDoc.Modified){string recovery=LocalPath("recovery-"+Guid.NewGuid().ToString("N")+".ics");((IZSceneDoc)ResultDoc).SaveAs(recovery,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);report["recovery_path"]=recovery;}
                ResultDoc.Close();ResultDoc=null;
            }catch(Exception e){success=false;report["result_cleanup_error"]=e.ToString();}
            foreach(var doc in OwnedSources.ToArray())try{
                // These are unique hidden READ-ONLY input copies. Exporting a
                // catalogue subtree may dirty their SDK caches, but no user edit
                // is made there. Original input bytes remain in source-*.ics;
                // meaningful generated work is saved in output/recovery above.
                // Re-saving a read-only input needlessly rebuilds its opaque
                // catalogue history and can raise unrelated regeneration errors.
                doc.Close();OwnedSources.Remove(doc);
            }catch(Exception e){success=false;report["source_cleanup_error"]=e.ToString();}
            try {
                if(req!=null){bool unchanged=A(req["sources"]).All(x=>Hash((string)O(x)["path"])==(string)O(x)["sha256"]);report["sources_unchanged"]=unchanged;if(!unchanged)success=false;}
                if(before!=null){var after=State(Docs().Where(d=>existingKeys.Contains(DocumentKey(d))));bool same=before.SequenceEqual(after);report["existing_documents_preserved"]=same;if(!same)success=false;report["after_existing"]=after;}
                if((!show||!success)&&priorActive!=null)App.ActiveDoc=priorActive;
            }catch(Exception e){success=false;report["preservation_error"]=e.ToString();}
            if(!success&&ResultDoc!=null)try{
                if(ResultDoc.Modified){string recovery=LocalPath("recovery-"+Guid.NewGuid().ToString("N")+".ics");((IZSceneDoc)ResultDoc).SaveAs(recovery,eZLinksSaveOptions.Z_LINKS_COPY_ALL,false);report["recovery_path"]=recovery;}
                ResultDoc.Close();ResultDoc=null;
            }catch(Exception e){report["late_cleanup_error"]=e.ToString();}
            report["passed"]=success;report["final_visible"]=success&&show&&ResultDoc!=null;
            File.WriteAllText(Path.Combine(Folder,"result.json"),J.Serialize(report));
            // Loaded worker assemblies live for the host lifetime. Do not retain
            // COM graphs of closed sources and intermediate scenes in statics.
            Sources.Clear();Nodes.Clear();Cuts.Clear();Groups.Clear();ExpectedLeafCounts.Clear();OwnedSources.Clear();UpdatedParts.Clear();
            Scene=null;ResultDoc=null;App=null;Parameters=null;
            Derived.Clear();Dimensionless.Clear();GroupIds=null;GroupLabels=null;
        }
        return success?0:1;
    }
}}
