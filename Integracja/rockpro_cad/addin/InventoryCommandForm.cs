using System;
using System.Collections.Generic;
using System.Drawing;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace RockPro.CAD {
[System.Runtime.InteropServices.ComVisible(false)]
internal sealed class InventoryCommandForm : Form {
 sealed class Item {
  internal Dictionary<string,object> Data;
  internal string Kind;
  public override string ToString(){return Rpc.Str(Data,Kind=="request"?"operation_id":"id")+" • "+
   (Kind=="lot"?Rpc.Str(Data,"item_id")+" • "+Unit(Rpc.Str(Data,"unit"))+" • v"+Rpc.Str(Data,"revision"):
    State(Rpc.Str(Data,Kind=="request"?"state":"status")));}
 }
 readonly Func<string,object,Dictionary<string,object>> backend;
 readonly int uiThread=System.Threading.Thread.CurrentThread.ManagedThreadId;
 readonly ComboBox action=new ScrollSafeChoice {DropDownStyle=ComboBoxStyle.DropDownList},lots=new ScrollSafeChoice {DropDownStyle=ComboBoxStyle.DropDownList},holds=new ScrollSafeChoice {DropDownStyle=ComboBoxStyle.DropDownList},requests=new ScrollSafeChoice {DropDownStyle=ComboBoxStyle.DropDownList};
 readonly TextBox plan=new TextBox(),reservation=new TextBox(),reference=new TextBox(),lookup=new TextBox(),operation=new TextBox {ReadOnly=true};
 readonly NumericUpDown quantity=new ScrollSafeNumber {Minimum=1,Maximum=1000000,Value=1};
 readonly Button reload=new Button(),open=new Button(),prepare=new Button(),execute=new Button(),cancel=new Button(),read=new Button(),fresh=new Button();
 readonly Label heading=new Label(),status=new Label();
 readonly GroupBox lookupGroup=new GroupBox(),operationGroup=new GroupBox();
 readonly TextBox summary=new TextBox {Multiline=true,ReadOnly=true,ScrollBars=ScrollBars.Both,WordWrap=false};
 readonly List<Label> captions=new List<Label>();
 readonly string[] actions={"reserve","issue","cancel","consume","return"};
 Dictionary<string,object> inventoryData,pendingPrepare,loadedIntent;
 bool busy,loading,uncertain,canRetryPreparation;
 static string T(string pl,string en){return LayoutLanguage.T(pl,en);}
 static string Unit(string key){return key=="piece"?T("szt.","piece"):key=="sheet"?T("arkusz","sheet"):key=="offcut"?T("resztka","offcut"):key;}
 static string State(string key){switch(key){case "prepared":return T("Przygotowane","Prepared");case "committed":return T("Zapisane z kwitem","Committed with receipt");case "rejected":return T("Odrzucone","Rejected");case "cancelled":return T("Anulowane","Cancelled");case "held":return T("Zarezerwowane","Held");case "issued":return T("Wydane","Issued");default:return key;}}
 internal InventoryCommandForm():this(Rpc.Call,true){}
 internal InventoryCommandForm(Func<string,object,Dictionary<string,object>> call,bool autoLoad){
  backend=call;Size=new Size(1260,900);MinimumSize=new Size(1100,760);Font=new Font("Segoe UI",10);AutoScaleMode=AutoScaleMode.Dpi;
  plan.MaxLength=reservation.MaxLength=lookup.MaxLength=100;reference.MaxLength=1000;lots.DropDownWidth=700;requests.DropDownWidth=800;
  BackColor=Color.FromArgb(242,246,249);Padding=new Padding(18);StartPosition=FormStartPosition.CenterParent;
  var root=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=2,RowCount=3};root.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,425));root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
  root.RowStyles.Add(new RowStyle(SizeType.Absolute,100));root.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.RowStyles.Add(new RowStyle(SizeType.Absolute,130));Controls.Add(root);
  heading.Dock=DockStyle.Fill;heading.Padding=new Padding(10);heading.BackColor=Color.FromArgb(255,235,214);root.Controls.Add(heading,0,0);root.SetColumnSpan(heading,2);
  var scroll=new Panel {Dock=DockStyle.Fill,AutoScroll=true};root.Controls.Add(scroll,0,1);var settings=new FlowLayoutPanel {Dock=DockStyle.Top,AutoSize=true,WrapContents=false,FlowDirection=FlowDirection.TopDown,Padding=new Padding(0,8,12,8)};scroll.Controls.Add(settings);
  Add(settings,T("Operacja","Action"),action);action.Items.AddRange(new object[]{T("Rezerwacja","Reserve"),T("Wydanie","Issue"),T("Anulowanie rezerwacji","Cancel hold"),T("Zużycie wydanego materiału","Consume issued stock"),T("Zwrot niewykorzystanego materiału","Return unused stock")});action.SelectedIndex=0;
  Add(settings,T("Partia / resztka (rezerwacja)","Lot / offcut (reservation)"),lots);Add(settings,T("Istniejąca rezerwacja / wydanie","Existing hold / issue"),holds);
  Add(settings,T("ID planu (rezerwacja)","Plan ID (reservation)"),plan);Add(settings,T("ID nowej rezerwacji","New reservation ID"),reservation);reservation.Text="hold-"+Guid.NewGuid().ToString("N");
  Add(settings,T("Ilość w jednostce partii","Quantity in lot units"),quantity);Add(settings,T("Podstawa polecenia / uwaga operatora","Instruction reference / operator note"),reference);
  var right=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=6,Padding=new Padding(12,8,0,0)};
  right.RowStyles.Add(new RowStyle(SizeType.Absolute,35));right.RowStyles.Add(new RowStyle(SizeType.Absolute,40));right.RowStyles.Add(new RowStyle(SizeType.Absolute,45));right.RowStyles.Add(new RowStyle(SizeType.Absolute,60));right.RowStyles.Add(new RowStyle(SizeType.Absolute,60));right.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.Controls.Add(right,1,1);
  var requestCaption=new Label {Dock=DockStyle.Fill,Text=T("Żądania z bazy — ostatnie 100","Stored requests — latest 100")};captions.Add(requestCaption);right.Controls.Add(requestCaption,0,0);requests.Dock=DockStyle.Fill;right.Controls.Add(requests,0,1);
  var tools=new FlowLayoutPanel {Dock=DockStyle.Fill};Style(reload,T("Odśwież dane","Refresh data"));Style(open,T("Otwórz żądanie","Open request"));tools.Controls.Add(reload);tools.Controls.Add(open);right.Controls.Add(tools,0,2);
  lookup.Dock=DockStyle.Fill;lookupGroup.Dock=DockStyle.Fill;lookupGroup.Controls.Add(lookup);right.Controls.Add(lookupGroup,0,3);operation.Dock=DockStyle.Fill;operationGroup.Dock=DockStyle.Fill;operationGroup.Controls.Add(operation);right.Controls.Add(operationGroup,0,4);summary.Dock=DockStyle.Fill;right.Controls.Add(summary,0,5);
  lookup.AccessibleName=T("Wpisz ID żądania lub wybierz je z listy","Enter a request ID or choose it from the list");operation.AccessibleName=T("Bieżący identyfikator operacji","Current operation ID");
  var footer=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=2};footer.RowStyles.Add(new RowStyle(SizeType.Absolute,50));footer.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.Controls.Add(footer,0,2);root.SetColumnSpan(footer,2);
  var buttons=new FlowLayoutPanel {Dock=DockStyle.Fill};Style(prepare,T("Zapisz żądanie","Prepare request"));Style(execute,T("Wykonaj żądanie","Execute request"));Style(cancel,T("Anuluj żądanie","Cancel request"));Style(read,T("Sprawdź wynik","Read outcome"));Style(fresh,T("Nowe żądanie","New request"));
  execute.BackColor=Color.FromArgb(237,102,21);execute.ForeColor=Color.White;foreach(var button in new[]{prepare,execute,cancel,read,fresh})buttons.Controls.Add(button);footer.Controls.Add(buttons,0,0);status.Dock=DockStyle.Fill;status.Padding=new Padding(0,8,0,0);footer.Controls.Add(status,0,1);
  reload.Click+=async delegate{await Run(LoadData);};open.Click+=async delegate{await Run(OpenExisting);};prepare.Click+=async delegate{await Run(Prepare);};execute.Click+=async delegate{await Run(Execute);};cancel.Click+=async delegate{await Run(Cancel);};read.Click+=async delegate{await Run(Read);};fresh.Click+=delegate{NewRequest();};
  action.SelectedIndexChanged+=delegate{if(!loading){FillHolds();UpdateButtons();ShowSummary();}};lots.SelectedIndexChanged+=delegate{UpdateButtons();ShowSummary();};holds.SelectedIndexChanged+=delegate{UpdateButtons();ShowSummary();};
  requests.SelectedIndexChanged+=delegate{var item=requests.SelectedItem as Item;if(item!=null)lookup.Text=Rpc.Str(item.Data,"operation_id");UpdateButtons();};
  foreach(var input in new[]{plan,reservation,reference,lookup})input.TextChanged+=delegate{UpdateButtons();ShowSummary();};quantity.ValueChanged+=delegate{ShowSummary();};
  Shown+=async delegate{if(autoLoad)await Run(LoadData);};FormClosing+=delegate(object sender,FormClosingEventArgs e){if(busy)e.Cancel=true;};
  UiText.LanguageChanged+=RefreshLanguage;FormClosed+=delegate{UiText.LanguageChanged-=RefreshLanguage;};RefreshLanguage(null,EventArgs.Empty);UpdateButtons();ShowSummary();
 }
 void Add(FlowLayoutPanel parent,string text,Control control){var caption=new Label {Text=text,Width=390,Height=35,Padding=new Padding(0,9,0,0)};captions.Add(caption);parent.Controls.Add(caption);control.Width=385;control.Margin=new Padding(0,0,0,8);parent.Controls.Add(control);}
 static void Style(Button button,string text){button.Text=text;button.Size=new Size(190,40);button.Margin=new Padding(0,0,8,4);button.BackColor=Color.White;}
 string Key {get{return action.SelectedIndex<0?"reserve":actions[action.SelectedIndex];}}
 bool Terminal {get{return loadedIntent!=null&&Rpc.Str(loadedIntent,"state")!="prepared";}}
 bool Supported {get{return loadedIntent==null||Array.IndexOf(actions,Rpc.Str(Rpc.Obj(loadedIntent["command"]),"action"))>=0;}}
 async Task<Dictionary<string,object>> Call(string name,object args){return await Task.Run(()=>backend(name,args));}
 async Task Run(Func<Task> work){
  if(System.Threading.Thread.CurrentThread.ManagedThreadId!=uiThread)throw new InvalidOperationException("Inventory command UI must start on its owner thread");
  System.Threading.SynchronizationContext.SetSynchronizationContext(new WindowsFormsSynchronizationContext());if(busy)return;busy=true;UpdateButtons();
  try{await work();}catch(Exception ex){status.ForeColor=Color.Firebrick;status.Text=ex.Message+T("\nDane i ID zachowane. Sprawdź wynik; nie ponowiono wykonania ani nie odświeżono rewizji.","\nInputs and ID retained. Read the outcome; execution was not retried and revisions were not refreshed.");}
  finally{busy=false;if(!IsDisposed){UpdateButtons();ShowSummary();}}
 }
 void UpdateButtons(){if(IsDisposed)return;bool draft=operation.Text.Length==0;bool selected=Key=="reserve"?lots.SelectedItem!=null:holds.SelectedItem!=null;
  action.Enabled=!busy&&draft;lots.Enabled=!busy&&draft&&Key=="reserve";holds.Enabled=!busy&&draft&&Key!="reserve";
  plan.Enabled=reservation.Enabled=!busy&&draft&&Key=="reserve";quantity.Enabled=!busy&&draft&&(Key=="reserve"||Key=="return");reference.Enabled=!busy&&draft;
  prepare.Enabled=!busy&&((draft&&selected&&reference.Text.Trim().Length>0&&(Key!="reserve"||plan.Text.Trim().Length>0&&reservation.Text.Trim().Length>0))||canRetryPreparation);
  prepare.Text=canRetryPreparation?T("Ponów zapis tego ID","Retry same preparation"):T("Zapisz żądanie","Prepare request");
  cancel.Enabled=!busy&&!uncertain&&loadedIntent!=null&&Rpc.Str(loadedIntent,"state")=="prepared";execute.Enabled=cancel.Enabled&&Supported;
  read.Enabled=!busy&&operation.Text.Length>0;fresh.Enabled=!busy&&!uncertain&&(draft||Terminal);reload.Enabled=!busy;
  requests.Enabled=lookup.Enabled=!busy&&(draft||Terminal);open.Enabled=!busy&&(draft||Terminal)&&lookup.Text.Trim().Length>0;
 }
 async Task LoadData(){var data=await Call("get_inventory",new {});var saved=await Call("list_inventory_intents",new {state="all",limit=100});
  string selectedLot=lots.SelectedItem is Item?Rpc.Str(((Item)lots.SelectedItem).Data,"id"):"";inventoryData=data;loading=true;
  try{lots.Items.Clear();foreach(var value in Rpc.Rows(data["lots"])){var item=new Item {Data=Rpc.Obj(value),Kind="lot"};lots.Items.Add(item);if(Rpc.Str(item.Data,"id")==selectedLot)lots.SelectedItem=item;}
   requests.Items.Clear();foreach(var value in Rpc.Rows(saved["intents"]))requests.Items.Add(new Item {Data=Rpc.Obj(value),Kind="request"});requests.SelectedIndex=-1;FillHolds();}
  finally{loading=false;}status.ForeColor=Color.FromArgb(55,75,95);status.Text=T("Dane wczytane. Wybierz partię/rezerwację albo jawnie otwórz zapisane żądanie. Odczyt nie wykonuje poleceń.","Data loaded. Choose a lot/hold or explicitly open a stored request. Reading never executes commands.");}
 void FillHolds(){string selected=holds.SelectedItem is Item?Rpc.Str(((Item)holds.SelectedItem).Data,"id"):"";holds.Items.Clear();if(inventoryData==null)return;
  foreach(var value in Rpc.Rows(inventoryData["reservations"])){var row=Rpc.Obj(value);string state=Rpc.Str(row,"status");bool allowed=(Key=="issue"||Key=="cancel")?state=="held":(Key=="consume"||Key=="return")&&state=="issued";
   if(allowed){var item=new Item {Data=row,Kind="hold"};holds.Items.Add(item);if(Rpc.Str(row,"id")==selected)holds.SelectedItem=item;}}
 }
 Dictionary<string,object> BuildCommand(out long revision){
  var command=new Dictionary<string,object>{{"action",Key}};Dictionary<string,object> lot;
  if(Key=="reserve"){
   if(!(lots.SelectedItem is Item))throw new Exception(T("Wybierz partię.","Choose a lot."));lot=((Item)lots.SelectedItem).Data;
   foreach(string id in new[]{plan.Text.Trim(),reservation.Text.Trim()})if(!System.Text.RegularExpressions.Regex.IsMatch(id,@"^[A-Za-z0-9_.-]{1,100}$"))throw new Exception(T("ID planu i rezerwacji: litery ASCII, cyfry, kropka, myślnik lub podkreślenie; do 100 znaków.","Plan and reservation IDs: ASCII letters, digits, dot, hyphen or underscore; up to 100 characters."));
   command["lot_id"]=Rpc.Str(lot,"id");command["reservation_id"]=reservation.Text.Trim();command["plan_id"]=plan.Text.Trim();command["quantity"]=(int)quantity.Value;
  }else{
   if(!(holds.SelectedItem is Item))throw new Exception(T("Wybierz rezerwację / wydanie.","Choose a hold / issue."));var hold=((Item)holds.SelectedItem).Data;command["reservation_id"]=Rpc.Str(hold,"id");lot=null;
   foreach(var value in Rpc.Rows(inventoryData["lots"])){var candidate=Rpc.Obj(value);if(Rpc.Str(candidate,"id")==Rpc.Str(hold,"lot_id")){lot=candidate;break;}}
   if(lot==null)throw new Exception(T("Brak partii dla tej rezerwacji.","Reservation lot is missing."));if(Key=="return")command["quantity"]=(int)quantity.Value;
  }
  revision=Convert.ToInt64(lot["revision"]);return command;
 }
 async Task Prepare(){
  if(pendingPrepare==null){long revision;var command=BuildCommand(out revision);operation.Text=Guid.NewGuid().ToString("N");
   pendingPrepare=new Dictionary<string,object>{{"command",command},{"operation_id",operation.Text},{"expected_revision",revision},{"decision_reference",reference.Text.Trim()},{"actor","UI"}};}
  uncertain=true;canRetryPreparation=false;loadedIntent=await Call("prepare_inventory_command",pendingPrepare);uncertain=false;
  status.ForeColor=Color.FromArgb(55,75,95);status.Text=T("Żądanie zapisane. Sprawdź treść i wersję; wykonanie jest osobną akcją i ponownie sprawdzi dostępność.","Request saved. Review its contents and revision; execution is a separate action and rechecks availability.");
 }
 async Task Execute(){uncertain=true;loadedIntent=await Call("execute_inventory_intent",new {operation_id=operation.Text});uncertain=false;ShowOutcome();}
 async Task Cancel(){uncertain=true;loadedIntent=await Call("cancel_inventory_intent",new {operation_id=operation.Text,command_sha256=loadedIntent["command_sha256"]});uncertain=false;ShowOutcome();}
 async Task Read(){
  uncertain=true;
  try{loadedIntent=await Call("get_inventory_intent",new {operation_id=operation.Text});uncertain=false;canRetryPreparation=false;ShowOutcome();}
  catch(Exception ex){if(ex.Message.Contains("INVENTORY_INTENT_NOT_FOUND")&&pendingPrepare!=null){canRetryPreparation=true;uncertain=true;}throw;}
 }
 async Task OpenExisting(){string id=lookup.Text.Trim();var saved=await Call("get_inventory_intent",new {operation_id=id});loadedIntent=saved;pendingPrepare=null;operation.Text=id;uncertain=false;canRetryPreparation=false;ShowOutcome();}
 void NewRequest(){if(uncertain||loadedIntent!=null&&!Terminal)return;operation.Text="";pendingPrepare=loadedIntent=null;canRetryPreparation=false;reservation.Text="hold-"+Guid.NewGuid().ToString("N");status.Text=T("Nowy szkic. Odśwież dane przed wyborem partii; wcześniejsze żądanie pozostaje w historii.","New draft. Refresh before selecting stock; the previous request remains in history.");UpdateButtons();ShowSummary();}
 void ShowOutcome(){string state=Rpc.Str(loadedIntent,"state");status.ForeColor=state=="rejected"?Color.Firebrick:Color.FromArgb(55,75,95);
  status.Text=T("Stan żądania: ","Request state: ")+State(state)+". "+(state=="committed"?T("Kwit zachowany; nie wykonujemy ponownie.","Receipt retained; execution is not repeated."):state=="prepared"?T("Polecenie nie ma jeszcze zachowanego wyniku. Wykonanie wymaga jawnej akcji.","No committed result yet. Execution requires an explicit action."):T("Żądanie zakończone; zmiana danych wymaga nowego żądania.","Request is terminal; changing inputs requires a new request."));
  if(loadedIntent.ContainsKey("diagnostic")&&loadedIntent["diagnostic"]!=null)status.Text+="\n"+Rpc.Str(loadedIntent,"diagnostic");
 }
 void ShowSummary(){if(IsDisposed)return;var text=new StringBuilder();text.AppendLine(T("ID operacji: ","Operation ID: ")+operation.Text);
  var command=loadedIntent!=null?Rpc.Obj(loadedIntent["command"]):pendingPrepare!=null?Rpc.Obj(pendingPrepare["command"]):null;
  if(command!=null){text.AppendLine(T("Przypięta wersja: ","Pinned revision: ")+Convert.ToString((loadedIntent??pendingPrepare)["expected_revision"]));foreach(var pair in command){string caption=pair.Key=="lot_id"?T("Partia","Lot"):pair.Key=="reservation_id"?T("Rezerwacja","Reservation"):pair.Key=="plan_id"?T("Plan","Plan"):pair.Key=="quantity"?T("Ilość","Quantity"):pair.Key=="action"?T("Operacja","Action"):pair.Key;int index=pair.Key=="action"?Array.IndexOf(actions,Convert.ToString(pair.Value)):-1;string value=index>=0?Convert.ToString(action.Items[index]):pair.Value is Dictionary<string,object>?new System.Web.Script.Serialization.JavaScriptSerializer().Serialize(pair.Value):Convert.ToString(pair.Value);text.AppendLine(caption+": "+value);}
   ShowStockContext(text,command);
   text.AppendLine();text.AppendLine(T("Podstawa polecenia: ","Instruction reference: ")+Convert.ToString((loadedIntent??pendingPrepare)["decision_reference"]));
   if(loadedIntent!=null)text.AppendLine(T("Stan: ","State: ")+State(Rpc.Str(loadedIntent,"state")));
  }else{text.AppendLine(T("Szkic — najpierw zapisz żądanie.","Draft — prepare the request first."));var item=lots.SelectedItem as Item;if(Key=="reserve"&&item!=null)text.AppendLine(item+"\n"+T("Fizycznie / rezerwacje / wolne: ","Physical / held / free: ")+Rpc.Str(item.Data,"on_hand")+" / "+Rpc.Str(item.Data,"reserved")+" / "+Rpc.Str(item.Data,"free"));}
  if(!Supported)text.AppendLine("\n"+T("Ten typ żądania można tu odczytać lub anulować. Wykonanie wymaga formularza dla tego typu operacji.","This request type can be read or cancelled here. Execution requires its dedicated operation form."));
  if(uncertain)text.AppendLine("\n"+T("Wynik niepotwierdzony. Odczytaj ten sam ID; dane i rewizja pozostają przypięte.","Outcome unconfirmed. Read this same ID; inputs and revision remain pinned."));summary.Text=text.ToString();
 }
 void ShowStockContext(StringBuilder text,Dictionary<string,object> command){
  if(inventoryData==null)return;string lotId=Rpc.Str(command,"lot_id");
  foreach(var value in Rpc.Rows(inventoryData["reservations"])){var hold=Rpc.Obj(value);if(Rpc.Str(hold,"id")==Rpc.Str(command,"reservation_id")){lotId=Rpc.Str(hold,"lot_id");text.AppendLine(T("Ilość rezerwacji / już zwrócono: ","Hold quantity / already returned: ")+Rpc.Str(hold,"quantity")+" / "+Rpc.Str(hold,"returned"));break;}}
  foreach(var value in Rpc.Rows(inventoryData["lots"])){var lot=Rpc.Obj(value);if(Rpc.Str(lot,"id")!=lotId)continue;
   text.AppendLine(T("Materiał / jednostka: ","Item / unit: ")+Rpc.Str(lot,"item_id")+" / "+Unit(Rpc.Str(lot,"unit")));
   text.AppendLine(Rpc.Str(lot,"scope")=="synthetic_test"?T("Pochodzenie: TEST syntetyczny","Provenance: SYNTHETIC TEST"):T("Pochodzenie: dane operatora","Provenance: operator input"));
   text.AppendLine(T("Ostatni odczyt partii v","Last lot read v")+Rpc.Str(lot,"revision")+T(" • fizycznie / rezerwacje / wolne: "," • physical / held / free: ")+Rpc.Str(lot,"on_hand")+" / "+Rpc.Str(lot,"reserved")+" / "+Rpc.Str(lot,"free"));break;
  }
 }
 void RefreshLanguage(object sender,EventArgs e){if(IsDisposed)return;Text=T("RockPro | Polecenia magazynowe","RockPro | Inventory commands");
  heading.Text=T("ROCKPRO • POLECENIA OPERATORA\nWybór z odczytanych danych → zapis trwałego żądania → osobne wykonanie → kwit. Rewizja nie jest odświeżana w tle.\nPrzygotowanie nie rezerwuje materiału. Niepewny wynik sprawdzaj pod tym samym ID; zgody produkcyjne pozostają odrębne.","ROCKPRO • OPERATOR COMMANDS\nChoose recorded stock → prepare a durable request → execute separately → receipt. Revisions are never refreshed in the background.\nPreparation does not reserve stock. Read uncertain outcomes using the same ID; production approvals remain separate.");
  lookupGroup.Text=T("ID do odczytu (lista lub wpis ręczny)","Request ID to open (list or manual entry)");operationGroup.Text=T("Bieżący, przypięty ID operacji","Current pinned operation ID");
  foreach(var caption in captions)caption.Text=LayoutLanguage.Translate(caption.Text);foreach(var button in new[]{reload,open,prepare,execute,cancel,read,fresh})button.Text=LayoutLanguage.Translate(button.Text);
  loading=true;try{int index=action.SelectedIndex;for(int i=0;i<action.Items.Count;i++)action.Items[i]=LayoutLanguage.Translate(Convert.ToString(action.Items[i]));action.SelectedIndex=index;}finally{loading=false;}ShowSummary();UpdateButtons();
 }
}
}
