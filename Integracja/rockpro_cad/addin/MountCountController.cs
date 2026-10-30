// Optional native quantity controller. Only scenes bearing its explicit manifest are touched.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;

[assembly:System.Reflection.AssemblyVersion("0.9.0.0")]
namespace RockPro.CAD {
    [ComVisible(true), Guid("93C43C38-9891-44D5-85A9-A07D513C3C21")]
    [ProgId("RockPro.CAD.MountCounts2027"), ClassInterface(ClassInterfaceType.None)]
    public class MountCountsAddin : IZAddinServer {
        public void InitSelf(ZAddinSite site) { MountCountController.Start(site.Application); }
        public void DeInitSelf() { MountCountController.Stop(); }
    }
    public static class MountCountController {
        public const string Property = "RockPro.MountCounts.v1";
        static readonly JavaScriptSerializer Json = new JavaScriptSerializer {MaxJsonLength=4000000};
        static Timer timer;
        static IZBaseApp app;
        static bool busy;
        public static bool Suspended;
        static readonly Dictionary<string,string> fingerprints=new Dictionary<string,string>();
        static Dictionary<string,object> O(object x) { return (Dictionary<string,object>)x; }
        static IZParameter P(IZSceneDoc scene,string name) { return scene.ParameterMgr.GetParameterByName(name); }
        public static void Start(IZBaseApp host) {
            if(!host.ApiVersion.StartsWith("29."))throw new InvalidOperationException("Quantity controller requires IronCAD 2027.");
            if(timer!=null)return;
            app=host;File.AppendAllText(Path.Combine(Path.GetDirectoryName(typeof(MountCountController).Assembly.Location),"quantity-startup.log"),DateTime.UtcNow.ToString("o")+" PID="+System.Diagnostics.Process.GetCurrentProcess().Id+" "+typeof(MountCountController).Assembly.FullName+Environment.NewLine);timer=new Timer();timer.Interval=600;timer.Tick+=Tick;timer.Start();
        }
        public static void Stop() { if(timer!=null){timer.Stop();timer.Dispose();timer=null;}app=null;fingerprints.Clear(); }
        static void Tick(object sender,EventArgs args) {
            if(busy||Suspended)return;
            busy=true;
            try {
                var doc=app.ActiveDoc;var scene=doc as IZSceneDoc;
                if(scene==null)return;
                var text=Manifest(scene);if(text==null)return;
                var q=O(Json.DeserializeObject(text));
                string key=doc.Name+"|"+doc.FileGUID;
                string signature=String.Join("|",Enumerable.Range(0,scene.ParameterMgr.Count).Select(i=>scene.ParameterMgr.GetParameter(i)).Where(p=>p.Type!=eZParamType.Z_PARAMETER_TYPE_TEXT).Select(p=>p.Name+":"+p.Expression+":"+p.Value));
                var utility=(IZSceneDocUtility)scene;
                signature+="|"+String.Join("",((object[])q["rows"]).Select(O).SelectMany(r=>(object[])r["slots"]).SelectMany(s=>(object[])s).Select(id=>utility.GetElementById(Convert.ToInt32(id)).GetStateStatus(eZElementState.Z_SUPPRESSED)?"1":"0"));
                string previous;if(fingerprints.TryGetValue(key,out previous)&&previous==signature)return;
                try {Apply(scene);Status(scene,"OK — liczba okuć i wycięcia są zsynchronizowane.");}
                catch(Exception error){Status(scene,"BŁĄD — "+error.GetBaseException().Message);throw;}
                finally {fingerprints[key]=signature;}
            } catch(Exception ex) {
                // No dialog while the constructor is editing. Preserve diagnostic evidence.
                try {File.AppendAllText(Path.Combine(Path.GetDirectoryName(typeof(MountCountController).Assembly.Location),"quantity-errors.log"),DateTime.UtcNow.ToString("o")+" "+ex+Environment.NewLine);}catch{}
            } finally {busy=false;}
        }
        static void Status(IZSceneDoc scene,string text) {
            IZParameter parameter=null;var mgr=scene.ParameterMgr;
            for(int i=0;i<mgr.Count;i++)if(mgr.GetParameter(i).Name=="RP_IloscOkuc_Status")parameter=mgr.GetParameter(i);
            if(parameter==null){parameter=mgr.CreateTextParameter("RP_IloscOkuc_Status",text);parameter.Notes="Wynik kontroli liczby bocznych okuć przez RockPro. BŁĄD oznacza, że trzeba poprawić liczbę, rozstaw lub głębokość. Nie edytuj tekstu ręcznie.";}
            else if(parameter.TextParameterValue!=text)parameter.TextParameterValue=text;
        }
        public static string Manifest(IZSceneDoc scene) {
            var mgr=((IZElement)scene.GetTopElement()).get_CustomPropMgr(false);
            if(mgr==null)return null;
            for(int i=0;i<mgr.Count;i++){string key;object value;mgr.GetAt(i,out key,out value);if(key==Property)return value as string;}
            return null;
        }

