using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Web.Script.Serialization;
using RockPro.CAD;

internal static class CasePlanUiChecks {
 static readonly BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
 static T Field<T>(object form,string name){return (T)form.GetType().GetField(name,Flags).GetValue(form);}
 static void Set(object form,string name,object value){form.GetType().GetField(name,Flags).SetValue(form,value);}
 static object Invoke(object form,string name,params object[] args){return form.GetType().GetMethod(name,Flags).Invoke(form,args);}
 static void Wait(Task task){DateTime until=DateTime.UtcNow.AddSeconds(15);while(!task.IsCompleted&&DateTime.UtcNow<until){Application.DoEvents();Thread.Sleep(5);}if(!task.IsCompleted)throw new Exception("Case UI task did not finish");task.GetAwaiter().GetResult();Application.DoEvents();}
 internal static void Run(){bool prior=UiText.IsEnglish;try{
  foreach(bool english in new[]{false,true})foreach(float scale in new[]{1f,1.5f}){
   UiText.SetLanguage(english,false);int calls=0;
   using(var form=new CasePlanForm("ui-test",delegate(string name,object args){calls++;throw new Exception("Unexpected backend call");},false)){
    if(scale>1)form.Scale(new SizeF(scale,scale));form.Size=form.MinimumSize;form.Show();Application.DoEvents();
    string banner=Field<Label>(form,"explanation").Text;
    if(!banner.Contains(english?"proxy solids":"bryłami zastępczymi")||!banner.Contains("Epson"))throw new Exception("Synthetic scope banner missing");
    string planPath=Environment.GetEnvironmentVariable("ROCKPRO_UI_PLAN");if(!String.IsNullOrEmpty(planPath)){
     var serializer=new JavaScriptSerializer {MaxJsonLength=16000000};Invoke(form,"ShowPlan",Rpc.Obj(serializer.DeserializeObject(File.ReadAllText(planPath))));
     Field<Label>(form,"status").Text=english?"UI check: populated synthetic proposal; no CAD execution.":"Test okna: wypełniony plan syntetyczny; bez uruchamiania CAD.";
    }
    foreach(string key in new[]{"prepare","load","savePlan","execute","read","recover"}){
     var button=Field<Button>(form,key);if(!button.Visible||button.Width<button.GetPreferredSize(Size.Empty).Width)throw new Exception("Case button clipped: "+key+" "+english+" "+scale);
     if(!button.Parent.ClientRectangle.Contains(button.Bounds))throw new Exception("Case button outside parent: "+key);
    }
    Set(form,"planId","UI-CHECK-NO-CAD");Invoke(form,"UpdateButtons");Application.DoEvents();
    string folder=Environment.GetEnvironmentVariable("ROCKPRO_UI_EVIDENCE");if(!String.IsNullOrEmpty(folder)){Directory.CreateDirectory(folder);using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(Path.Combine(folder,"case-"+(english?"en":"pl")+"-"+(scale>1?"150":"100")+".png"));}}
    Set(form,"busy",true);Invoke(form,"UpdateButtons");foreach(string key in new[]{"prepare","load","savePlan","execute","read","recover"})if(Field<Button>(form,key).Enabled)throw new Exception("Busy case control enabled");
    Set(form,"busy",false);Set(form,"pendingOperation",true);Field<TextBox>(form,"operation").Text="unknown-operation";Invoke(form,"UpdateButtons");
    if(Field<Button>(form,"execute").Enabled||!Field<Button>(form,"read").Enabled||!Field<Button>(form,"recover").Enabled)throw new Exception("Unknown outcome must expose recovery without execution");
    if(calls!=0)throw new Exception("Case form automatically called backend");
    form.Close();
   }
  }
  UiText.SetLanguage(false,false);int executions=0;string operationId="";
  using(var form=new CasePlanForm("ui-test",delegate(string name,object args){if(name=="execute_case_plan"){executions++;throw new TimeoutException("simulated lost CAD reply");}throw new Exception("Unexpected tool");},false)){
   form.Show();Application.DoEvents();Set(form,"planId","pinned-test-plan");Set(form,"revision",1L);
   Wait((Task)Invoke(form,"Run",new Func<Task>(delegate{return (Task)Invoke(form,"Execute");})));
   operationId=Field<TextBox>(form,"operation").Text;
   if(executions!=1||operationId.Length!=32||!Field<bool>(form,"pendingOperation")||Field<Button>(form,"execute").Enabled||!Field<Button>(form,"recover").Enabled)throw new Exception("Lost reply must retain operation ID without retry");
   form.Close();
  }
  foreach(bool journalUnavailable in new[]{false,true}){
   int attempts=0;using(var rejected=new CasePlanForm("ui-test",delegate(string name,object args){
    if(name=="execute_case_plan"){attempts++;throw new Exception("CASE_REVISION_CONFLICT");}
    if(name=="get_case_operation")throw new Exception(journalUnavailable?"journal connection unavailable":"CASE_OPERATION_NOT_FOUND");
    throw new Exception("Unexpected retry");},false)){
    rejected.Show();Application.DoEvents();Set(rejected,"planId","stale-plan");Set(rejected,"revision",1L);
    Wait((Task)Invoke(rejected,"Run",new Func<Task>(delegate{return (Task)Invoke(rejected,"Execute");})));
    if(attempts!=1||Field<bool>(rejected,"pendingOperation")!=journalUnavailable||Field<Button>(rejected,"execute").Enabled||!Field<Button>(rejected,"load").Enabled)throw new Exception("Pre-journal rejection/recovery state incorrect");
    rejected.Close();
   }
  }
  int reads=0;using(var reopened=new CasePlanForm("ui-test",delegate(string name,object args){reads++;
   if(name=="list_case_operations")return new Dictionary<string,object>{{"operations",new object[]{new Dictionary<string,object>{{"operation_id",operationId},{"state","outcome_unknown"}}}}};
   if(name=="get_case_operation")return new Dictionary<string,object>{{"status","outcome_unknown"},{"operation_id",operationId}};
   throw new Exception("Reopening must only discover/read outstanding operations");},false)){
   reopened.Show();Application.DoEvents();Wait((Task)Invoke(reopened,"Run",new Func<Task>(delegate{return (Task)Invoke(reopened,"LoadSaved");})));
   if(reads!=2||Field<TextBox>(reopened,"operation").Text!=operationId||!Field<bool>(reopened,"pendingOperation"))throw new Exception("Outstanding operation not restored after reopening");
   reopened.Close();
  }
  Console.WriteLine("PASS: case prototype PL/EN 100/150 percent, button bounds, synthetic scope, busy/recovery, lost reply retained without retry, restart recovery discovery");
 }finally{UiText.SetLanguage(prior,false);}}
}
