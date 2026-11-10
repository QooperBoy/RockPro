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

internal static class InventoryCommandUiChecks {
 const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
 static T Field<T>(object form,string key){return (T)form.GetType().GetField(key,Flags).GetValue(form);}
 static Dictionary<string,object> Data(object value){var json=new JavaScriptSerializer();return Rpc.Obj(json.DeserializeObject(json.Serialize(value)));}
 static void Run(object form,string method){var task=(Task)form.GetType().GetMethod("Run",Flags).Invoke(form,new object[]{new Func<Task>(delegate{return (Task)form.GetType().GetMethod(method,Flags).Invoke(form,new object[0]);})});var watch=System.Diagnostics.Stopwatch.StartNew();while(!task.IsCompleted){if(watch.ElapsedMilliseconds>30000)throw new TimeoutException("Inventory command UI timed out");Application.DoEvents();Thread.Sleep(5);}task.GetAwaiter().GetResult();Application.DoEvents();}
 static void Choose(ComboBox combo,string id){for(int i=0;i<combo.Items.Count;i++)if(combo.Items[i].ToString().StartsWith(id+" •")){combo.SelectedIndex=i;return;}throw new Exception("Missing inventory selection "+id);}
 sealed class Backend {
  internal Dictionary<string,object> Inventory,Current,Submitted;
  internal int Prepares,Executes,Cancels;internal string Failure="";
  internal Dictionary<string,object> Call(string name,object args){var request=Data(args);
   if(name=="get_inventory")return RevisionUi.Clone(Inventory);
   if(name=="list_inventory_intents")return new Dictionary<string,object>{{"intents",Current==null?new object[0]:new object[]{RevisionUi.Clone(Current)}}};
   if(name=="prepare_inventory_command"){
    Prepares++;Submitted=request;Current=RevisionUi.Clone(request);Current["state"]="prepared";Current["command_sha256"]=new String('a',64);Current["receipt"]=null;Current["diagnostic"]=null;Current["production_approved"]=false;
    if(Failure=="prepare-not-stored"&&Prepares==1){Current=null;throw new TimeoutException("SIMULATED_PREPARE_NOT_STORED");}
    if(Failure=="prepare")throw new TimeoutException("SIMULATED_LOST_PREPARE_REPLY");return RevisionUi.Clone(Current);
   }
   if(name=="get_inventory_intent"){if(Current==null)throw new Exception("INVENTORY_INTENT_NOT_FOUND");if(Rpc.Str(request,"operation_id")!=Rpc.Str(Current,"operation_id"))throw new Exception("Changed recovery ID");return RevisionUi.Clone(Current);}
   if(name=="execute_inventory_intent"){
    Executes++;if(Rpc.Str(request,"operation_id")!=Rpc.Str(Current,"operation_id"))throw new Exception("Changed execution ID");Current["state"]=Failure=="conflict"?"rejected":"committed";
    if(Failure=="execute")throw new TimeoutException("SIMULATED_LOST_EXECUTE_REPLY");if(Failure=="conflict")throw new Exception("INVENTORY_REVISION_CONFLICT");return RevisionUi.Clone(Current);
   }
   if(name=="cancel_inventory_intent"){Cancels++;Current["state"]="cancelled";return RevisionUi.Clone(Current);}
   throw new Exception("Unexpected tool/write: "+name);
  }
 }
 static InventoryCommandForm Open(Backend backend){var form=new InventoryCommandForm(backend.Call,false);form.Show();Application.DoEvents();SynchronizationContext.SetSynchronizationContext(null);Run(form,"LoadData");return form;}
 static void Draft(object form){Choose(Field<ComboBox>(form,"lots"),"locks-test");Field<TextBox>(form,"plan").Text="qa-plan";Field<TextBox>(form,"reservation").Text="qa-reservation";Field<TextBox>(form,"reference").Text="UI-only operator instruction";Field<NumericUpDown>(form,"quantity").Value=2;}
 static void AssertPrepared(InventoryCommandForm form,Backend backend){
  if(backend.Prepares!=1||backend.Executes!=0||Convert.ToInt64(backend.Submitted["expected_revision"])!=5||!Field<Button>(form,"execute").Enabled||Field<NumericUpDown>(form,"quantity").Enabled)throw new Exception("Preparation executed stock, refreshed CAS or left fields editable");
 }
 internal static void Run(){
  var json=new JavaScriptSerializer {MaxJsonLength=16000000};string path=Path.GetFullPath(Path.Combine(Application.StartupPath,"..","..","qa","fixtures","inventory-ui.json"));var fixture=Rpc.Obj(json.DeserializeObject(File.ReadAllText(path)));
  bool oldCheck=Control.CheckForIllegalCrossThreadCalls,oldLanguage=UiText.IsEnglish;var context=SynchronizationContext.Current;Control.CheckForIllegalCrossThreadCalls=true;
  try{
   foreach(bool english in new[]{false,true})foreach(float scale in new[]{1f,1.5f}){
    UiText.SetLanguage(english,false);var backend=new Backend {Inventory=Rpc.Obj(fixture["inventory"])};
    using(var form=Open(backend)){form.Scale(new SizeF(scale,scale));Application.DoEvents();Draft(form);Run(form,"Prepare");AssertPrepared(form,backend);
     foreach(string key in new[]{"prepare","execute","cancel","read","fresh"}){var button=Field<Button>(form,key);if(!button.Visible||!button.Parent.ClientRectangle.Contains(button.Bounds)||button.Width<button.GetPreferredSize(Size.Empty).Width)throw new Exception("Inventory command action clipped "+key+" "+english+" "+scale);}
     string folder=Environment.GetEnvironmentVariable("ROCKPRO_UI_EVIDENCE");if(!String.IsNullOrEmpty(folder)){Directory.CreateDirectory(folder);using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(Path.Combine(folder,"inventory-command-"+(english?"en":"pl")+"-"+(scale>1?"150":"100")+".png"));}}
     string id=Field<TextBox>(form,"operation").Text;UiText.SetLanguage(!english,false);if(id!=Field<TextBox>(form,"operation").Text||Field<TextBox>(form,"reference").Text!="UI-only operator instruction"||backend.Prepares!=1)throw new Exception("Language switch lost draft/ID or wrote data");
     Run(form,"Cancel");if(backend.Cancels!=1||backend.Executes!=0||!Field<Button>(form,"fresh").Enabled)throw new Exception("Request cancellation executed stock or lost terminal state");form.Close();
    }
   }
   UiText.SetLanguage(false,false);
   foreach(string failure in new[]{"execute","conflict","prepare"}){
    var backend=new Backend {Inventory=Rpc.Obj(fixture["inventory"]),Failure=failure};
    using(var form=Open(backend)){Draft(form);Run(form,"Prepare");string id=Field<TextBox>(form,"operation").Text;
     if(failure!="prepare")Run(form,"Execute");
     if(Field<Button>(form,"execute").Enabled||Field<Button>(form,"fresh").Enabled||!Field<Button>(form,"read").Enabled)throw new Exception("Uncertain reply allowed a new execution/ID");
     Run(form,"Read");if(backend.Prepares!=1||backend.Executes!=(failure=="prepare"?0:1)||Field<TextBox>(form,"operation").Text!=id||Field<NumericUpDown>(form,"quantity").Value!=2||Field<TextBox>(form,"reference").Text!="UI-only operator instruction")throw new Exception("Recovery retried writes or lost inputs/revision");
     if(failure!="prepare"&&!Field<Button>(form,"fresh").Enabled)throw new Exception("Recovered terminal outcome not reflected in UI");form.Close();
    }
   }
   var restored=new Backend {Inventory=Rpc.Obj(fixture["inventory"])};
   using(var first=Open(restored)){Draft(first);Run(first,"Prepare");first.Close();}
   using(var form=Open(restored)){
    if(restored.Prepares!=1||restored.Executes!=0||Field<ComboBox>(form,"requests").Items.Count!=1||Field<TextBox>(form,"operation").Text!="")throw new Exception("Reopening automatically selected/executed a request");
    Field<ComboBox>(form,"requests").SelectedIndex=0;Run(form,"OpenExisting");
    if(!Field<Button>(form,"execute").Enabled||!Field<TextBox>(form,"summary").Text.Contains("UI-only operator instruction")||restored.Prepares!=1||restored.Executes!=0)throw new Exception("Stored request was not explicitly recoverable");form.Close();
   }
   for(int index=1;index<5;index++){
    var backend=new Backend {Inventory=Rpc.Obj(fixture["inventory"])};
    using(var form=Open(backend)){Field<ComboBox>(form,"action").SelectedIndex=index;Choose(Field<ComboBox>(form,"holds"),index<3?"held-test":"issued-test");Field<TextBox>(form,"reference").Text="UI-only hold instruction";Field<NumericUpDown>(form,"quantity").Value=2;Run(form,"Prepare");
     var command=Rpc.Obj(backend.Submitted["command"]);if(Convert.ToInt64(backend.Submitted["expected_revision"])!=5||command.ContainsKey("quantity")!=(index==4)||backend.Executes!=0)throw new Exception("Hold operation used the wrong quantity/revision or executed automatically");form.Close();
    }
   }
   var invalid=new Backend {Inventory=Rpc.Obj(fixture["inventory"])};
   using(var form=Open(invalid)){Draft(form);Field<TextBox>(form,"plan").Text="invalid plan with spaces";Run(form,"Prepare");if(invalid.Prepares!=0||Field<TextBox>(form,"operation").Text!=""||!Field<TextBox>(form,"plan").Enabled)throw new Exception("Invalid local IDs were locked into a pending operation");form.Close();}
   var missing=new Backend {Inventory=Rpc.Obj(fixture["inventory"]),Failure="prepare-not-stored"};
   using(var form=Open(missing)){Draft(form);Run(form,"Prepare");string id=Field<TextBox>(form,"operation").Text;var submitted=RevisionUi.Clone(missing.Submitted);Run(form,"Read");
    if(!Field<Button>(form,"prepare").Enabled||Field<Button>(form,"fresh").Enabled||missing.Prepares!=1||Field<TextBox>(form,"reference").Enabled)throw new Exception("Missing preparation was retried or allowed changing its ID/payload");
    Run(form,"Prepare");if(missing.Prepares!=2||missing.Executes!=0||id!=Field<TextBox>(form,"operation").Text||Convert.ToInt64(missing.Submitted["expected_revision"])!=Convert.ToInt64(submitted["expected_revision"])||Rpc.Str(missing.Submitted,"decision_reference")!=Rpc.Str(submitted,"decision_reference"))throw new Exception("Explicit preparation retry changed its binding or executed stock");form.Close();
   }
   StockEntryChecks(Rpc.Obj(fixture["inventory"]));
   Console.WriteLine("PASS: inventory commands PL/EN 100/150, eight actions, explicit prepare/execute separation, lot/delivery CAS, explicit stock metadata, lost replies/conflict recovery, no retries and stored requests after reopening");
  }finally{SynchronizationContext.SetSynchronizationContext(context);Control.CheckForIllegalCrossThreadCalls=oldCheck;UiText.SetLanguage(oldLanguage,false);}
 }
 static void StockDraft(InventoryCommandForm form,int index){
  Field<ComboBox>(form,"action").SelectedIndex=index;Field<TextBox>(form,"reference").Text="UI-only stock instruction";
  if(index==7){Choose(Field<ComboBox>(form,"deliveryChoice"),"delivery-test");Field<TextBox>(form,"stockLotId").Text="ui-received";Field<TextBox>(form,"stockLocation").Text="rack-qa";Field<NumericUpDown>(form,"stockQuantity").Value=5;Field<ComboBox>(form,"stockCondition").SelectedIndex=0;return;}
  Field<TextBox>(form,"stockItem").Text=index==5?"qa-plywood":"qa-locks";Field<ComboBox>(form,"stockUnit").SelectedIndex=index==5?2:0;Field<ComboBox>(form,"stockScope").SelectedIndex=1;
  Field<NumericUpDown>(form,"stockQuantity").Value=index==5?1:30;
  if(index==5){Field<TextBox>(form,"stockLotId").Text="ui-offcut";Field<TextBox>(form,"stockLocation").Text="rack-qa";Field<NumericUpDown>(form,"stockLength").Value=1000;Field<NumericUpDown>(form,"stockWidth").Value=600;Field<NumericUpDown>(form,"stockThickness").Value=9;Field<ComboBox>(form,"stockCondition").SelectedIndex=0;}
  else{Field<TextBox>(form,"newDeliveryId").Text="ui-delivery";Field<TextBox>(form,"confirmation").Text="QA-PO";Field<DateTimePicker>(form,"dueDate").Value=new DateTime(2030,1,1);Field<DateTimePicker>(form,"dueDate").Checked=true;}
 }
 static void StockEntryChecks(Dictionary<string,object> inventory){
  foreach(bool english in new[]{false,true})foreach(float scale in new[]{1f,1.5f})for(int index=5;index<8;index++){
   UiText.SetLanguage(english,false);var backend=new Backend {Inventory=inventory};
   using(var form=Open(backend)){form.Scale(new SizeF(scale,scale));Application.DoEvents();Field<ComboBox>(form,"action").SelectedIndex=index;
    if(Field<NumericUpDown>(form,"stockQuantity").Value!=0||Field<ComboBox>(form,"stockScope").SelectedIndex!=-1||Field<DateTimePicker>(form,"dueDate").Checked||Field<Button>(form,"prepare").Enabled)throw new Exception("Stock entry invented quantity, scope or confirmation date");
    StockDraft(form,index);Run(form,"Prepare");var command=Rpc.Obj(backend.Submitted["command"]);
    foreach(var pair in Field<Dictionary<Control,Control>>(form,"inputGroups")){var group=(TableLayoutPanel)pair.Value;if(!group.Visible)continue;var label=group.GetControlFromPosition(0,0);if(label==null||group.GetControlFromPosition(0,1)!=pair.Key||label.Bottom>pair.Key.Top)throw new Exception("Stock input separated from its label after dynamic layout");}
    if(backend.Prepares!=1||backend.Executes!=0||Convert.ToInt64(backend.Submitted["expected_revision"])!=(index==7?2:0)||!Field<Button>(form,"execute").Enabled)throw new Exception("Stock preparation executed or used wrong lot/delivery revision");
    if(index==6){var delivery=Rpc.Obj(command["delivery"]);if(Rpc.Str(delivery,"due_date")!="2030-01-01"||Rpc.Str(delivery,"confirmation_reference")!="QA-PO"||Convert.ToInt32(delivery["quantity"])!=30)throw new Exception("Delivery confirmation fields lost");}
    else{var lot=Rpc.Obj(command["lot"]);if(Rpc.Str(lot,"scope")!="synthetic_test"||Rpc.Str(lot,"condition")!="usable"||Convert.ToInt32(lot["on_hand"])!=(index==5?1:5))throw new Exception("Physical stock fields invented or dropped");
     if(index==5&&Rpc.Rows(lot["dimensions_mm"]).Length!=3)throw new Exception("Offcut dimensions missing");if(index==7&&(Rpc.Str(lot,"item_id")!="locks-test"||Rpc.Str(lot,"unit")!="piece"||lot["dimensions_mm"]!=null||Field<ComboBox>(form,"stockScope").Enabled||Field<TextBox>(form,"stockItem").Enabled))throw new Exception("Receipt could override confirmed delivery metadata");}
    string folder=Environment.GetEnvironmentVariable("ROCKPRO_UI_EVIDENCE");if(!String.IsNullOrEmpty(folder))using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(Path.Combine(folder,"inventory-stock-"+index+"-"+(english?"en":"pl")+"-"+(scale>1?"150":"100")+".png"));}
    string payload=new JavaScriptSerializer().Serialize(backend.Submitted);UiText.SetLanguage(!english,false);if(payload!=new JavaScriptSerializer().Serialize(backend.Submitted)||backend.Prepares!=1)throw new Exception("Language switch changed stock payload");form.Close();
   }
  }
  var invalid=new Backend {Inventory=inventory};using(var form=Open(invalid)){StockDraft(form,5);Field<NumericUpDown>(form,"stockQuantity").Value=2;Run(form,"Prepare");if(invalid.Prepares!=0||Field<TextBox>(form,"operation").Text!=""||Field<NumericUpDown>(form,"stockQuantity").Value!=2)throw new Exception("Offcut count was silently changed or invalid request persisted");form.Close();}
  var stale=new Backend {Inventory=RevisionUi.Clone(inventory)};using(var form=Open(stale)){StockDraft(form,7);Run(form,"Prepare");foreach(var value in Rpc.Rows(stale.Inventory["deliveries"]))Rpc.Obj(value)["revision"]=3;Run(form,"LoadData");stale.Failure="conflict";Run(form,"Execute");Run(form,"Read");if(Convert.ToInt64(stale.Submitted["expected_revision"])!=2||stale.Executes!=1||!Field<Button>(form,"fresh").Enabled)throw new Exception("Receipt refreshed its delivery CAS or retried after conflict");form.Close();}
 }
}