        static double[] Numbers(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
        static double[] Matrix(IZSceneElement e){var m=e.GetTransformToGlobal();return Enumerable.Range(0,16).Select(i=>m.GetValue(i/4,i%4)).ToArray();}
        public static double[] ContourCenter(IZProfile profile){
            var points=new List<double[]>();foreach(object raw in (Array)profile.GetCurveIds()){
                int id=Convert.ToInt32(raw);object a,b;double radius;var kind=profile.GetCurveType(id).ToString();
                if(kind=="Z_CURVE2D_LINE"){profile.GetLineData(id,out a,out b);points.Add(Numbers(a));points.Add(Numbers(b));}
                else if(kind=="Z_CURVE2D_CIRCLE"){profile.GetCircleData(id,out a,out radius);var c=Numbers(a);points.Add(new[]{c[0]-radius,c[1]-radius});points.Add(new[]{c[0]+radius,c[1]+radius});}
                else if(kind!="Z_CURVE2D_FILLET")throw new InvalidOperationException("Unsupported mounting contour: "+kind);
            }
            if(points.Count==0)throw new InvalidOperationException("Mounting contour has no supported reference points.");
            var center=new[]{(points.Min(p=>p[0])+points.Max(p=>p[0]))/2,(points.Min(p=>p[1])+points.Max(p=>p[1]))/2,0};
            var m=Matrix((IZSceneElement)profile);return Enumerable.Range(0,3).Select(j=>m[12+j]+Enumerable.Range(0,3).Sum(k=>center[k]*m[k*4+j])).ToArray();
        }
        static void SetWorld(IZSceneElement e,double[] world){
            var actual=Matrix(e);if(Enumerable.Range(0,16).Max(i=>Math.Abs(actual[i]-world[i]))<1e-11)return;
            var parent=(IZSceneElement)((IZElement)e).GetParent();var p=Matrix(parent);var local=new double[16];local[15]=1;
            for(int a=0;a<3;a++){for(int b=0;b<3;b++)local[a*4+b]=Enumerable.Range(0,3).Sum(k=>world[a*4+k]*p[b*4+k]);local[12+a]=Enumerable.Range(0,3).Sum(k=>(world[12+k]-p[12+k])*p[a*4+k]);}
            // Pin the SDK's own position components (anchor-aware), not guessed
            // feature-frame origins. The quantity controller owns these mounts.
            var m=e.GetTransformToParent();for(int i=0;i<16;i++)m.SetValue(i/4,i%4,local[i]);e.SetTransformToParent(m);
            for(int i=0;i<3;i++){double value=e.get_PositionTransformComponentValue((eZTransformComponentType)i);e.set_PositionTransformComponentExpression((eZTransformComponentType)i,value.ToString("G16",System.Globalization.CultureInfo.InvariantCulture)+" m");}
        }
        public static void Position(IZSceneDoc scene,Dictionary<string,object> q){
            var utility=(IZSceneDocUtility)scene;double w=P(scene,"RP_SzerokoscSkrzyni").Value*1000;
            double h=P(scene,"RP_WysokoscDolu").Value*1000,lift=P(scene,"RP_UniesienieCzapki").Value*1000;
            foreach(var pose in ((object[])q["poses"]).Select(O)){
                var m=Numbers(pose["world"]);int n=(int)Math.Round(P(scene,(string)pose["count"]).Value),i=Convert.ToInt32(pose["index"]);
                if(i>=n)continue;
                double center=P(scene,(string)pose["center"]).Value*1000,spread=P(scene,(string)pose["spread"]).Value*1000;
                m[13]=(-1011.5+center+(n<=1?0:(-0.5+(double)i/(n-1))*spread))/1000;
                if((bool)pose["right"])m[12]+=(w-Convert.ToDouble(q["base_width"]))/1000;
                string height=(string)pose["height"];
                if(!String.IsNullOrEmpty(height))m[14]+=(P(scene,height).Value*1000-Convert.ToDouble(pose["height_base"]))/1000;
                if((bool)pose["follow_body"])m[14]+=(h-Convert.ToDouble(q["base_body"]))/1000;
                if((bool)pose["cap"])m[14]+=(lift-Convert.ToDouble(q["base_lift"]))/1000;
                SetWorld((IZSceneElement)utility.GetElementById(Convert.ToInt32(pose["id"])),m);
            }
            scene.Update();
        }
        public static void MateCuts(IZSceneDoc scene,Dictionary<string,object> q){
            var utility=(IZSceneDocUtility)scene;var targets=new Dictionary<int,IZPart>();
            // Two deterministic corrections account for native feature anchor
            // normalization during body generation; neither changes the contour.
            for(int pass=0;pass<2;pass++){
                targets.Clear();
                foreach(var mate in ((object[])q["mates"]).Select(O)){
                    var element=utility.GetElementById(Convert.ToInt32(mate["id"]));if(element.GetStateStatus(eZElementState.Z_SUPPRESSED))continue;
                    var root=utility.GetElementById(Convert.ToInt32(mate["root"]));if(root.GetStateStatus(eZElementState.Z_SUPPRESSED))continue;
                    var frame=Matrix((IZSceneElement)root);var offset=Numbers(mate["local"]);var expected=Enumerable.Range(0,3).Select(j=>frame[12+j]+Enumerable.Range(0,3).Sum(k=>offset[k]*frame[k*4+j])).ToArray();
                    var actual=ContourCenter(((IZExtrudeFeature)element).CrossSection);if(Enumerable.Range(0,3).Max(k=>Math.Abs(expected[k]-actual[k]))<1e-10)continue;var world=Matrix((IZSceneElement)element);
                    for(int k=0;k<3;k++)world[12+k]+=expected[k]-actual[k];SetWorld((IZSceneElement)element,world);
                    var part=(IZPart)element.GetOwnerPart();targets[((IZElement)part).Id]=part;
                }
                if(targets.Count==0)break;foreach(var part in targets.Values)part.Update();scene.Update();
            }
        }

        public static double[] WorldBounds(IZPart part){
            var b=Numbers(part.GetBody(true).GetBoundingBox());var m=Matrix((IZSceneElement)part);
            var points=Enumerable.Range(0,8).Select(mask=>Enumerable.Range(0,3).Select(j=>m[12+j]+Enumerable.Range(0,3).Sum(k=>b[k+3*((mask>>k)&1)]*m[k*4+j])).ToArray()).ToArray();
            return Enumerable.Range(0,6).Select(j=>j<3?points.Min(p=>p[j]):points.Max(p=>p[j-3])).ToArray();
        }
        public static void Transport(IZSceneDoc scene,Dictionary<string,object> q){
            if(!q.ContainsKey("transport"))return;var t=O(q["transport"]);var u=(IZSceneDocUtility)scene;
            double width=P(scene,"RP_Podwozie_SzerokoscPodpory").Value*1000;
            double thickness=P(scene,"RP_Podwozie_GruboscPodpory").Value*1000;
            double edge=P(scene,"RP_Podwozie_MarginesKonca").Value*1000;
            double inset=P(scene,"RP_Podwozie_OdsuniecieBoku").Value*1000;
            double wheelInset=P(scene,"RP_Podwozie_OdsuniecieKol").Value*1000;
            var floor=WorldBounds((IZPart)u.GetElementById(Convert.ToInt32(t["floor"])));
            double length=(floor[4]-floor[1])*1000-2*edge;
            if(width<120||thickness<12||edge<35||inset<width/2+35||length<180||wheelInset<50||2*wheelInset+80>length||2*(inset+width/2)>(floor[3]-floor[0])*1000)
                throw new InvalidOperationException("Podwozie: brak miejsca na podpory i sztywne płyty kół. Sprawdź marginesy, szerokość podpory i odsunięcia.");
            foreach(var rail in ((object[])t["rails"]).Select(O)){
                int id=Convert.ToInt32(rail["id"]);var part=(IZPart)u.GetElementById(id);var mgr=(IZPartFeatureMgr)part;var f=mgr.GetFeatureAt(0);var box=(IZSizeBox)f;
                // The source plate is a single rectangular native extrude.
                double[] sizes={width,length,thickness};
                double[] actual={box.Length*1000,box.Width*1000,box.Height*1000};
                for(int k=0;k<3;k++)if(Math.Abs(actual[k]-sizes[k])>1e-7){string v=sizes[k].ToString("G16",System.Globalization.CultureInfo.InvariantCulture)+" mm";if(k==0)box.LengthExpression=v;else if(k==1)box.WidthExpression=v;else box.HeightExpression=v;}
                part.Update();var bounds=WorldBounds(part);bool right=(bool)rail["right"];
                double cx=right?floor[3]-inset/1000:floor[0]+inset/1000;
                double cy=(floor[1]+floor[4])/2,top=floor[2];var m=Matrix((IZSceneElement)part);
                m[12]+=cx-(bounds[0]+bounds[3])/2;m[13]+=cy-(bounds[1]+bounds[4])/2;m[14]+=top-bounds[5];SetWorld((IZSceneElement)part,m);
                foreach(var wheel in ((object[])rail["wheels"]).Select(O)){
                    var wm=Numbers(wheel["world"]);var offset=Numbers(wheel["mount_offset"]);
                    wm[12]=cx-offset[0];wm[13]=((bool)wheel["rear"]?floor[4]-(edge+wheelInset)/1000:floor[1]+(edge+wheelInset)/1000)-offset[1];
                    wm[14]=top-thickness/1000-offset[2];SetWorld((IZSceneElement)u.GetElementById(Convert.ToInt32(wheel["id"])),wm);
                }
            }
            scene.Update();
        }

        public static int Apply(IZSceneDoc scene) {
            var text=Manifest(scene);if(text==null)throw new InvalidOperationException("Quantity manifest missing.");
            var q=O(Json.DeserializeObject(text));
            if((string)q["contract"]!="rockpro-tv-counts-v2")throw new InvalidOperationException("Unsupported quantity contract.");
            scene.Update();
            var utility=(IZSceneDocUtility)scene;
            var changes=new List<Tuple<IZElement,bool>>();
            double depth=P(scene,"RP_GlebokoscSkrzyni").Value*1000;
            var validRows=new List<Dictionary<string,object>>();
            var errors=new List<string>();
            try{Transport(scene,q);}catch(Exception ex){errors.Add(ex.GetBaseException().Message);}
            foreach(var row in ((object[])q["rows"]).Select(O)) {
                double value=P(scene,(string)row["count"]).Value;
                var slots=(object[])row["slots"];
                double center=P(scene,(string)row["center"]).Value*1000;
                double spread=P(scene,(string)row["spread"]).Value*1000;
                string error=MountRowLayout.Validate(value,Convert.ToInt32(row["minimum"]),slots.Length,
                    depth,center,spread,2*Convert.ToDouble(row["half_width"]),
                    Convert.ToDouble(row["clearance"]),Convert.ToDouble(row["clearance"]));
                if(error!=null){errors.Add((string)row["count"]+": "+error);continue;}
                int n=(int)Math.Round(value);
                validRows.Add(row);
                for(int i=0;i<slots.Length;i++)foreach(object raw in (object[])slots[i]) {
                    var e=utility.GetElementById(Convert.ToInt32(raw));
                    if(e==null)throw new InvalidOperationException("Missing quantity member "+raw);
                    if(e.Type!=eZElementType.Z_ELEMENT_ASSEMBLY&&(!(e is IZExtrudeFeature)||((IZFeature)e).OperationType!=eZOperationType.Z_SUBTRACT))throw new InvalidOperationException("Invalid quantity member type "+raw);
                    changes.Add(Tuple.Create(e,i>=n));
                }
            }
            // A rejected row keeps its last valid geometry. Independent valid
            // rows still update, including their associated machining features.
            var accepted=new HashSet<string>(validRows.Select(row=>(string)row["count"]));
            var memberIds=new HashSet<int>(validRows.SelectMany(row=>(object[])row["slots"]).SelectMany(slot=>(object[])slot).Select(Convert.ToInt32));
            var activePlan=new Dictionary<string,object>(q);
            activePlan["rows"]=validRows.Cast<object>().ToArray();
            activePlan["poses"]=((object[])q["poses"]).Select(O).Where(p=>accepted.Contains((string)p["count"])).Cast<object>().ToArray();
            activePlan["mates"]=((object[])q["mates"]).Select(O).Where(m=>memberIds.Contains(Convert.ToInt32(m["id"]))).Cast<object>().ToArray();
            Position(scene,activePlan);
            var changed=changes.Where(c=>c.Item1.GetStateStatus(eZElementState.Z_SUPPRESSED)!=c.Item2).ToArray();
            if(changed.Length>0){
                var batchUtility=scene.GetTopElement().Application.Utility;
                foreach(bool suppress in new[]{true,false}){
                    var members=changed.Where(c=>c.Item2==suppress).ToArray();
                    if(members.Length==0)continue;
                    var array=batchUtility.CreateEmptyIUnknownArray();
                    foreach(var member in members)array.AddElement(member.Item1);
                    batchUtility.SetSuppressStateMultiple(array,suppress);
                    foreach(var member in members)if(member.Item1.GetStateStatus(eZElementState.Z_SUPPRESSED)!=suppress)member.Item1.SetSuppressState(suppress);
                }
                // Imported catalog solids are rigid. Rebuild only plates/profiles
                // whose subtract features changed, not every imported vendor body.
                var targets=changed.Where(c=>c.Item1.Type!=eZElementType.Z_ELEMENT_ASSEMBLY&&c.Item1.Type!=eZElementType.Z_ELEMENT_PART)
                    .Select(c=>c.Item1.GetOwnerPart()).GroupBy(e=>e.Id).Select(g=>g.First());
                foreach(var target in targets)((IZPart)target).Update();
                scene.Update();scene.Redraw();
            }
            MateCuts(scene,activePlan);
            if(errors.Count>0)throw new InvalidOperationException(String.Join("; ",errors)+" Pozostałe poprawne rzędy zostały przeliczone.");
            return changed.Length;
        }
    }
}
