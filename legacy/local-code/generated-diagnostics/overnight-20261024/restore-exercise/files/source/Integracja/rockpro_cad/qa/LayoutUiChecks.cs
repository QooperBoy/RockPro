using System;
using System.Drawing;
using System.Reflection;
using System.Windows.Forms;
using RockPro.CAD;
class LayoutUiChecks {
 [STAThread] static void Main(){Application.EnableVisualStyles();bool previousLanguage=UiText.IsEnglish;try{UiText.SetLanguage(false,false);
  using(var ranked=new RankedChoice {Tag=new[]{"XYZ","YZX"}}){
   ranked.Initialize(new[]{"XYZ","YZX"},new[]{"Standard","Obrót"});ranked.Items.AddRange(new[]{"Standard","Obrót"});ranked.SelectedIndex=0;
   ranked.Rank(new object[]{new System.Collections.Generic.Dictionary<string,object>{{"key","YZX"},{"valid",true},{"volume_l",20.0},{"score",0.0}},new System.Collections.Generic.Dictionary<string,object>{{"key","XYZ"},{"valid",true},{"volume_l",40.0},{"score",1.0}}});
   if(ranked.SelectedKey!="XYZ"||ranked.SelectedIndex!=1)throw new Exception("Ranking changed selected orientation");
   ranked.SelectKey("YZX");if(ranked.SelectedKey!="YZX"||ranked.SelectedIndex!=0)throw new Exception("Ranked key mapping failed");
  }
  var orange=Color.FromArgb(239,143,65);var gray=Color.Gray;int[] f={0,1,2,3};
  var partition=new[]{new PointF(10,10),new PointF(90,10),new PointF(90,90),new PointF(10,90)};
  var accessory=new[]{new PointF(65,30),new PointF(85,30),new PointF(85,70),new PointF(65,70)};
  foreach(bool reverse in new[]{false,true})using(var r=new DepthRaster(100,100)){
   if(reverse)r.Quad(accessory,new double[]{45,45,45,45},f,orange);
   r.Quad(partition,new double[]{100,10,10,100},f,gray);
   if(!reverse)r.Quad(accessory,new double[]{45,45,45,45},f,orange);
   if(r.Pixel(75,50)!=orange.ToArgb())throw new Exception("Partition occluded nearer accessory");
   if(r.Pixel(20,50)!=gray.ToArgb())throw new Exception("Partition lost");
  }
  using(var form=new Form {Size=new Size(420,220)}){
   var scroll=new Panel {Dock=DockStyle.Fill,AutoScroll=true};form.Controls.Add(scroll);
   var content=new Panel {Width=300,Height=1200};scroll.Controls.Add(content);
   var number=new ScrollSafeNumber {Value=12,Top=10};content.Controls.Add(number);
   var choice=new ScrollSafeChoice {Top=60,DropDownStyle=ComboBoxStyle.DropDownList};choice.Items.AddRange(new[]{"A","B","C"});choice.SelectedIndex=1;content.Controls.Add(choice);
   form.Show();Application.DoEvents();number.Focus();
   var e=new HandledMouseEventArgs(MouseButtons.None,0,0,0,-120);
   typeof(ScrollSafeNumber).GetMethod("OnMouseWheel",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(number,new object[]{e});
   if(number.Value!=12||!e.Handled||scroll.AutoScrollPosition.Y>=0)throw new Exception("Wheel changed number or did not scroll");
   var msg=Message.Create(choice.Handle,0x020A,new IntPtr(unchecked(-120<<16)),IntPtr.Zero);
   typeof(ScrollSafeChoice).GetMethod("WndProc",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(choice,new object[]{msg});
   if(choice.SelectedIndex!=1)throw new Exception("Wheel changed orientation");
   form.Close();
  }
  var original=new System.Collections.Generic.Dictionary<string,object>{{"name","Początek"},{"notes","Baza"},{"revision",1}};
  var draft=RevisionUi.Clone(original);draft["notes"]="Moje niezapisane wpisy";
  var current=RevisionUi.Clone(original);current["notes"]="Zmiana AI";current["revision"]=2;
  var conflict=RevisionUi.Conflict(new Exception(new System.Web.Script.Serialization.JavaScriptSerializer().Serialize(new {code="PROJECT_CONFLICT",expected_revision=1,current_revision=2,current=current})),"PROJECT_CONFLICT");
  if(conflict==null||RevisionUi.Conflict(new Exception("Brak połączenia"),"PROJECT_CONFLICT")!=null)throw new Exception("Conflict classification failed");
  using(var differences=RevisionUi.DifferenceGrid(original,draft,current)){
   if(differences.ColumnHeadersHeightSizeMode!=DataGridViewColumnHeadersHeightSizeMode.AutoSize||differences.ColumnHeadersDefaultCellStyle.WrapMode!=DataGridViewTriState.True)throw new Exception("Conflict/history headers must autosize for DPI");
   bool found=false;foreach(DataGridViewRow row in differences.Rows)if(Convert.ToString(row.Cells[0].Value)=="Notatki"){found=true;if(Convert.ToString(row.Cells[1].Value)!="Baza"||Convert.ToString(row.Cells[2].Value)!="Moje niezapisane wpisy"||Convert.ToString(row.Cells[3].Value)!="Zmiana AI")throw new Exception("Three-way comparison lost values");}
   if(!found)throw new Exception("Missing conflict row");
  }
  if(Convert.ToString(draft["revision"])!="1"||Convert.ToString(draft["notes"])!="Moje niezapisane wpisy"||Convert.ToString(original["notes"])!="Baza")throw new Exception("Conflict mutated draft or token");
  using(var panel=new RockProPanel(null)){
   var flags=BindingFlags.Instance|BindingFlags.NonPublic;
   var stageA=new System.Collections.Generic.Dictionary<string,object>{{"status","draft"},{"revision",1},{"note","Notatka konstruktora"}};
   var stageB=new System.Collections.Generic.Dictionary<string,object>{{"status","review"},{"revision",4}};
   var project=new System.Collections.Generic.Dictionary<string,object>{{"id","test"},{"name","Test"},{"revision",1},{"stages",new System.Collections.Generic.Dictionary<string,object>{{"inquiry",stageA},{"devices",stageB}}}};
   typeof(RockProPanel).GetField("project",flags).SetValue(panel,project);
   typeof(RockProPanel).GetMethod("StagesView",flags).Invoke(panel,null);
   var bases=(System.Collections.Generic.Dictionary<string,System.Collections.Generic.Dictionary<string,object>>)typeof(RockProPanel).GetField("stageBases",flags).GetValue(panel);
   stageA["revision"]=2;stageB["revision"]=5;
   if(Convert.ToInt32(bases["inquiry"]["revision"])!=1||Convert.ToInt32(bases["devices"]["revision"])!=4)throw new Exception("Stage row baselines follow mutable project versions");
  }
  Console.WriteLine("PASS: revision conflicts classify, preserve draft/token, show three-way values, capture independent row baselines");
  Console.WriteLine("PASS: depth buffer in both orders; number and choice wheel suppression; form scrolling");
  LanguageChecks();
  CasePlanUiChecks.Run();
  }finally{UiText.SetLanguage(previousLanguage,false);}
 }
 static void LayoutLanguageChecks(){
  var flags=BindingFlags.Instance|BindingFlags.NonPublic;
  UiText.SetLanguage(false,false);
  using(var form=new LayoutForm("language-test-not-opened")){
   var fields=(System.Collections.Generic.Dictionary<string,Control>)typeof(LayoutForm).GetField("fields",flags).GetValue(form);
   fields["name"].Text="Urządzenie użytkownika / custom device";
   fields["side_name"].Text="Kable klienta / custom cables";
   ((NumericUpDown)fields["x"]).Value=412.75m;
   ((RankedChoice)fields["orientation"]).SelectKey("YZX");
   ((RankedChoice)fields["arrangement"]).SelectKey("Z");
   ((ComboBox)fields["side"]).SelectedIndex=2;
   typeof(LayoutForm).GetField("dirty",flags).SetValue(form,true);
   typeof(LayoutForm).GetField("layoutRevision",flags).SetValue(form,17L);
   typeof(LayoutForm).GetField("revision",flags).SetValue(form,8);
   foreach(bool english in new[]{true,false}){
    UiText.SetLanguage(english,false);
    if(fields["name"].Text!="Urządzenie użytkownika / custom device"||fields["side_name"].Text!="Kable klienta / custom cables")throw new Exception("Layout language switch translated user text");
    if(((NumericUpDown)fields["x"]).Value!=412.75m)throw new Exception("Layout language switch changed dimensions");
    if(((RankedChoice)fields["orientation"]).SelectedKey!="YZX"||((RankedChoice)fields["arrangement"]).SelectedKey!="Z"||((ComboBox)fields["side"]).SelectedIndex!=2)throw new Exception("Layout language switch changed canonical layout choices");
    if(!(bool)typeof(LayoutForm).GetField("dirty",flags).GetValue(form)||(long)typeof(LayoutForm).GetField("layoutRevision",flags).GetValue(form)!=17L||(int)typeof(LayoutForm).GetField("revision",flags).GetValue(form)!=8)throw new Exception("Layout language switch reset dirty state or version tokens");
    if(english&&!form.Text.Contains("version 17"))throw new Exception("Layout title did not switch to English");
    if(!english&&!form.Text.Contains("wersja 17"))throw new Exception("Layout title did not return to Polish");
   }
  }
  Console.WriteLine("PASS: layout PL/EN/PL preserves dimensions, user text, orientation, arrangement, dirty state and both version tokens");
 }
 static void LanguageChecks(){
  LayoutLanguageChecks();
  var flags=BindingFlags.Instance|BindingFlags.NonPublic;
  using(var panel=new RockProPanel(null)){
   var data=new System.Collections.Generic.Dictionary<string,object>{{"id","language-test"},{"name","Projekt klienta / customer name"},{"notes","Notatka użytkownika — do not translate"},{"revision",7},{"quantity",2},{"source","C:\\sample\\projekt.ics"}};
   typeof(RockProPanel).GetField("project",flags).SetValue(panel,data);
   typeof(RockProPanel).GetMethod("ShowView",flags).Invoke(panel,new object[]{"Projekt"});
   var note=(TextBox)typeof(RockProPanel).GetField("notes",flags).GetValue(panel);note.Text="Niezapisany szkic / draft ąę";
   data["revision"]=8; // Simulate a newer project cache while the editor retains its old baseline.
   UiText.SetLanguage(true,false);
   var translatedNote=(TextBox)typeof(RockProPanel).GetField("notes",flags).GetValue(panel);
   if(translatedNote.Text!="Niezapisany szkic / draft ąę")throw new Exception("Language switch lost unsaved card notes");
   if(UiText.T("polski","English")!="English")throw new Exception("English selection failed");
   if(Rpc.Str(data,"name")!="Projekt klienta / customer name"||Rpc.Str(data,"revision")!="8")throw new Exception("Language switch mutated project data/version");
   var cardBaseline=(System.Collections.Generic.Dictionary<string,object>)typeof(RockProPanel).GetField("cardBase",flags).GetValue(panel);
   if(Rpc.Str(cardBaseline,"revision")!="7")throw new Exception("Language switch adopted newer card baseline");
   using(var diff=RevisionUi.DifferenceGrid(data,data,data)){
    if(diff.Columns[1].HeaderText=="Przy otwarciu")throw new Exception("Conflict headers remain Polish in English mode");
    if(Convert.ToString(diff.Rows[0].Cells[1].Value)!="Projekt klienta / customer name")throw new Exception("Conflict translated customer data");
   }
   UiText.SetLanguage(false,false);
   if(((TextBox)typeof(RockProPanel).GetField("notes",flags).GetValue(panel)).Text!="Niezapisany szkic / draft ąę")throw new Exception("Round-trip language switch lost draft");
   var stages=new System.Collections.Generic.Dictionary<string,object>{{"inquiry",new System.Collections.Generic.Dictionary<string,object>{{"status","draft"},{"revision",7}}}};
   data["stages"]=stages;
   typeof(RockProPanel).GetMethod("ShowView",flags).Invoke(panel,new object[]{"Etapy"});
   var inputs=(System.Collections.Generic.Dictionary<string,ComboBox>)typeof(RockProPanel).GetField("stageInputs",flags).GetValue(panel);
   inputs["inquiry"].SelectedIndex=2;
   stages["inquiry"]=new System.Collections.Generic.Dictionary<string,object>{{"status","waiting"},{"revision",8}};
   foreach(bool english in new[]{true,false}){
    UiText.SetLanguage(english,false);
    inputs=(System.Collections.Generic.Dictionary<string,ComboBox>)typeof(RockProPanel).GetField("stageInputs",flags).GetValue(panel);
    var baselines=(System.Collections.Generic.Dictionary<string,System.Collections.Generic.Dictionary<string,object>>)typeof(RockProPanel).GetField("stageBases",flags).GetValue(panel);
    if(inputs["inquiry"].SelectedIndex!=2||Rpc.Str(baselines["inquiry"],"revision")!="7"||Rpc.Str(baselines["inquiry"],"status")!="draft")throw new Exception("Language switch lost stage draft or adopted newer cached baseline");
    if(!inputs["inquiry"].Parent.Controls[0].Text.Contains("v7"))throw new Exception("Stage render/save baseline adopted newer cached revision");
   }
  }
  Console.WriteLine("PASS: PL/EN switch preserves user text, draft and project revision; conflict headers localize");
 }
}

