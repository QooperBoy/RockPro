using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using System.Windows.Forms;
using RockPro.CAD;

internal static class HandleDecisionUiChecks {
 const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
 static T Field<T>(object form,string name){return (T)form.GetType().GetField(name,Flags).GetValue(form);}
 static void Set(object form,string name,object value){form.GetType().GetField(name,Flags).SetValue(form,value);}
 static object Invoke(object form,string name,params object[] args){return form.GetType().GetMethod(name,Flags).Invoke(form,args);}
 static void Wait(Task task){while(!task.IsCompleted){Application.DoEvents();System.Threading.Thread.Sleep(5);}task.GetAwaiter().GetResult();Application.DoEvents();}
 static Dictionary<string,object> Row(string id,double y){return new Dictionary<string,object>{{"id",id},{"matrix_world_mm",new object[]{new object[]{1,0,0,0},new object[]{0,1,0,0},new object[]{0,0,1,0},new object[]{id.StartsWith("handles/left/")?0:650,y,150,1}}}};}
 static Dictionary<string,object> Evidence(){return new Dictionary<string,object>{{"baseline",new Dictionary<string,object>{{"members",new object[]{Row("handles/left/1",125),Row("handles/left/2",375),Row("handles/right/1",125),Row("handles/right/2",375)}}}},{"current",new Dictionary<string,object>{{"members",new object[]{Row("handles/left/1",125),Row("handles/left/2",375),Row("handles/right/1",125),Row("handles/right/2",387)}}}}};}
 static Dictionary<string,object> Result(){return new Dictionary<string,object>{{"blocked",false},{"review_sha256","test-review"},{"issues",new object[0]},
  {"manual_changes",new object[]{new Dictionary<string,object>{{"id","handles/right/2"},{"delta",new object[]{0,12,0}}}}},
  {"proposed_members",new object[]{Row("handles/left/1",150),Row("handles/left/2",450),Row("handles/right/1",150),Row("handles/right/2",462)}}};}
 internal static void Run(){
  foreach(bool english in new[]{false,true})foreach(float scale in new[]{1f,1.5f}){
   UiText.SetLanguage(english,false);int calls=0;
   using(var form=new HandleDecisionForm("UI-ONLY",delegate(string name,object args){calls++;throw new Exception("Unexpected backend");},false)){
    form.Show();form.Scale(new SizeF(scale,scale));Application.DoEvents();
    Set(form,"evidence",Evidence());Set(form,"revision",2L);Set(form,"projectRevision",4L);Field<ComboBox>(form,"choice").SelectedIndex=2;
    Set(form,"review",Result());Field<TextBox>(form,"reference").Text=english?"UI test only":"Wyłącznie próba okna";
    Invoke(form,"ShowRows",Result());Invoke(form,"UpdateButtons");Application.DoEvents();
    if(Field<DataGridView>(form,"differences").Rows.Count!=4)throw new Exception("Opposing handle comparison rows missing");
    Field<Label>(form,"status").Text=english?"UI test fixture: four handles on opposing walls. No CAD execution.":"Próba okna: cztery uchwyty na przeciwległych ścianach. Bez uruchamiania CAD.";
    foreach(string name in new[]{"load","measurement","readCad","preview","save"}){
     Button button=Field<Button>(form,name);
     if(!button.Visible||button.Width<button.GetPreferredSize(Size.Empty).Width||!button.Parent.ClientRectangle.Contains(button.Bounds))throw new Exception("Handle action clipped: "+name+" "+scale+" "+english);
    }
    if(!Field<Button>(form,"save").Enabled)throw new Exception("Explicit reviewed choice not recordable");
    string folder=Environment.GetEnvironmentVariable("ROCKPRO_UI_EVIDENCE");if(!String.IsNullOrEmpty(folder)){
     Directory.CreateDirectory(folder);using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(Path.Combine(folder,"handles-"+(english?"en":"pl")+"-"+(scale>1?"150":"100")+".png"));}}
    Set(form,"busy",true);Invoke(form,"UpdateButtons");foreach(string name in new[]{"load","measurement","readCad","preview","save"})if(Field<Button>(form,name).Enabled)throw new Exception("Handle action enabled while busy");
    Set(form,"busy",false);Invoke(form,"UpdateButtons");
    Field<ComboBox>(form,"choice").SelectedIndex=1;
    if(Field<Button>(form,"save").Enabled)throw new Exception("Changed choice reused old preview");
    if(calls!=0)throw new Exception("Handle form automatically called backend");form.Close();
   }
  }
  UiText.SetLanguage(false,false);
  foreach(bool conflict in new[]{false,true}){
   int calls=0;Dictionary<string,object> submitted=null;
   using(var form=new HandleDecisionForm("UI-ONLY",delegate(string name,object args){calls++;submitted=(Dictionary<string,object>)args;
    if(name!="save_handle_reconciliation")throw new Exception("Unexpected tool");if(conflict)throw new Exception("PROJECT_CONFLICT");return new Dictionary<string,object>{{"revision",3}};},false)){
    form.Show();Application.DoEvents();Set(form,"evidence",Evidence());Set(form,"revision",2L);Set(form,"projectRevision",4L);
    Field<ComboBox>(form,"choice").SelectedIndex=2;Field<TextBox>(form,"reference").Text="Explicit UI test";Set(form,"review",Result());Invoke(form,"UpdateButtons");
    Wait((Task)Invoke(form,"Run",new Func<Task>(delegate{return (Task)Invoke(form,"Save");})));
    if(calls!=1||Convert.ToInt64(submitted["expected_revision"])!=2||Convert.ToInt64(submitted["expected_project_revision"])!=4)throw new Exception("Handle CAS refreshed/retried");
    if(Field<long>(form,"revision")!=(conflict?2:3)||Field<long>(form,"projectRevision")!=4)throw new Exception("Handle revision mutation incorrect");
    if(Field<ComboBox>(form,"choice").SelectedIndex!=2||Field<TextBox>(form,"reference").Text!="Explicit UI test")throw new Exception("Handle conflict lost user choice");
    form.Close();
   }
  }
  foreach(bool stale in new[]{false,true}){
   int calls=0;
   using(var form=new HandleDecisionForm("UI-ONLY",delegate(string name,object args){calls++;var serializer=new System.Web.Script.Serialization.JavaScriptSerializer();var request=Rpc.Obj(serializer.DeserializeObject(serializer.Serialize(args)));
    if(Convert.ToInt64(request["expected_revision"])!=2||Convert.ToInt64(request["expected_project_revision"])!=4)throw new Exception("Measurement refreshed revision tokens");
    if(name=="measure_handle_reconciliation")return new Dictionary<string,object>{{"measurement_id","test-native-observation"},{"evidence",Evidence()},{"prior_state",null},{"preview",Result()},{"document_modified",true}};
    if(name=="save_handle_reconciliation"){if(Rpc.Str(request,"measurement_id")!="test-native-observation")throw new Exception("Missing measurement token");if(stale)throw new Exception("HANDLE_MEASUREMENT_STALE");return new Dictionary<string,object>{{"revision",3}};}
    throw new Exception("Unexpected tool");},false)){
    form.Show();Application.DoEvents();Set(form,"revision",2L);Set(form,"projectRevision",4L);
    Wait((Task)Invoke(form,"Run",new Func<Task>(delegate{return (Task)Invoke(form,"ReadCad");})));
    if(Field<ComboBox>(form,"choice").SelectedIndex!=-1||Field<Button>(form,"save").Enabled)throw new Exception("Measurement auto-selected decision");
    Field<ComboBox>(form,"choice").SelectedIndex=2;Field<TextBox>(form,"reference").Text="Native observation UI test";Set(form,"review",Result());
    Wait((Task)Invoke(form,"Run",new Func<Task>(delegate{return (Task)Invoke(form,"Save");})));
    if(calls!=2||Field<long>(form,"revision")!=(stale?2:3)||Field<long>(form,"projectRevision")!=4)throw new Exception("Native observation retried/refreshed CAS: calls="+calls+", revision="+Field<long>(form,"revision")+", project="+Field<long>(form,"projectRevision")+", status="+Field<Label>(form,"status").Text);
    if(stale&&!Field<Label>(form,"status").Text.Contains("Zmierz"))throw new Exception("Stale measurement missing remeasure instruction");
    form.Close();
   }
  }
  using(var form=new HandleDecisionForm("UI-ONLY",delegate(string name,object args){throw new Exception("CAD not open");},false)){
   form.Show();Application.DoEvents();Set(form,"evidence",Evidence());Set(form,"measurementId","old-token");Set(form,"review",Result());
   Wait((Task)Invoke(form,"Run",new Func<Task>(delegate{return (Task)Invoke(form,"ReadCad");})));
   if(Field<string>(form,"measurementId")!=""||Field<Button>(form,"save").Enabled)throw new Exception("Failed CAD read kept old valid observation");form.Close();
  }
  Console.WriteLine("PASS: handle decisions PL/EN 100/150, native measurement tokens, stale-read rejection, independent CAS and no automatic CAD/retry");
 }
}
