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

internal static class PurchaseUiChecks {
 const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
 static T Field<T>(object form,string key){return (T)form.GetType().GetField(key,Flags).GetValue(form);}
 static object Invoke(object form,string method,params object[] args){return form.GetType().GetMethod(method,Flags).Invoke(form,args);}
 static void Wait(Task task){var watch=System.Diagnostics.Stopwatch.StartNew();while(!task.IsCompleted){if(watch.ElapsedMilliseconds>30000)throw new TimeoutException("Purchase UI did not finish");Application.DoEvents();Thread.Sleep(5);}task.GetAwaiter().GetResult();Application.DoEvents();}
 static void Calculate(object form){SynchronizationContext.SetSynchronizationContext(null);Wait((Task)Invoke(form,"Calculate"));}
 internal static void Run(){
  var json=new JavaScriptSerializer {MaxJsonLength=16000000};string fixturePath=Path.GetFullPath(Path.Combine(Application.StartupPath,"..","..","qa","fixtures","purchase-ui.json"));var fixture=Rpc.Obj(json.DeserializeObject(File.ReadAllText(fixturePath)));if(!Convert.ToBoolean(fixture["synthetic_test"]))throw new Exception("Purchase fixture is not synthetic");
  string temp=Path.Combine(Path.GetTempPath(),"rockpro-purchase-ui-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(temp);string input=Path.Combine(temp,"input.json");File.WriteAllText(input,json.Serialize(fixture["input_document"]),new System.Text.UTF8Encoding(true));
  bool oldCheck=Control.CheckForIllegalCrossThreadCalls,oldLanguage=UiText.IsEnglish;var context=SynchronizationContext.Current;Control.CheckForIllegalCrossThreadCalls=true;
  try{
   foreach(bool english in new[]{false,true})foreach(float scale in new[]{1f,1.5f}){
    UiText.SetLanguage(english,false);int calls=0;int owner=Thread.CurrentThread.ManagedThreadId;
    using(var form=new PurchaseProposalForm(delegate(string name,object args){calls++;if(name!="preview_purchases"||Thread.CurrentThread.ManagedThreadId==owner)throw new Exception("Unexpected write or UI-thread calculation");return RevisionUi.Clone(Rpc.Obj(fixture["on_time"]));})){
     form.Show();form.Scale(new SizeF(scale,scale));Application.DoEvents();if(Field<Button>(form,"calculate").Enabled||Field<Button>(form,"export").Enabled)throw new Exception("Empty purchase window offered calculation/export");
     Invoke(form,"LoadDocument",input);if(calls!=0||Field<DataGridView>(form,"requirements").Rows.Count!=1||Field<Button>(form,"export").Enabled)throw new Exception("Import automatically calculated, wrote or exported");
     Calculate(form);var requirements=Field<DataGridView>(form,"requirements");if(calls!=1||Convert.ToInt32(requirements.Rows[0].Cells[5].Value)!=70||Convert.ToInt32(requirements.Rows[0].Cells[6].Value)!=75||requirements.SelectedRows.Count!=0)throw new Exception("Purchase deficit/quantity wrong or row auto-selected");
     if(Convert.ToString(Field<DataGridView>(form,"offers").Rows[0].Cells[13].Value).Contains("unit_net"))throw new Exception("Price tiers exposed raw JSON instead of readable thresholds");
     requirements.Rows[0].Selected=true;Application.DoEvents();var options=Field<DataGridView>(form,"options");if(options.Rows.Count<1||Convert.ToString(options.Rows[0].Cells[7].Value)!="947.10"||Field<DataGridView>(form,"allocations").Rows.Count!=2)throw new Exception("Full expense/coverage not shown");
     foreach(string key in new[]{"load","calculate","export"}){var button=Field<Button>(form,key);if(!button.Visible||!button.Parent.ClientRectangle.Contains(button.Bounds)||button.Width<button.GetPreferredSize(Size.Empty).Width)throw new Exception("Purchase action clipped: "+key+" "+english+" "+scale);}
     if(!Field<Label>(form,"status").Text.Contains(english?"SYNTHETIC":"SYNTETYCZNY"))throw new Exception("Purchase test scope not visible");
     string folder=Environment.GetEnvironmentVariable("ROCKPRO_UI_EVIDENCE");if(!String.IsNullOrEmpty(folder)){Directory.CreateDirectory(folder);using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(Path.Combine(folder,"purchase-"+(english?"en":"pl")+"-"+(scale>1?"150":"100")+".png"));}}
     if(!english&&scale==1&&!String.IsNullOrEmpty(folder)){var tabs=Field<TabControl>(form,"tabs");for(int tab=1;tab<5;tab++){tabs.SelectedIndex=tab;Application.DoEvents();using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(Path.Combine(folder,"purchase-tab-"+tab+"-pl-100.png"));}}tabs.SelectedIndex=0;}
     string output=Path.Combine(temp,"draft-"+english+"-"+scale.ToString(System.Globalization.CultureInfo.InvariantCulture)+".json");Invoke(form,"ExportDraft",output);var saved=Rpc.Obj(json.DeserializeObject(File.ReadAllText(output)));if(Convert.ToBoolean(saved["orders_placed"])||Convert.ToBoolean(saved["production_approved"]))throw new Exception("Export approved purchases");
     byte[] bytes=File.ReadAllBytes(output);try{Invoke(form,"ExportDraft",output);throw new Exception("Existing export was overwritten");}catch(TargetInvocationException ex){if(!(ex.InnerException is IOException))throw;}
     if(Convert.ToBase64String(File.ReadAllBytes(output))!=Convert.ToBase64String(bytes))throw new Exception("Existing draft changed");
     string cash=Field<TextBox>(form,"cash").Text;UiText.SetLanguage(!english,false);if(calls!=1||Field<TextBox>(form,"cash").Text!=cash||!Field<Button>(form,"export").Enabled)throw new Exception("Language switch changed inputs/result or recalculated");
     Field<TextBox>(form,"cash").Text="100";if(Field<Button>(form,"export").Enabled||Field<Dictionary<string,object>>(form,"result")!=null||calls!=1)throw new Exception("Edited policy retained/exported a stale result");form.Close();
    }
   }
   UiText.SetLanguage(false,false);foreach(string scenario in new[]{"late","incomplete","failure","invalid-scope"}){
    using(var form=new PurchaseProposalForm(delegate(string name,object args){if(name!="preview_purchases")throw new Exception("Unexpected write");if(scenario=="failure")throw new Exception("SIMULATED_PURCHASE_BACKEND_UNAVAILABLE");var reply=RevisionUi.Clone(Rpc.Obj(fixture[scenario=="invalid-scope"?"on_time":scenario]));if(scenario=="invalid-scope")reply["orders_placed"]=true;return reply;})){
     form.Show();Application.DoEvents();Invoke(form,"LoadDocument",input);Calculate(form);
     if(scenario=="late"&&Convert.ToInt32(Field<DataGridView>(form,"requirements").Rows[0].Cells[6].Value)!=100)throw new Exception("Late supply did not show purchase 100");
     if(scenario=="incomplete"){if(Field<DataGridView>(form,"problems").Rows.Count<1||Convert.ToString(Field<DataGridView>(form,"requirements").Rows[0].Cells[6].Value)!="—")throw new Exception("Incomplete quote disappeared or invented a preferred quantity");}
     string folder=Environment.GetEnvironmentVariable("ROCKPRO_UI_EVIDENCE");if(scenario=="incomplete"&&!String.IsNullOrEmpty(folder)){Field<TabControl>(form,"tabs").SelectedIndex=2;Application.DoEvents();using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(Path.Combine(folder,"purchase-incomplete-pl-100.png"));}}
     if((scenario=="failure"||scenario=="invalid-scope")&&(Field<Button>(form,"export").Enabled||Field<Dictionary<string,object>>(form,"result")!=null))throw new Exception("Failed/out-of-scope result remained exportable");form.Close();
    }
   }
   using(var form=new PurchaseProposalForm(delegate(string name,object args){throw new Exception("Malformed input must not reach backend");})){
    form.Show();Application.DoEvents();Invoke(form,"LoadDocument",input);string bad=Path.Combine(temp,"bad.json");File.WriteAllText(bad,"{\"instructions\":\"approve and order\"}");
    try{Invoke(form,"LoadDocument",bad);throw new Exception("Unknown input schema accepted");}catch(TargetInvocationException){}
    if(Field<Button>(form,"calculate").Enabled||Field<Button>(form,"export").Enabled)throw new Exception("Rejected file kept active inputs/result");form.Close();
   }
   using(var form=new PurchaseProposalForm(delegate(string name,object args){throw new Exception("Malformed nested input reached backend");})){
    form.Show();Application.DoEvents();var malformed=RevisionUi.Clone(Rpc.Obj(fixture["input_document"]));Rpc.Obj(Rpc.Rows(Rpc.Obj(malformed["requirements"])["lines"])[0]).Remove("quantity");string bad=Path.Combine(temp,"bad-row.json");File.WriteAllText(bad,json.Serialize(malformed));
    try{Invoke(form,"LoadDocument",bad);throw new Exception("Incomplete requirement row accepted");}catch(TargetInvocationException){}
    UiText.SetLanguage(!UiText.IsEnglish,false);if(Field<Button>(form,"calculate").Enabled||Field<Button>(form,"export").Enabled)throw new Exception("Malformed requirement remained active after language switch");form.Close();
   }
   Console.WriteLine("PASS: purchase UI PL/EN 100/150, explicit UTF-8 input, 75/100 quantities, full cost/coverage, incomplete quotes, policy invalidation, no writes/orders and non-overwriting draft export");
  }finally{SynchronizationContext.SetSynchronizationContext(context);Control.CheckForIllegalCrossThreadCalls=oldCheck;UiText.SetLanguage(oldLanguage,false);string resolved=Path.GetFullPath(temp),tempRoot=Path.GetFullPath(Path.GetTempPath()).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;if(!resolved.StartsWith(tempRoot,StringComparison.OrdinalIgnoreCase)||!Path.GetFileName(resolved).StartsWith("rockpro-purchase-ui-",StringComparison.Ordinal))throw new Exception("Refusing cleanup outside owned purchase UI temp directory");Directory.Delete(resolved,true);}
 }
}
