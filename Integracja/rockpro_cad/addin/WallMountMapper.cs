// Wall-local rigid mounting. Geometry stays native; only plywood/profile cuts are copied.
using System;
using System.Linq;
using System.Collections.Generic;
using System.Globalization;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;
namespace RockPro.CAD {
 public static class WallMountMapper {
  public static Dictionary<string,object> O(object x){return (Dictionary<string,object>)x;}
  public static double[] N(object x){return ((Array)x).Cast<object>().Select(Convert.ToDouble).ToArray();}
  static double V(IZSceneDoc s,string n){return s.ParameterMgr.GetParameterByName(n).Value*1000;}
  static double Scalar(IZSceneDoc s,string n){return s.ParameterMgr.GetParameterByName(n).Value;}
  public static double[] Point(double[] m,double[] p){return Enumerable.Range(0,3).Select(j=>m[12+j]+Enumerable.Range(0,3).Sum(k=>p[k]*m[k*4+j])).ToArray();}
  public static double[] Relative(double[] world,double[] frame){var m=new double[16];m[15]=1;for(int a=0;a<3;a++){for(int b=0;b<3;b++)m[a*4+b]=Enumerable.Range(0,3).Sum(k=>world[a*4+k]*frame[b*4+k]);m[12+a]=Enumerable.Range(0,3).Sum(k=>(world[12+k]-frame[12+k])*frame[a*4+k]);}return m;}
  public static double[] Compose(double[] local,double[] frame){var m=new double[16];m[15]=1;for(int a=0;a<3;a++)for(int b=0;b<3;b++)m[a*4+b]=Enumerable.Range(0,3).Sum(k=>local[a*4+k]*frame[k*4+b]);var p=Point(frame,local.Skip(12).Take(3).ToArray());for(int i=0;i<3;i++)m[12+i]=p[i];return m;}
  public static double[] LocalPoint(double[] point,double[] frame){return Enumerable.Range(0,3).Select(j=>Enumerable.Range(0,3).Sum(k=>(point[k]-frame[12+k])*frame[j*4+k])).ToArray();}
  public static string WallName(int wall){return new[]{"","przód","tył","lewa","prawa","góra","dno"}[wall];}
  public static int Panel(Dictionary<string,object> q,int wall,int section){return Convert.ToInt32(O(O(q["wall_targets"])[section.ToString()])[wall.ToString()]);}
  public static double[] Frame(IZSceneDoc s,Dictionary<string,object> q,int wall,int section,bool joint,out double length,out double height){
   if(wall<1||wall>6||section<1||section>2||(wall==5&&section!=2)||(wall==6&&section!=1)||(joint&&wall>4))throw new InvalidOperationException("Nie ma takiej powierzchni montażowej/złącza. Góra należy do czapki, dno do korpusu; zamki wymagają pionowego złącza.");
   var u=(IZSceneDocUtility)s;var b=MountCountController.WorldBounds((IZPart)u.GetElementById(Panel(q,wall,section)));var floor=MountCountController.WorldBounds((IZPart)u.GetElementById(Panel(q,6,1)));
   double[] x,y,z,origin;
   double low=b[2];if(joint){var bottom=MountCountController.WorldBounds((IZPart)u.GetElementById(Panel(q,wall,1)));var top=MountCountController.WorldBounds((IZPart)u.GetElementById(Panel(q,wall,2)));low=(bottom[5]+top[2])/2;}
   if(wall==1){x=new[]{1.0,0,0};y=new[]{0.0,0,1};z=new[]{0.0,-1,0};origin=new[]{floor[0],b[1],low};}
   else if(wall==2){x=new[]{-1.0,0,0};y=new[]{0.0,0,1};z=new[]{0.0,1,0};origin=new[]{floor[3],b[4],low};}
   else if(wall==3){x=new[]{0.0,-1,0};y=new[]{0.0,0,1};z=new[]{-1.0,0,0};origin=new[]{b[0],floor[4],low};}
   else if(wall==4){x=new[]{0.0,1,0};y=new[]{0.0,0,1};z=new[]{1.0,0,0};origin=new[]{b[3],floor[1],low};}
   else if(wall==5){x=new[]{1.0,0,0};y=new[]{0.0,1,0};z=new[]{0.0,0,1};origin=new[]{floor[0],floor[1],b[5]};}
   else{x=new[]{1.0,0,0};y=new[]{0.0,-1,0};z=new[]{0.0,0,-1};origin=new[]{floor[0],floor[4],b[2]};}
   length=wall==3||wall==4?(floor[4]-floor[1])*1000:(floor[3]-floor[0])*1000;
   height=wall>4?(floor[4]-floor[1])*1000:(b[5]-b[2])*1000;
   return x.Concat(new[]{0.0}).Concat(y).Concat(new[]{0.0}).Concat(z).Concat(new[]{0.0}).Concat(origin).Concat(new[]{1.0}).ToArray();
  }
  public static double[] Anchor(double[] frame,double u,double v){var m=(double[])frame.Clone();var p=Point(frame,new[]{u/1000,v/1000,0});for(int k=0;k<3;k++)m[12+k]=p[k];return m;}
  public static double[] BoundsInFrame(double[] localBox,double[] matrix,double[] frame){var points=Enumerable.Range(0,8).Select(mask=>LocalPoint(Point(matrix,Enumerable.Range(0,3).Select(k=>localBox[k+3*((mask>>k)&1)]).ToArray()),frame)).ToArray();return new[]{points.Min(p=>p[0])*1000,points.Min(p=>p[1])*1000,points.Max(p=>p[0])*1000,points.Max(p=>p[1])*1000};}
  public static bool Overlap(double[] a,double[] b,double gap){return a[0]<b[2]+gap-1e-6&&a[2]+gap>b[0]+1e-6&&a[1]<b[3]+gap-1e-6&&a[3]+gap>b[1]+1e-6;}
  static bool Pose(IZSceneElement e,double[] m){if(MountCountController.Matrix(e).Zip(m,(a,b)=>Math.Abs(a-b)).Max()<1e-10)return false;MountCountController.SetWorld(e,m);return true;}
  static void Label(IZElement root,string name){
   if(root.Name==name){
    if(root.GetChildrenCount()==0)return;
    object raw;root.GetChildrenZArray().Get(0,out raw);
    if(((IZElement)raw).Name.StartsWith(name+" — podczęść ",StringComparison.Ordinal))return;
   }
   root.Name=name;int index=0;
   // Imported parts may expose non-renamable internal model objects. Label
   // complete parts/assemblies only; retain their native feature histories.
   Action<IZElement> children=null;children=e=>{
    if(e.Type!=eZElementType.Z_ELEMENT_ASSEMBLY)return;
    var list=e.GetChildrenZArray();for(int i=0;i<e.GetChildrenCount();i++){
     object raw;list.Get(i,out raw);var child=(IZElement)raw;
     if(child.Type!=eZElementType.Z_ELEMENT_PART&&child.Type!=eZElementType.Z_ELEMENT_ASSEMBLY)continue;
     child.Name=name+" — podczęść "+(++index).ToString("D2")+" — ID "+child.Id;children(child);
    }
   };
   children(root);
  }
  class Plan {public Dictionary<string,object> Row,Bag;public string Key;public int Wall,Section,Count;public double[] Frame;public double U,V,Span;public List<double[]> Rects=new List<double[]>();public string Error;}
  public static string[] Apply(IZSceneDoc s,Dictionary<string,object> q){
   if(!q.ContainsKey("portable_rows"))return new string[0];var utility=(IZSceneDocUtility)s;var plans=new List<Plan>();
   foreach(var row in ((object[])q["portable_rows"]).Select(O)){
    var p=new Plan{Row=row,Key=(string)row["key"]};plans.Add(p);
    try{
     double wall=Scalar(s,(string)row["wall"]),sec=row.ContainsKey("section")?Scalar(s,(string)row["section"]):1;
     if(wall!=Math.Round(wall)||sec!=Math.Round(sec))throw new InvalidOperationException("Ściana i sekcja muszą być liczbami całkowitymi.");p.Wall=(int)wall;p.Section=(int)sec;
     bool joint=(string)row["kind"]=="latch";double length,height;p.Frame=Frame(s,q,p.Wall,p.Section,joint,out length,out height);
     p.U=V(s,(string)row["center"]);p.V=V(s,(string)row["vertical"]);p.Span=V(s,(string)row["spread"]);
     if(joint){
      var lower=MountCountController.WorldBounds((IZPart)utility.GetElementById(Panel(q,p.Wall,1)));
      var upper=MountCountController.WorldBounds((IZPart)utility.GetElementById(Panel(q,p.Wall,2)));
      double allowance=Math.Max(0,(upper[2]-lower[5])*500);
      if(Math.Abs(p.V)>allowance+1e-6)throw new InvalidOperationException("Pion zamka poza strefą złącza. Dopuszczalne ±"+allowance.ToString("0.##",CultureInfo.GetCultureInfo("pl-PL"))+" mm, wynikające z połowy szczeliny między sklejkami.");
     }
     double count=Scalar(s,(string)row["count"]);var roots=(object[])row["roots"];var footprint=N(row["footprint"]);
     string error=MountRowLayout.Validate(count,0,roots.Length,length,p.U,p.Span,2*Math.Max(Math.Abs(footprint[0]),Math.Abs(footprint[2])),12,35);
     if(error!=null)throw new InvalidOperationException(error);p.Count=(int)count;
     var bags=((object[])row["bags"]).Select(O);p.Bag=bags.Single(b=>Convert.ToInt32(b["wall"])==p.Wall&&Convert.ToInt32(b["section"])==(joint?0:p.Section));
     for(int i=0;i<p.Count;i++){double center=p.U+(p.Count==1?0:(-.5+(double)i/(p.Count-1))*p.Span);var rect=new[]{center+footprint[0],p.V+footprint[1],center+footprint[2],p.V+footprint[3]};
      if(!joint&&(rect[1]<35-1e-6||rect[3]>height-35+1e-6))throw new InvalidOperationException("Okucie wychodzi poza wysokość wybranej ścianki albo strefę profilu. Zmień PozycjaV.");p.Rects.Add(rect);}
     foreach(var obstacle in ((object[])q["wall_obstacles"]).Select(O)){
      if(Convert.ToInt32(obstacle["wall"])!=p.Wall)continue;
      var element=(IZSceneElement)utility.GetElementById(Convert.ToInt32(obstacle["id"]));if(((IZElement)element).GetStateStatus(eZElementState.Z_SUPPRESSED))continue;
      var rect=BoundsInFrame(N(obstacle["local_box"]),MountCountController.Matrix(element),p.Frame);
      if(p.Rects.Any(r=>Overlap(r,rect,12)))throw new InvalidOperationException("Kolizja z istniejącym okuciem ID "+obstacle["id"]+" na ścianie "+WallName(p.Wall)+". Zmień położenie U/V lub rozstaw.");
     }
    }catch(Exception ex){p.Error=ex.GetBaseException().Message;}
   }
   // Compare desired rows in global coordinates: different section frames have different V origins.
   foreach(var a in plans.Where(p=>p.Error==null).ToArray())foreach(var b in plans.Where(p=>p.Error==null&&p!=a).ToArray()){
    if(a.Wall!=b.Wall)continue;var shifted=b.Rects.Select(r=>{var points=new[]{LocalPoint(Point(b.Frame,new[]{r[0]/1000,r[1]/1000,0}),a.Frame),LocalPoint(Point(b.Frame,new[]{r[2]/1000,r[3]/1000,0}),a.Frame)};return new[]{points.Min(p=>p[0])*1000,points.Min(p=>p[1])*1000,points.Max(p=>p[0])*1000,points.Max(p=>p[1])*1000};});
    if(a.Rects.Any(r=>shifted.Any(t=>Overlap(r,t,12)))){a.Error="Kolizja z rzędem "+b.Key+" na tej samej ścianie.";b.Error="Kolizja z rzędem "+a.Key+" na tej samej ścianie.";}
   }
   // Invalid rows keep their last valid physical location; that occupied space
   // must still prevent another row from moving through them.
   bool retry;
   do{
    retry=false;
    foreach(var a in plans.Where(p=>p.Error==null).ToArray())foreach(var b in plans.Where(p=>p.Error!=null).ToArray()){
     if(!b.Row.ContainsKey("last_wall")||a.Wall!=Convert.ToInt32(b.Row["last_wall"]))continue;
     var boxes=(object[])b.Row["root_boxes"];
     foreach(var slot in (object[])b.Row["roots"]){var ids=(object[])slot;
      for(int k=0;k<ids.Length;k++){
       var element=utility.GetElementById(Convert.ToInt32(ids[k]));if(element.GetStateStatus(eZElementState.Z_SUPPRESSED))continue;
       var rect=BoundsInFrame(N(boxes[k]),MountCountController.Matrix((IZSceneElement)element),a.Frame);
       if(a.Rects.Any(r=>Overlap(r,rect,12))){a.Error="Kolizja z ostatnim poprawnym układem rzędu "+b.Key+". Popraw najpierw jego błąd.";retry=true;break;}
      }if(a.Error!=null)break;
     }
    }
   }while(retry);
   var dirty=new Dictionary<int,IZPart>();
   foreach(var p in plans.Where(p=>p.Error==null)){
    var row=p.Row;var roots=(object[])row["roots"];var rootPoses=(object[])row["root_poses"];
    Action<int,bool> suppress=(id,value)=>{var e=utility.GetElementById(id);if(e.GetStateStatus(eZElementState.Z_SUPPRESSED)==value)return;e.SetSuppressState(value);if(e is IZFeature){var part=(IZPart)e.GetOwnerPart();dirty[((IZElement)part).Id]=part;}};
    foreach(var bag in ((object[])row["bags"]).Select(O))foreach(var spec in ((object[])bag["features"]).Select(O))suppress(Convert.ToInt32(spec["id"]),bag!=p.Bag||Convert.ToInt32(spec["slot"])>=p.Count);
    for(int i=0;i<roots.Length;i++){
     var anchor=Anchor(p.Frame,p.U+(p.Count<=1?0:(-.5+(double)i/(p.Count-1))*p.Span),p.V);var members=(object[])roots[i];
     for(int k=0;k<members.Length;k++){int id=Convert.ToInt32(members[k]);suppress(id,i>=p.Count);if(i>=p.Count)continue;Pose((IZSceneElement)utility.GetElementById(id),Compose(N(rootPoses[k]),anchor));Label(utility.GetElementById(id),"RockPro | "+((string)row["kind"]=="latch"?"Zamek L905/915":"Uchwyt H7159")+" — "+((string)row["kind"]=="latch"?(k==0?"czapka — górna połówka":"korpus — dolna połówka"):(p.Section==2?"czapka":"korpus"))+" — "+WallName(p.Wall)+" — "+p.Key+" — pozycja "+(i+1));}
    }
    foreach(var spec in ((object[])p.Bag["features"]).Select(O)){
     int i=Convert.ToInt32(spec["slot"]);if(i>=p.Count)continue;var anchor=Anchor(p.Frame,p.U+(p.Count<=1?0:(-.5+(double)i/(p.Count-1))*p.Span),p.V);var e=utility.GetElementById(Convert.ToInt32(spec["id"]));
     if(Pose((IZSceneElement)e,Compose(N(spec["relative"]),anchor))){var part=(IZPart)e.GetOwnerPart();dirty[((IZElement)part).Id]=part;}
    }
   }
   foreach(var part in dirty.Values)part.Update();s.Update();
   for(int pass=0;pass<2;pass++){
    dirty.Clear();foreach(var p in plans.Where(p=>p.Error==null))foreach(var spec in ((object[])p.Bag["features"]).Select(O)){
     int i=Convert.ToInt32(spec["slot"]);if(i>=p.Count)continue;var anchor=Anchor(p.Frame,p.U+(p.Count<=1?0:(-.5+(double)i/(p.Count-1))*p.Span),p.V);var expected=Point(anchor,N(spec["center"]));var e=utility.GetElementById(Convert.ToInt32(spec["id"]));var actual=MountCountController.ContourCenter(((IZExtrudeFeature)e).CrossSection);
     if(expected.Zip(actual,(a,b)=>Math.Abs(a-b)).Max()<1e-10)continue;var world=MountCountController.Matrix((IZSceneElement)e);for(int k=0;k<3;k++)world[12+k]+=expected[k]-actual[k];Pose((IZSceneElement)e,world);var part=(IZPart)e.GetOwnerPart();dirty[((IZElement)part).Id]=part;
    }if(dirty.Count==0)break;foreach(var part in dirty.Values)part.Update();s.Update();
   }
   foreach(var p in plans.Where(p=>p.Error==null)){p.Row["last_wall"]=p.Wall;p.Row["last_section"]=p.Section;}
   s.GetTopElement().get_CustomPropMgr(false).SetValueByName(MountCountController.Property,new JavaScriptSerializer{MaxJsonLength=4000000}.Serialize(q));
   return plans.Where(p=>p.Error!=null).Select(p=>p.Key+": "+p.Error).ToArray();
  }
 }
}
