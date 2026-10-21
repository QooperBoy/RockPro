using System;
using System.Drawing;
using System.Reflection;
using System.Windows.Forms;
using RockPro.CAD;
class LayoutUiChecks {
 [STAThread] static void Main(){Application.EnableVisualStyles();
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
 }
}
