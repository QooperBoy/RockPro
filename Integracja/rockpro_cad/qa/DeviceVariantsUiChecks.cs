using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using RockPro.CAD;

internal static class DeviceVariantsUiChecks {
 const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
 static T Field<T>(object form,string name){return (T)form.GetType().GetField(name,Flags).GetValue(form);}
 static void Set(object form,string name,object value){form.GetType().GetField(name,Flags).SetValue(form,value);}
 static object Invoke(object form,string name,params object[] args){return form.GetType().GetMethod(name,Flags).Invoke(form,args);}
 static void Wait(Task task){var watch=System.Diagnostics.Stopwatch.StartNew();while(!task.IsCompleted){if(watch.ElapsedMilliseconds>30000)throw new TimeoutException("Device UI operation did not complete in 30 seconds");Application.DoEvents();System.Threading.Thread.Sleep(5);}task.GetAwaiter().GetResult();Application.DoEvents();}
 static Dictionary<string,object> Data(object value){var serializer=new JavaScriptSerializer {MaxJsonLength=16000000};return Rpc.Obj(serializer.DeserializeObject(serializer.Serialize(value)));}
 internal static void Run(){
  Control.CheckForIllegalCrossThreadCalls=true;
  string fixturePath=Path.GetFullPath(Path.Combine(Application.StartupPath,"..","..","qa","fixtures","device-layout-ui.json"));
  var fixture=Rpc.Obj(new JavaScriptSerializer {MaxJsonLength=16000000}.DeserializeObject(File.ReadAllText(fixturePath)));
  if(!Convert.ToBoolean(fixture["synthetic_test"]))throw new Exception("UI fixture scope missing");
  var layout=Rpc.Obj(fixture["layout"]);var binding=Rpc.Obj(layout["device_binding"]);var spec=Rpc.Obj(layout["spec"]);
  foreach(bool english in new[]{false,true})foreach(float scale in new[]{1f,1.5f}){
   Console.WriteLine("Device UI: catalog chooser "+english+" "+scale);
   UiText.SetLanguage(english,false);int saves=0;
   using(var form=new DeviceVariantsForm("UI-ONLY",delegate(string name,object args){
    if(name=="get_layout")return RevisionUi.Clone(layout);if(name=="list_device_records")return RevisionUi.Clone(Rpc.Obj(fixture["catalog"]));
    if(name=="preview_catalog_layouts"){var request=Data(args);if(Convert.ToInt32(request["expected_device_revision"])!=1)throw new Exception("Catalog revision not pinned");return RevisionUi.Clone(Rpc.Obj(fixture["proposals"]));}
    saves++;throw new Exception("Unexpected write/tool: "+name);},false)){
    form.Show();form.Scale(new SizeF(scale,scale));Application.DoEvents();
    Console.WriteLine("Device UI: loading catalog");Wait((Task)Invoke(form,"Run",new Func<Task>(delegate{return (Task)Invoke(form,"LoadData");})));
    Field<CheckedListBox>(form,"orientations").SetItemChecked(2,true);
    Console.WriteLine("Device UI: calculating catalog proposals");Wait((Task)Invoke(form,"Run",new Func<Task>(delegate{return (Task)Invoke(form,"Calculate");})));
    if(form.SelectedSpec!=null||Field<Button>(form,"accept").Enabled)throw new Exception("Proposal auto-selected");
    var grid=Field<DataGridView>(form,"variants");if(grid.Rows.Count<1||grid.Rows.Count>3)throw new Exception("Proposal table limit wrong");
    grid.Rows[0].Selected=true;Invoke(form,"SelectProposal");Application.DoEvents();
    if(form.SelectedSpec==null||form.SelectedBinding==null||form.BaseLayoutRevision!=7||!Field<Button>(form,"accept").Enabled)throw new Exception("Explicit proposal selection missing binding/version");
    Field<Label>(form,"status").Text=english?"UI test: synthetic data; no CAD or database writes.":"Próba okna: dane syntetyczne; bez CAD i zapisu do bazy.";
    foreach(string key in new[]{"calculate","accept"}){var button=Field<Button>(form,key);if(!button.Visible||!button.Parent.ClientRectangle.Contains(button.Bounds)||button.Width<button.GetPreferredSize(Size.Empty).Width)throw new Exception("Catalog action clipped: "+key+" "+english+" "+scale);}
    Field<Button>(form,"calculate").Focus();foreach(Control control in form.Controls[0].Controls){var scroll=control as Panel;if(scroll!=null&&scroll.AutoScroll)scroll.AutoScrollPosition=Point.Empty;}Application.DoEvents();
    string folder=Environment.GetEnvironmentVariable("ROCKPRO_UI_EVIDENCE");if(!String.IsNullOrEmpty(folder)){Directory.CreateDirectory(folder);using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(Path.Combine(folder,"catalog-"+(english?"en":"pl")+"-"+(scale>1?"150":"100")+".png"));}}
    var inputs=Field<Dictionary<string,NumericUpDown>>(form,"inputs");inputs["count"].Value=3;
    if(form.SelectedSpec!=null||Field<Button>(form,"accept").Enabled)throw new Exception("Changed input retained old proposal");
    Console.WriteLine("Device UI: language switch");UiText.SetLanguage(!english,false);if(inputs["count"].Value!=3||form.BaseLayoutRevision!=7)throw new Exception("Language switch reset proposal inputs/version");
    if(saves!=0)throw new Exception("Catalog chooser wrote automatically");form.Close();
   }
  }
  UiText.SetLanguage(false,false);
  foreach(bool conflict in new[]{false,true}){
   Console.WriteLine("Device UI: bound save, conflict="+conflict);
   int saves=0;
   using(var form=new LayoutForm("UI-ONLY",spec,binding,7,delegate(string name,object args){
    if(name=="get_layout"){var current=RevisionUi.Clone(layout);current["revision"]=9;return current;}
    if(name=="preview_bound_device_layout")return RevisionUi.Clone(layout);
    if(name=="save_bound_device_layout"){saves++;var request=Data(args);if(Convert.ToInt64(request["expected_revision"])!=7)throw new Exception("Stale proposal adopted current version");
     if(Convert.ToDouble(Rpc.Obj(request["spec"])["gap"])!=31)throw new Exception("Constructor edits lost");if(conflict)throw new Exception("LAYOUT_CONFLICT");var saved=RevisionUi.Clone(layout);saved["revision"]=8;return saved;}
    throw new Exception("Unexpected tool "+name);},false,false)){
    form.Show();Application.DoEvents();Console.WriteLine("Device UI: loading bound editor");Wait((Task)Invoke(form,"LoadLayout"));
    var fields=Field<Dictionary<string,Control>>(form,"fields");foreach(string axis in new[]{"x","y","z"})if(fields[axis].Enabled)throw new Exception("Source dimension editable while bound");
    if(Field<long>(form,"layoutRevision")!=7)throw new Exception("Proposal token refreshed on load");
    ((NumericUpDown)fields["gap"]).Value=31;Console.WriteLine("Device UI: saving bound editor");Wait((Task)Invoke(form,"Persist",false));
    if(saves!=1||Field<long>(form,"layoutRevision")!=(conflict?7:8)||((NumericUpDown)fields["gap"]).Value!=31)throw new Exception("Bound layout write retried or discarded draft");
    Set(form,"dirty",false);form.Close();
   }
  }
  foreach(bool conflict in new[]{false,true}){
   Console.WriteLine("Device UI: explicit unlink, conflict="+conflict);
   int unlinks=0;
   using(var form=new LayoutForm("UI-ONLY",spec,binding,7,delegate(string name,object args){
    if(name=="get_layout"||name=="preview_bound_device_layout")return RevisionUi.Clone(layout);
    if(name=="preview_layout")return RevisionUi.Clone(layout);
    if(name=="unlink_layout_device"){unlinks++;if(Convert.ToInt64(Data(args)["expected_revision"])!=7)throw new Exception("Unlink token refreshed");if(conflict)throw new Exception("LAYOUT_CONFLICT");return new Dictionary<string,object>{{"revision",8}};}
    throw new Exception("Unexpected tool "+name);},false,false)){
    form.Show();Application.DoEvents();Console.WriteLine("Device UI: loading unlink editor");Wait((Task)Invoke(form,"LoadLayout"));Console.WriteLine("Device UI: unlinking");Wait((Task)Invoke(form,"UnlinkSource"));
    if(unlinks!=1||Field<long>(form,"layoutRevision")!=(conflict?7:8))throw new Exception("Unlink retried or refreshed revision");
    var fields=Field<Dictionary<string,Control>>(form,"fields");if(fields["x"].Enabled==conflict)throw new Exception("Unlink failure changed source ownership");
    Set(form,"dirty",false);form.Close();
   }
  }
  Console.WriteLine("PASS: catalog proposals PL/EN 100/150, explicit selection, bound edits/CAS and explicit unlink without automatic writes");
  Control.CheckForIllegalCrossThreadCalls=false;
 }
}
