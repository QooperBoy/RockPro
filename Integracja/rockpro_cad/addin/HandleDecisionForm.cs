using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace RockPro.CAD {
[System.Runtime.InteropServices.ComVisible(false)]
internal sealed class HandleDecisionForm : Form {
 readonly string projectId;
 readonly Func<string,object,Dictionary<string,object>> backend;
 readonly DataGridView differences=new DataGridView();
 readonly ComboBox choice=new ScrollSafeChoice {DropDownStyle=ComboBoxStyle.DropDownList};
 readonly Button load=new Button(),measurement=new Button(),readCad=new Button(),preview=new Button(),save=new Button();
 readonly Label heading=new Label(),status=new Label(),referenceLabel=new Label();
 readonly TextBox reference=new TextBox();
 readonly ToolTip tips=new ToolTip();
 Dictionary<string,object> evidence,priorState,review;
 long revision,projectRevision;
 string measurementId="";
 bool busy,loading;
 static readonly string[] keys={"preserve_absolute","restore_rule","adopt_offset","leave_manual"};
 static string T(string pl,string en){return UiText.T(pl,en);}
 internal HandleDecisionForm(string id):this(id,Rpc.Call,true){}
 internal HandleDecisionForm(string id,Func<string,object,Dictionary<string,object>> call,bool autoLoad){
  projectId=id;backend=call;Font=new Font("Segoe UI",10);BackColor=Color.FromArgb(245,248,250);
  Size=new Size(1160,760);MinimumSize=new Size(900,650);StartPosition=FormStartPosition.CenterParent;
  AutoScaleMode=AutoScaleMode.Dpi;Padding=new Padding(18);
  var root=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=5};
  root.RowStyles.Add(new RowStyle(SizeType.Absolute,100));root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  root.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.RowStyles.Add(new RowStyle(SizeType.Absolute,80));root.RowStyles.Add(new RowStyle(SizeType.Absolute,96));
  Controls.Add(root);heading.Dock=DockStyle.Fill;heading.BackColor=Color.FromArgb(255,237,218);heading.Padding=new Padding(12);root.Controls.Add(heading,0,0);
  var actions=new FlowLayoutPanel {Dock=DockStyle.Fill,AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,WrapContents=true,Padding=new Padding(0,8,0,5)};
  foreach(var button in new[]{load,measurement,readCad,preview,save}){button.Width=248;button.Height=40;button.Margin=new Padding(0,0,8,5);button.BackColor=Color.White;actions.Controls.Add(button);}
  choice.Width=540;choice.Height=36;choice.Margin=new Padding(0,2,0,0);actions.Controls.Add(choice);root.Controls.Add(actions,0,1);
  differences.Dock=DockStyle.Fill;differences.ReadOnly=true;differences.AllowUserToAddRows=false;differences.AllowUserToDeleteRows=false;
  differences.RowHeadersVisible=false;differences.BackgroundColor=Color.White;differences.AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill;
  differences.AutoSizeRowsMode=DataGridViewAutoSizeRowsMode.AllCells;differences.ColumnHeadersHeightSizeMode=DataGridViewColumnHeadersHeightSizeMode.AutoSize;
  differences.DefaultCellStyle.Padding=new Padding(5,8,5,8);differences.DefaultCellStyle.WrapMode=DataGridViewTriState.True;
  for(int i=0;i<5;i++)differences.Columns.Add("c"+i,"");root.Controls.Add(differences,0,2);
  var note=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,Padding=new Padding(0,8,0,0)};
  referenceLabel.Dock=DockStyle.Fill;reference.Dock=DockStyle.Fill;note.Controls.Add(referenceLabel,0,0);note.Controls.Add(reference,0,1);root.Controls.Add(note,0,3);
  status.Dock=DockStyle.Fill;status.Padding=new Padding(0,8,0,0);root.Controls.Add(status,0,4);
  load.Click+=async delegate{await Run(LoadSaved);};measurement.Click+=delegate{LoadMeasurement();};
  readCad.Click+=async delegate{await Run(ReadCad);};
  preview.Click+=async delegate{await Run(Preview);};save.Click+=async delegate{await Run(Save);};
  choice.SelectedIndexChanged+=delegate{if(!loading){review=null;UpdateButtons();}};
  reference.TextChanged+=delegate{UpdateButtons();};
  Shown+=async delegate{if(autoLoad)await Run(LoadSaved);};FormClosing+=delegate(object sender,FormClosingEventArgs e){if(busy)e.Cancel=true;};
  UiText.LanguageChanged+=RefreshLanguage;FormClosed+=delegate{UiText.LanguageChanged-=RefreshLanguage;tips.Dispose();};
  RefreshLanguage(null,EventArgs.Empty);UpdateButtons();
 }
 async Task<Dictionary<string,object>> Call(string name,object args){return await Task.Run(()=>backend(name,args));}
 async Task Run(Func<Task> action){if(busy)return;busy=true;UpdateButtons();try{await action();}catch(Exception ex){status.ForeColor=Color.Firebrick;status.Text=ex.Message+T("\nNie ponowiono zapisu ani nie odświeżono rewizji. Twoje wybory pozostają w oknie.","\nNo retry or revision refresh. Your choices remain in the window.")+(ex.Message.Contains("HANDLE_MEASUREMENT_")?T("\nZmierz uchwyty ponownie przed kolejnym podglądem i zapisem.","\nMeasure the handles again before previewing and saving."):"");}finally{busy=false;if(!IsDisposed)UpdateButtons();}}
 void UpdateButtons(){if(IsDisposed)return;load.Enabled=measurement.Enabled=!busy;readCad.Enabled=!busy&&revision>0;choice.Enabled=!busy&&evidence!=null;
  preview.Enabled=!busy&&evidence!=null&&choice.SelectedIndex>=0;
  save.Enabled=!busy&&review!=null&&choice.SelectedIndex>=0&&reference.Text.Trim().Length>0;reference.Enabled=!busy;}
 async Task LoadSaved(){
  review=null;measurementId="";
  var card=await Call("get_project",new {project_id=projectId});
  var saved=await Call("get_handle_reconciliation",new {project_id=projectId});revision=Convert.ToInt64(saved["revision"]);review=null;
  projectRevision=Convert.ToInt64(Rpc.Obj(card["project"])["revision"]);
  if(Convert.ToBoolean(saved["saved"])){evidence=Rpc.Obj(saved["evidence"]);var result=Rpc.Obj(saved["result"]);priorState=result.ContainsKey("state")&&result["state"]!=null?Rpc.Obj(result["state"]):null;reference.Text=Rpc.Str(saved,"decision_reference");ShowRows(result);}
  else{evidence=null;priorState=null;differences.Rows.Clear();}
  status.ForeColor=Color.FromArgb(55,70,85);status.Text=T("Odczytano wersję decyzji ","Loaded decision revision ")+revision+T(" i karty "," and project revision ")+projectRevision+T(". Wczytaj pomiar i jawnie wybierz sposób zachowania uchwytów.",". Load a measurement and explicitly choose how to handle the group.");
 }
 async Task ReadCad(){
  review=null;measurementId="";
  var result=await Call("measure_handle_reconciliation",new {project_id=projectId,expected_revision=revision,expected_project_revision=projectRevision});
  evidence=Rpc.Obj(result["evidence"]);priorState=result.ContainsKey("prior_state")&&result["prior_state"]!=null?Rpc.Obj(result["prior_state"]):null;
  measurementId=Rpc.Str(result,"measurement_id");if(String.IsNullOrEmpty(measurementId))throw new Exception(T("Brak identyfikatora świeżego pomiaru.","Fresh measurement ID is missing."));
  choice.SelectedIndex=-1;ShowRows(Rpc.Obj(result["preview"]));status.ForeColor=Color.FromArgb(55,70,85);
  status.Text=T("Odczytano pozycje uchwytów bezpośrednio z otwartego pliku projektu w IronCAD. Wybierz decyzję i oblicz podgląd.\n","Handle poses read directly from the open project file in IronCAD. Choose a decision and calculate its preview.\n")+
   (Convert.ToBoolean(result["document_modified"])?T("Model ma niezapisane zmiany. Zapis decyzji nie zapisuje modelu. ","The model has unsaved changes. Recording a decision does not save CAD. "):"")+
   T("Przed zapisem decyzji SDK ponownie sprawdzi pozycje.","Before recording the decision, the SDK rechecks the poses.");
 }
 void LoadMeasurement(){using(var dialog=new OpenFileDialog {Filter=T("Pomiar uchwytów (*.json)|*.json","Handle measurement (*.json)|*.json"),CheckFileExists=true,Multiselect=false}){
  if(dialog.ShowDialog(this)!=DialogResult.OK)return;try{var file=new FileInfo(dialog.FileName);if(file.Length>2*1024*1024)throw new Exception(T("Pomiar przekracza 2 MB.","Measurement exceeds 2 MB."));
   var serializer=new JavaScriptSerializer {MaxJsonLength=2*1024*1024};evidence=Rpc.Obj(serializer.DeserializeObject(File.ReadAllText(file.FullName,System.Text.Encoding.UTF8)));
   review=null;measurementId="";choice.SelectedIndex=-1;differences.Rows.Clear();status.Text=T("Wczytano zapisany pomiar. Wybierz decyzję i oblicz podgląd. Plik CAD nie został zmieniony.","Saved measurement loaded. Choose a decision and calculate its preview. CAD has not changed.");UpdateButtons();
  }catch(Exception ex){evidence=null;review=null;measurementId="";status.Text=ex.Message;UpdateButtons();}}}
 Dictionary<string,object> PreviewArgs(){var args=new Dictionary<string,object>{{"evidence",evidence},{"choice",keys[choice.SelectedIndex]}};if(priorState!=null)args["prior_state"]=priorState;return args;}
 async Task Preview(){review=null;var result=await Call("preview_handle_reconciliation",PreviewArgs());review=result;ShowRows(result);bool blocked=Convert.ToBoolean(result["blocked"]);
  status.ForeColor=blocked?Color.Firebrick:Color.FromArgb(35,110,70);var issues=new List<string>();foreach(object value in Rpc.Rows(result["issues"]))issues.Add(Issue(Convert.ToString(value)));
  status.Text=(blocked?T("Zmiana wymaga rozwiązania konfliktu. ","Conflict must be resolved. "):T("Podgląd odsadzeń mieści się na ściankach. ","Offset proposal fits the walls. "))+String.Join("; ",issues.ToArray())+
   T("\nZapis utrwali decyzję, bez zastosowania w CAD. Różowy: ręczna zmiana; niebieski: nowa pozycja [mm].","\nSaving records the decision without applying it in CAD. Pink: manual change; blue: proposed position [mm].");}
 async Task Save(){var args=PreviewArgs();args["project_id"]=projectId;args["expected_revision"]=revision;args["expected_project_revision"]=projectRevision;args["review_sha256"]=review["review_sha256"];args["decision_reference"]=reference.Text.Trim();
  if(measurementId.Length>0)args["measurement_id"]=measurementId;
  var result=await Call("save_handle_reconciliation",args);revision=Convert.ToInt64(result["revision"]);review=null;
  measurementId="";
  status.ForeColor=Color.FromArgb(35,110,70);status.Text=T("Decyzja zapisana, wersja ","Decision saved, revision ")+revision+T(". CAD bez zmian; przed wykonaniem potrzebny świeży pomiar i kontrolowana kopia.",". CAD unchanged; execution requires fresh measurement and a controlled copy.");}
 static string Vec(Dictionary<string,object> row){if(row.Count==0)return "—";var matrix=Rpc.Rows(row["matrix_world_mm"]);var p=Rpc.Rows(matrix[3]);return String.Join(" / ",Array.ConvertAll(new[]{p[0],p[1],p[2]},x=>Convert.ToDouble(x).ToString("0.###",CultureInfo.CurrentCulture)));}
 static Dictionary<string,Dictionary<string,object>> Members(object snapshot){var result=new Dictionary<string,Dictionary<string,object>>();foreach(object value in Rpc.Rows(Rpc.Obj(snapshot)["members"])){var row=Rpc.Obj(value);result.Add(Rpc.Str(row,"id"),row);}return result;}
 void ShowRows(Dictionary<string,object> result){differences.Rows.Clear();var baseline=Members(evidence["baseline"]);var current=Members(evidence["current"]);var changed=new Dictionary<string,string>();
  foreach(object value in Rpc.Rows(result["manual_changes"])){var row=Rpc.Obj(value);changed[Rpc.Str(row,"id")]=String.Join(" / ",Array.ConvertAll(Rpc.Rows(row["delta"]),x=>Convert.ToDouble(x).ToString("0.###",CultureInfo.CurrentCulture)));}
  foreach(object value in Rpc.Rows(result["proposed_members"])){var row=Rpc.Obj(value);var id=Rpc.Str(row,"id");string name=id.Replace("handles/left/",T("Lewy uchwyt ","Left handle ")).Replace("handles/right/",T("Prawy uchwyt ","Right handle "));
   int n=differences.Rows.Add(name,Vec(baseline[id]),Vec(current[id]),Vec(row),changed.ContainsKey(id)?changed[id]:"—");differences.Rows[n].Cells[3].Style.BackColor=Color.FromArgb(221,237,251);if(changed.ContainsKey(id))differences.Rows[n].Cells[2].Style.BackColor=Color.FromArgb(255,223,231);}
 }
 static string Issue(string value){string[] parts=value.Split(':');string caption=parts[0];switch(caption){case "CONSTRUCTOR_DECISION_REQUIRED":caption=T("Potrzebna decyzja konstruktora","Constructor decision required");break;case "HANDLE_OFF_MOUNTING_WALL":caption=T("Uchwyt poza płaszczyzną montażu","Handle off its mounting wall");break;case "HANDLE_NO_EDGE_CLEARANCE":caption=T("Za mały odstęp od krawędzi","Insufficient edge clearance");break;case "HANDLE_PAIR_NO_CLEARANCE":caption=T("Za mały odstęp między uchwytami","Insufficient handle spacing");break;case "MANUAL_MEMBERS_REQUIRE_APPROVED_ANCHORS":caption=T("Element ręczny wymaga zatwierdzonej kotwy","Manual member needs an approved anchor");break;case "ROTATION_REQUIRES_MANUAL_REVIEW":caption=T("Obrót wymaga osobnego sprawdzenia","Rotation needs separate review");break;}return caption+(parts.Length>1?" ("+parts[1]+")":"");}
 void RefreshLanguage(object sender,EventArgs e){if(IsDisposed)return;Text=T("RockPro CAD | Ręczne zmiany uchwytów","RockPro CAD | Manual handle changes");heading.Text=T("ROCKPRO • DECYZJE DLA GRUPY H7159\nPomiar z otwartego CAD lub zapisane dowody → porównanie kotew → jawna decyzja. Zapis decyzji nie przesuwa części.\nZakres: cztery/dwa przypięte uchwyty. Pozostałe części i pełny odbiór skrzyni wymagają osobnej kontroli.","ROCKPRO • H7159 GROUP DECISIONS\nOpen CAD measurement or saved evidence → compare anchors → explicit decision. Recording does not move parts.\nScope: four/two bound handles. Other parts and full-case acceptance require separate checks.");
  load.Text=T("Wczytaj zapisane decyzje","Reload saved decisions");measurement.Text=T("Wczytaj pomiar…","Load measurement…");preview.Text=T("Oblicz podgląd decyzji","Preview decision");save.Text=T("Zapisz decyzję, bez CAD","Record decision, no CAD");
  readCad.Text=T("Zmierz uchwyty z IronCAD","Measure handles in IronCAD");
  loading=true;int selected=choice.SelectedIndex;choice.Items.Clear();choice.Items.AddRange(new[]{T("Zachowaj bezwzględne pozycje","Preserve absolute positions"),T("Wróć do reguły dla grupy","Restore group rule"),T("Zapisz zmierzone odsadzenia kotew","Adopt measured anchor offsets"),T("Pozostaw zmienione elementy ręczne","Leave changed members manual")});choice.SelectedIndex=selected;loading=false;
  referenceLabel.Text=T("Podstawa decyzji / uwaga konstruktora (wymagana przy zapisie)","Decision reference / constructor note (required to save)");string[] columns={T("Uchwyt","Handle"),T("Bazowo XYZ [mm]","Baseline XYZ [mm]"),T("W pomiarze XYZ [mm]","Measured XYZ [mm]"),T("Propozycja XYZ [mm]","Proposed XYZ [mm]"),T("Ręczne ΔXYZ [mm]","Manual ΔXYZ [mm]")};for(int i=0;i<5;i++)differences.Columns[i].HeaderText=columns[i];
  tips.SetToolTip(save,T("Zapisuje oświadczenie operatora we wspólnej SQLite. Nie przesuwa części i nie nadaje zgody produkcyjnej.","Records an operator claim in shared SQLite. Does not move parts or approve production."));}
}
}
