using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using RockPro.CAD;

internal static class InventoryUiChecks {
 const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
 static T Field<T>(object form,string name){return (T)form.GetType().GetField(name,Flags).GetValue(form);}
 static Task Reload(object form){return (Task)form.GetType().GetMethod("Reload",Flags).Invoke(form,new object[0]);}
 static void Wait(Task task){var watch=System.Diagnostics.Stopwatch.StartNew();while(!task.IsCompleted){if(watch.ElapsedMilliseconds>30000)throw new TimeoutException("Inventory UI read timed out");Application.DoEvents();Thread.Sleep(5);}task.GetAwaiter().GetResult();Application.DoEvents();}
 internal static void Run(){
  var serializer=new JavaScriptSerializer {MaxJsonLength=16000000};string path=Path.GetFullPath(Path.Combine(Application.StartupPath,"..","..","qa","fixtures","inventory-ui.json"));
  var fixture=Rpc.Obj(serializer.DeserializeObject(File.ReadAllText(path)));if(!Convert.ToBoolean(fixture["synthetic_test"]))throw new Exception("Inventory fixture is not synthetic");
  bool previousCheck=Control.CheckForIllegalCrossThreadCalls;var context=SynchronizationContext.Current;bool previousLanguage=UiText.IsEnglish;
  Control.CheckForIllegalCrossThreadCalls=true;
  try{
   foreach(bool english in new[]{false,true})foreach(float scale in new[]{1f,1.5f}){
    UiText.SetLanguage(english,false);int calls=0,owner=Thread.CurrentThread.ManagedThreadId;
    using(var form=new InventoryForm(delegate(string name,object args){
     calls++;if(Thread.CurrentThread.ManagedThreadId==owner)throw new Exception("Inventory backend ran on UI thread");
     if(name=="get_inventory")return RevisionUi.Clone(Rpc.Obj(fixture["inventory"]));
     if(name=="get_inventory_history")return RevisionUi.Clone(Rpc.Obj(fixture["history"]));
     throw new Exception("Inventory viewer attempted a write: "+name);
    },false)){
     form.Show();form.Scale(new SizeF(scale,scale));Application.DoEvents();if(calls!=0)throw new Exception("Inventory preview called backend automatically");
     SynchronizationContext.SetSynchronizationContext(null);Wait(Reload(form));
     if(calls!=2||Field<DataGridView>(form,"lots").Rows.Count!=4||Field<DataGridView>(form,"history").Rows.Count!=10)throw new Exception("Inventory reads/counts incorrect");
     bool balance=false,quarantine=false;
     foreach(DataGridViewRow row in Field<DataGridView>(form,"lots").Rows){
      if(Convert.ToString(row.Cells[0].Value)=="locks-test"){balance=true;if(Convert.ToInt64(row.Cells[4].Value)!=8||Convert.ToInt64(row.Cells[5].Value)!=3||Convert.ToInt64(row.Cells[6].Value)!=5)throw new Exception("UI subtracted reservations twice");}
      if(Convert.ToString(row.Cells[0].Value)=="quarantine-test"){quarantine=true;if(Convert.ToInt64(row.Cells[6].Value)!=0)throw new Exception("Quarantine shown as free");}
      if(!Convert.ToString(row.Cells[10].Value).Contains(english?"SYNTHETIC":"TEST"))throw new Exception("Synthetic inventory provenance hidden");
     }
     if(!balance||!quarantine||Convert.ToInt64(Field<DataGridView>(form,"deliveries").Rows[0].Cells[5].Value)!=25)throw new Exception("Missing balance or outstanding delivery");
     foreach(string key in new[]{"reload","details"}){var button=Field<Button>(form,key);if(!button.Visible||!button.Parent.ClientRectangle.Contains(button.Bounds)||button.Width<button.GetPreferredSize(Size.Empty).Width)throw new Exception("Inventory action clipped "+key+" "+english+" "+scale);}
     string folder=Environment.GetEnvironmentVariable("ROCKPRO_UI_EVIDENCE");if(!String.IsNullOrEmpty(folder)){Directory.CreateDirectory(folder);using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(Path.Combine(folder,"inventory-"+(english?"en":"pl")+"-"+(scale>1?"150":"100")+".png"));}}
     foreach(string key in new[]{"lots","reservations","deliveries","history"})if(!Field<DataGridView>(form,key).ReadOnly)throw new Exception("Inventory table allows editing: "+key);
     var tabControl=Field<TabControl>(form,"tabs");
     for(int tab=1;tab<4;tab++){
      tabControl.SelectedIndex=tab;Application.DoEvents();
      if(tab==3){Field<DataGridView>(form,"history").Rows[0].Selected=true;Application.DoEvents();if(!Field<Button>(form,"details").Enabled)throw new Exception("History receipt not selectable");}
      if(!english&&scale==1&&!String.IsNullOrEmpty(folder))using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(Path.Combine(folder,"inventory-tab-"+tab+"-pl-100.png"));}
     }
     UiText.SetLanguage(!english,false);if(calls!=2||Field<DataGridView>(form,"lots").Rows.Count!=4)throw new Exception("Language switch reread inventory or lost data");
     form.Close();
    }
   }
   int attempts=0;bool fail=false;
   using(var form=new InventoryForm(delegate(string name,object args){
    attempts++;if(name=="get_inventory"){var data=RevisionUi.Clone(Rpc.Obj(fixture["inventory"]));if(fail)Rpc.Obj(Rpc.Rows(data["lots"])[0])["on_hand"]=999;return data;}
    if(name=="get_inventory_history"){if(fail)throw new Exception("SIMULATED_HISTORY_UNAVAILABLE");return RevisionUi.Clone(Rpc.Obj(fixture["history"]));}
    throw new Exception("Unexpected write");
   },false)){
    form.Show();Application.DoEvents();Wait(Reload(form));var grid=Field<DataGridView>(form,"lots");object old=grid.Rows[0].Cells[4].Value;
    fail=true;Wait(Reload(form));
    if(attempts!=4||!Equals(grid.Rows[0].Cells[4].Value,old)||!Field<Label>(form,"status").Text.Contains("SIMULATED_HISTORY_UNAVAILABLE")||!Field<Button>(form,"reload").Enabled)throw new Exception("Failed read mixed old/new data, retried or stayed busy");
    UiText.SetLanguage(!UiText.IsEnglish,false);if(!Field<Label>(form,"status").Text.Contains(UiText.IsEnglish?"outdated":"nieaktualne"))throw new Exception("Language switch cleared stale-data warning");form.Close();
   }
   using(var form=new InventoryForm(delegate(string name,object args){return name=="get_inventory"?new Dictionary<string,object>{{"lots",new object[0]},{"reservations",new object[0]},{"deliveries",new object[0]}}:new Dictionary<string,object>{{"events",new object[0]}};},false)){
    form.Show();Application.DoEvents();Wait(Reload(form));if(Field<DataGridView>(form,"lots").Rows.Count!=0||Field<Button>(form,"details").Enabled)throw new Exception("Empty inventory invented rows or a selected receipt");form.Close();
   }
   Console.WriteLine("PASS: inventory viewer PL/EN 100/150, physical/held/free balances, quarantine, deliveries/history/provenance, no writes, stale/empty states and owner-thread async");
  }finally{SynchronizationContext.SetSynchronizationContext(context);Control.CheckForIllegalCrossThreadCalls=previousCheck;UiText.SetLanguage(previousLanguage,false);}
 }
}
