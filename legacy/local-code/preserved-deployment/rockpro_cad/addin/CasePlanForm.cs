using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace RockPro.CAD {
[ComVisible(false)]
internal sealed class CasePlanForm : Form {
 readonly string projectId;
 readonly Func<string,object,Dictionary<string,object>> backend;
 readonly bool autoLoad;
 readonly ToolTip tips=new ToolTip {AutoPopDelay=20000};
 readonly Label explanation=new Label(),metrics=new Label(),status=new Label(),operationLabel=new Label();
 readonly Button prepare=new StudioButton(),load=new StudioButton(),savePlan=new StudioButton(),execute=new StudioButton(),read=new StudioButton(),recover=new StudioButton();
 readonly TextBox operation=new TextBox();
 readonly DataGridView groups=Grid(),parts=Grid();
 readonly TabControl tabs=new TabControl();
 readonly TabPage groupTab=new TabPage(),partTab=new TabPage();
 Dictionary<string,object> request,plan;
 long revision;
 string planId="",lastState="";
 bool busy,pendingOperation;
 internal CasePlanForm(string id):this(id,Rpc.Call,true) {}
 internal CasePlanForm(string id,Func<string,object,Dictionary<string,object>> rpc,bool start) {
  projectId=id;backend=rpc;autoLoad=start;
  Size=new Size(1160,800);MinimumSize=new Size(980,700);StartPosition=FormStartPosition.CenterParent;
  AutoScaleMode=AutoScaleMode.Dpi;Font=new Font("Segoe UI",10);BackColor=Color.FromArgb(244,246,249);
  var root=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=5,Padding=new Padding(18)};
  root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
  root.RowStyles.Add(new RowStyle(SizeType.AutoSize));root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  root.RowStyles.Add(new RowStyle(SizeType.AutoSize));root.RowStyles.Add(new RowStyle(SizeType.Percent,100));
  root.RowStyles.Add(new RowStyle(SizeType.Absolute,170));Controls.Add(root);
  explanation.AutoSize=true;explanation.ForeColor=Color.FromArgb(42,53,67);explanation.Margin=new Padding(0,0,0,12);
  root.Controls.Add(explanation,0,0);root.SizeChanged+=delegate{explanation.MaximumSize=new Size(Math.Max(400,root.ClientSize.Width-40),0);};
  var toolbar=new FlowLayoutPanel {Dock=DockStyle.Fill,AutoSize=true,WrapContents=true,Margin=new Padding(0,0,0,8)};
  foreach(var button in new[]{prepare,load,savePlan,execute}){Style(button,button==execute);toolbar.Controls.Add(button);}
  root.Controls.Add(toolbar,0,1);metrics.AutoSize=true;metrics.Margin=new Padding(0,0,0,10);root.Controls.Add(metrics,0,2);
  groupTab.Controls.Add(groups);partTab.Controls.Add(parts);tabs.TabPages.Add(groupTab);tabs.TabPages.Add(partTab);tabs.Dock=DockStyle.Fill;root.Controls.Add(tabs,0,3);
  var footer=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=2};
  footer.RowStyles.Add(new RowStyle(SizeType.AutoSize));footer.RowStyles.Add(new RowStyle(SizeType.Percent,100));
  var recoverRow=new FlowLayoutPanel {Dock=DockStyle.Fill,AutoSize=true,WrapContents=true,Margin=new Padding(0,6,0,0)};
  operationLabel.AutoSize=true;operationLabel.Margin=new Padding(0,8,5,0);operation.Width=280;operation.Margin=new Padding(0,4,8,0);
  Style(read,false);Style(recover,false);read.Width=160;recover.Width=180;
  recoverRow.Controls.Add(operationLabel);recoverRow.Controls.Add(operation);recoverRow.Controls.Add(read);recoverRow.Controls.Add(recover);
  footer.Controls.Add(recoverRow,0,0);status.Dock=DockStyle.Fill;status.AutoEllipsis=false;status.Margin=new Padding(0,8,0,0);footer.Controls.Add(status,0,1);root.Controls.Add(footer,0,4);
  prepare.Click+=async delegate{await Run(Prepare);};load.Click+=async delegate{await Run(LoadSaved);};
  savePlan.Click+=async delegate{await Run(SaveAndPlan);};execute.Click+=async delegate{await Run(Execute);};
  read.Click+=async delegate{await Run(async delegate{await ReadOperation(false);});};recover.Click+=async delegate{await Run(async delegate{await ReadOperation(true);});};
  operation.TextChanged+=delegate{UpdateButtons();};Shown+=async delegate{if(autoLoad)await Run(LoadSaved);};
  FormClosing+=delegate(object sender,FormClosingEventArgs e){if(busy)e.Cancel=true;};
  UiText.LanguageChanged+=RefreshLanguage;FormClosed+=delegate{UiText.LanguageChanged-=RefreshLanguage;tips.Dispose();};
  RefreshLanguage(null,EventArgs.Empty);UpdateButtons();
 }
 static string T(string pl,string en){return UiText.T(pl,en);}
 static DataGridView Grid(){var grid=new DataGridView {Dock=DockStyle.Fill,ReadOnly=true,AllowUserToAddRows=false,
  AllowUserToDeleteRows=false,AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill,BackgroundColor=Color.White,
  BorderStyle=BorderStyle.None,RowHeadersVisible=false,SelectionMode=DataGridViewSelectionMode.FullRowSelect,
  ColumnHeadersHeightSizeMode=DataGridViewColumnHeadersHeightSizeMode.AutoSize,AutoSizeRowsMode=DataGridViewAutoSizeRowsMode.AllCells};
  grid.DefaultCellStyle.Padding=new Padding(5,4,5,4);grid.DefaultCellStyle.SelectionBackColor=Color.FromArgb(255,229,208);
  grid.DefaultCellStyle.SelectionForeColor=Color.FromArgb(35,47,60);grid.AlternatingRowsDefaultCellStyle.BackColor=Color.FromArgb(248,250,252);return grid;}
 static void Style(Button b,bool primary){b.Width=215;b.Height=42;b.Margin=new Padding(0,0,8,6);
  b.BackColor=primary?Color.FromArgb(237,102,21):Color.White;b.ForeColor=primary?Color.White:Color.FromArgb(35,47,60);}
 async Task<Dictionary<string,object>> Call(string name,object args){return await Task.Run(()=>backend(name,args));}
 async Task Run(Func<Task> action){if(busy)return;busy=true;UpdateButtons();status.ForeColor=Color.FromArgb(80,94,110);
  status.Text=T("Trwa operacja…","Working…");try{await action();}catch(Exception ex){status.ForeColor=Color.FromArgb(174,44,44);
   status.Text=ex.Message+(pendingOperation?T("\nWynik CAD jest niepewny. Odczytaj stan lub odzyskaj operację z dowodów; nie ponawiaj tworzenia.","\nCAD outcome is unknown. Read the status or recover from evidence; do not repeat creation."):
   T("\nNie ponowiono zapisu. Wczytaj aktualne dane przed porównaniem i kolejnym zapisem.","\nSaving was not retried. Reload current data before comparing and saving again."));
  }finally{busy=false;if(!IsDisposed)UpdateButtons();}}
 void UpdateButtons(){if(IsDisposed)return;prepare.Enabled=!busy&&!pendingOperation;load.Enabled=!busy;
  savePlan.Enabled=!busy&&!pendingOperation&&request!=null;execute.Enabled=!busy&&!pendingOperation&&planId.Length>0;
  read.Enabled=recover.Enabled=!busy&&operation.Text.Trim().Length>0;operation.Enabled=!busy;}
 async Task LoadSaved(){var operations=await Call("list_case_operations",new {project_id=projectId,limit=50});
  foreach(var item in Rpc.Rows(operations["operations"])){var row=Rpc.Obj(item);string state=Rpc.Str(row,"state");
   if(state!="registered"&&state!="failed"){operation.Text=Rpc.Str(row,"operation_id");pendingOperation=true;await ReadOperation(false);return;}}
  pendingOperation=false;
  var current=await Call("get_case_request",new {project_id=projectId});revision=Convert.ToInt64(current["revision"]);
  planId="";plan=null;request=current.ContainsKey("request")&&current["request"]!=null?Rpc.Obj(current["request"]):null;
  if(request==null){groups.Rows.Clear();parts.Rows.Clear();metrics.Text=T("Brak zapisanego żądania. Przygotuj prototyp z zapisanego układu.","No saved request. Prepare a prototype from the saved layout.");}
  else ShowPlan(await Call("preview_case",new {request=request}));
  status.Text=T("Odczytano żądanie, rewizja ","Request loaded, revision ")+revision+T(". Przygotowanie i zapis nie uruchamiają CAD.",". Preparation and saving do not run CAD.");}
 async Task Prepare(){planId="";plan=null;var layout=await Call("get_layout",new {project_id=projectId});
  if(!Convert.ToBoolean(layout["saved"]))throw new Exception(T("Najpierw zapisz układ w konfiguratorze 3D.","Save the layout in the 3D editor first."));
  var prepared=await Call("prepare_case_request",new {project_id=projectId,expected_layout_revision=layout["revision"]});
  var current=await Call("get_case_request",new {project_id=projectId});revision=Convert.ToInt64(current["revision"]);
  request=Rpc.Obj(prepared["request"]);ShowPlan(Rpc.Obj(prepared["preview"]));
  status.Text=T("Prototyp przygotowany z zapisanego układu. Sprawdź grupy i bryły, a następnie zapisz plan.","Prototype prepared from the saved layout. Review groups and solids, then save the plan.");}
 async Task SaveAndPlan(){planId="";var saved=await Call("save_case_request",new {project_id=projectId,request=request,expected_revision=revision,actor="UI",change_source="addin-case-prototype"});
  if(!saved.ContainsKey("saved")||!Convert.ToBoolean(saved["saved"])){ShowPlan(Rpc.Obj(saved["preview"]));return;}
  revision=Convert.ToInt64(saved["revision"]);var result=await Call("plan_project_case",new {project_id=projectId,expected_revision=revision});
  ShowPlan(Rpc.Obj(result["plan"]));if(Rpc.Str(result,"status")!="planned")return;
  planId=Rpc.Str(result,"plan_id");var binding=Rpc.Obj(result["binding"]);
  status.Text=T("Plan zapisany, rewizja ","Plan saved, revision ")+revision+T(". Źródło przypięte: ",". Pinned source: ")+Rpc.Str(binding,"source")+
   T("\nPrzycisk tworzenia uruchomi nowy prototyp ICS z bryłami zastępczymi.","\nThe create button will build a new ICS prototype with proxy solids.");}
 async Task Execute(){string selectedPlan=planId;operation.Text=Guid.NewGuid().ToString("N");pendingOperation=true;UpdateButtons();
  Exception error=null;Dictionary<string,object> result=null;
  try{result=await Call("execute_case_plan",new {project_id=projectId,plan_id=selectedPlan,operation_id=operation.Text,expected_revision=revision});}catch(Exception ex){error=ex;}
  if(error!=null){try{ShowOperation(await Call("get_case_operation",new {project_id=projectId,operation_id=operation.Text}));}
   catch(Exception journalError){if(journalError.Message.Contains("CASE_OPERATION_NOT_FOUND")){pendingOperation=false;planId="";}}
   throw error;
  }ShowOperation(result);}
 async Task ReadOperation(bool recoverEvidence){ShowOperation(await Call(recoverEvidence?"recover_case_operation":"get_case_operation",new {project_id=projectId,operation_id=operation.Text.Trim()}));}
 void ShowOperation(Dictionary<string,object> result){lastState=Rpc.Str(result,"status");pendingOperation=lastState!="registered"&&lastState!="failed";if(!pendingOperation)planId="";
  if(lastState=="registered")status.Text=T("Prototyp zapisany i ponownie otwarty; archiwum zarejestrowane. Źródło projektu zachowane.\n","Prototype saved and reopened; archive registered. Project source preserved.\n")+Rpc.Str(result,"snapshot_path")+
   T("\nWalidacja: prototyp syntetyczny; bez odbioru produkcyjnego.","\nValidation: synthetic prototype; no production acceptance.");
  else status.Text=T("Stan operacji: ","Operation state: ")+State(lastState)+T(". ID: ",". ID: ")+operation.Text+
   (pendingOperation?T("\nSprawdź dowody i użyj odzyskiwania. Tworzenie nie zostanie ponowione automatycznie.","\nInspect the evidence and use recovery. Creation will not be repeated automatically."):
    T("\nOperacja nieudana; nie zarejestrowano archiwum.","\nOperation failed; no archive was registered."));
  if(result.ContainsKey("diagnostic")&&result["diagnostic"]!=null)status.Text+="\n"+Rpc.Str(Rpc.Obj(result["diagnostic"]),"message");}
 static string State(string v){switch(v){case "registered":return T("zarejestrowana","registered");case "failed":return T("nieudana","failed");case "planned":return T("zaplanowana","planned");
  case "applying":return T("wykonywana","applying");case "saved":return T("zapisana","saved");case "reopened_verified":return T("sprawdzona po otwarciu","reopened and checked");case "outcome_unknown":return T("wynik niepewny","outcome unknown");default:return v;}}
 static string Vec(object v){return String.Join(" × ",Array.ConvertAll(Rpc.Rows(v),x=>Convert.ToDouble(x).ToString("0.##",CultureInfo.CurrentCulture)));}
 void ShowPlan(Dictionary<string,object> value){plan=value;groups.Rows.Clear();parts.Rows.Clear();
  if(Rpc.Str(value,"status")!="planned"){planId="";metrics.Text=T("Plan zablokowany.","Plan blocked.");var messages=new List<string>();
   foreach(var d in Rpc.Rows(value.ContainsKey("diagnostics")?value["diagnostics"]:null)){var detail=Rpc.Obj(d);messages.Add(Rpc.Str(detail,"code")+": "+Rpc.Str(detail,"message"));}throw new Exception(String.Join("\n",messages.ToArray()));}
  foreach(var item in Rpc.Rows(value["groups"])){var g=Rpc.Obj(item);groups.Rows.Add(Rpc.Str(g,"symmetry_group_id"),Rpc.Str(g,"family"),Rpc.Str(g,"mode"),Rpc.Str(g,"datum"),Rpc.Rows(g["members"]).Length,Rpc.Str(g,"exception_approval"));}
  foreach(var item in Rpc.Rows(value["occurrences"])){var p=Rpc.Obj(item);parts.Rows.Add(Rpc.Str(p,"id"),Rpc.Str(p,"definition"),Rpc.Str(p,"frame"),Vec(p["shape"]),Vec(p["closed_xyz"]));}
  metrics.Text=T("Sklejka [mm]: ","Plywood [mm]: ")+Vec(value["plywood_external"])+T("   •   Transport [mm]: ","   •   Transport [mm]: ")+Vec(value["transport_external"])+
   T("\nGrupy: ","\nGroups: ")+groups.Rows.Count+T("   •   Bryły zastępcze: ","   •   Proxy solids: ")+parts.Rows.Count+T("   •   Status: prototyp syntetyczny","   •   Status: synthetic prototype");}
 void RefreshLanguage(object sender,EventArgs e){if(IsDisposed)return;Text=T("RockPro CAD | Prototyp skrzyni","RockPro CAD | Case prototype");
  explanation.Text=T("PROTOTYP SKRZYNI • mm\nZapisany układ → grupy symetrii i plan części → nowy plik ICS. Płyty, profile, okucia i wnętrze są bryłami zastępczymi.\nDwa urządzenia, przegrody i komora X/Y. Katalog Epson, wycięcia, styki, kolizje i nośność wymagają osobnego odbioru.",
   "CASE PROTOTYPE • mm\nSaved layout → symmetry groups and part proposal → new ICS file. Panels, profiles, hardware and inserts are proxy solids.\nTwo devices, dividers and an X/Y compartment. Epson catalog, cutouts, joints, collisions and strength require separate acceptance.");
  prepare.Text=T("Przygotuj z układu","Prepare from layout");load.Text=T("Wczytaj zapisane","Reload saved request");savePlan.Text=T("Zapisz i przypnij plan","Save and pin plan");execute.Text=T("Utwórz prototyp ICS","Create ICS prototype");
  read.Text=T("Odczytaj stan","Read operation");recover.Text=T("Odzyskaj z dowodów","Recover from evidence");operationLabel.Text=T("ID operacji:","Operation ID:");groupTab.Text=T("Grupy symetrii","Symmetry groups");partTab.Text=T("Bryły zastępcze","Proxy solids");
  Columns(groups,new[]{T("Grupa","Group"),T("Rodzina","Family"),T("Tryb","Mode"),T("Odniesienie","Datum"),T("Sztuk","Count"),T("Zgoda testowa","Test approval")});
  Columns(parts,new[]{T("Wystąpienie","Occurrence"),T("Definicja","Definition"),T("Rama","Frame"),T("Wymiary [mm]","Shape [mm]"),T("Położenie XYZ [mm]","Closed XYZ [mm]")});
  tips.SetToolTip(prepare,T("Używa zapisanego układu bez zmiany liczby urządzeń i komory.","Uses the saved layout without changing device count or compartment."));
  tips.SetToolTip(savePlan,T("Zapis CAS we wspólnej bazie. Konflikt zatrzymuje zapis i zachowuje dane formularza.","CAS save to the shared database. A conflict stops saving and preserves form data."));
  tips.SetToolTip(execute,T("Otwórz przypięte źródło ICS w IronCAD. Powstaje nowy plik z bryłami zastępczymi i osobne archiwum.","Open the pinned source ICS in IronCAD. Creates a new file with proxy solids and a separate archive."));
  tips.SetToolTip(operation,T("Po utracie odpowiedzi zachowaj ID. Nieukończona operacja zostanie odczytana przy otwarciu okna.","Keep the ID if a reply is lost. An unfinished operation is loaded when this window opens."));
  tips.SetToolTip(recover,T("Sprawdza istniejące dowody; nie uruchamia ponownie CAD.","Checks existing evidence; never runs CAD again."));
  if(plan!=null&&Rpc.Str(plan,"status")=="planned")ShowPlan(plan);
 }
 static void Columns(DataGridView g,string[] labels){if(g.Columns.Count==0)for(int i=0;i<labels.Length;i++)g.Columns.Add("c"+i,labels[i]);
  for(int i=0;i<labels.Length;i++)g.Columns[i].HeaderText=labels[i];g.ColumnHeadersDefaultCellStyle.WrapMode=DataGridViewTriState.True;}
}
}
