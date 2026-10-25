using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Web.Script.Serialization;

namespace RockPro.CAD {
[System.Runtime.InteropServices.ComVisible(false)]
internal sealed class InventoryForm : Form {
 readonly Func<string,object,Dictionary<string,object>> backend;
 readonly int uiThread=System.Threading.Thread.CurrentThread.ManagedThreadId;
 readonly Label heading=new Label(),status=new Label(),limitLabel=new Label();
 readonly Button reload=new Button(),details=new Button();
 readonly NumericUpDown historyLimit=new ScrollSafeNumber {Minimum=1,Maximum=500,Value=100,Width=90};
 readonly TabControl tabs=new TabControl();
 readonly DataGridView lots=Grid(),reservations=Grid(),deliveries=Grid(),history=Grid();
 readonly TabPage lotTab=new TabPage(),reservationTab=new TabPage(),deliveryTab=new TabPage(),historyTab=new TabPage();
 readonly ToolTip tips=new ToolTip();
 Dictionary<string,object> inventoryData,historyData;
 DateTime? loadedAt;
 bool busy,failed;
 int loadedLimit;
 static string T(string pl,string en){return UiText.T(pl,en);}
 internal InventoryForm():this(Rpc.Call,true){}
 internal InventoryForm(Func<string,object,Dictionary<string,object>> call,bool autoLoad){
  backend=call;Size=new Size(1280,820);MinimumSize=new Size(1050,680);Font=new Font("Segoe UI",10);
  AutoScaleMode=AutoScaleMode.Dpi;StartPosition=FormStartPosition.CenterParent;BackColor=Color.FromArgb(242,246,249);Padding=new Padding(18);
  var root=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=4};
  root.RowStyles.Add(new RowStyle(SizeType.Absolute,100));root.RowStyles.Add(new RowStyle(SizeType.Absolute,60));
  root.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.RowStyles.Add(new RowStyle(SizeType.Absolute,85));Controls.Add(root);
  heading.Dock=DockStyle.Fill;heading.Padding=new Padding(10);heading.BackColor=Color.FromArgb(255,235,214);root.Controls.Add(heading,0,0);
  var actions=new FlowLayoutPanel {Dock=DockStyle.Fill,Padding=new Padding(0,8,0,0)};
  foreach(var button in new[]{reload,details}){button.Size=new Size(260,40);button.BackColor=Color.White;button.Margin=new Padding(0,0,10,0);actions.Controls.Add(button);}
  limitLabel.AutoSize=true;limitLabel.Margin=new Padding(8,10,5,0);actions.Controls.Add(limitLabel);historyLimit.Margin=new Padding(0,6,0,0);actions.Controls.Add(historyLimit);root.Controls.Add(actions,0,1);
  lotTab.Controls.Add(lots);reservationTab.Controls.Add(reservations);deliveryTab.Controls.Add(deliveries);historyTab.Controls.Add(history);
  tabs.TabPages.AddRange(new[]{lotTab,reservationTab,deliveryTab,historyTab});tabs.Dock=DockStyle.Fill;root.Controls.Add(tabs,0,2);
  status.Dock=DockStyle.Fill;status.Padding=new Padding(0,10,0,0);root.Controls.Add(status,0,3);
  reload.Click+=async delegate{await Reload();};details.Click+=delegate{ShowDetails();};history.SelectionChanged+=delegate{UpdateButtons();};tabs.SelectedIndexChanged+=delegate{UpdateButtons();};
  historyLimit.ValueChanged+=delegate{if(!busy&&loadedAt.HasValue)status.Text=T("Zmieniono limit. Użyj Odśwież, aby wczytać historię.","Limit changed. Use Refresh to load the history.");};
  Shown+=async delegate{if(autoLoad)await Reload();};FormClosing+=delegate(object sender,FormClosingEventArgs e){if(busy)e.Cancel=true;};
  UiText.LanguageChanged+=RefreshLanguage;FormClosed+=delegate{UiText.LanguageChanged-=RefreshLanguage;tips.Dispose();};RefreshLanguage(null,EventArgs.Empty);UpdateButtons();
 }
 static DataGridView Grid(){
  var grid=new DataGridView {Dock=DockStyle.Fill,ReadOnly=true,AllowUserToAddRows=false,AllowUserToDeleteRows=false,
   RowHeadersVisible=false,MultiSelect=false,SelectionMode=DataGridViewSelectionMode.FullRowSelect,BackgroundColor=Color.White,
   AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill,AutoSizeRowsMode=DataGridViewAutoSizeRowsMode.AllCells,
   ColumnHeadersHeightSizeMode=DataGridViewColumnHeadersHeightSizeMode.AutoSize};
  grid.DefaultCellStyle.WrapMode=DataGridViewTriState.True;grid.DefaultCellStyle.Padding=new Padding(4,7,4,7);
  grid.DefaultCellStyle.SelectionBackColor=Color.FromArgb(255,229,208);grid.DefaultCellStyle.SelectionForeColor=Color.FromArgb(35,47,60);return grid;
 }
 static void Columns(DataGridView grid,string[] captions){
  if(grid.Columns.Count==0)for(int i=0;i<captions.Length;i++){int index=grid.Columns.Add("c"+i,captions[i]);grid.Columns[index].MinimumWidth=70;}
  for(int i=0;i<captions.Length;i++)grid.Columns[i].HeaderText=captions[i];
 }
 static string ValueText(Dictionary<string,object> row,string key){return Rpc.Str(row,key);}
 static long Number(Dictionary<string,object> row,string key){return row.ContainsKey(key)&&row[key]!=null?Convert.ToInt64(row[key]):0;}
 static string Unit(string key){return key=="piece"?T("szt.","piece"):key=="sheet"?T("arkusz","sheet"):key=="offcut"?T("resztka","offcut"):key;}
 static string Scope(string key){return key=="synthetic_test"?T("TEST syntetyczny","SYNTHETIC TEST"):key=="source_input"?T("Dane operatora","Operator input"):key;}
 static string State(string key){switch(key){
  case "usable":return T("Dopuszczony","Usable");case "quarantine":return T("Kwarantanna","Quarantine");case "scrap":return T("Złom","Scrap");
  case "held":return T("Zarezerwowane","Held");case "issued":return T("Wydane","Issued");case "consumed":return T("Zużyte","Consumed");
  case "returned":return T("Zwrócone","Returned");case "cancelled":return T("Anulowane","Cancelled");default:return key;}}
 static string Action(string key){switch(key){
  case "register":return T("Rejestracja partii","Register lot");case "reserve":return T("Rezerwacja","Reserve");case "issue":return T("Wydanie","Issue");
  case "consume":return T("Zużycie","Consume");case "return":return T("Zwrot","Return");case "cancel":return T("Anulowanie","Cancel");
  case "delivery":return T("Potwierdzenie dostawy","Confirm delivery");case "receive":return T("Przyjęcie dostawy","Receive delivery");default:return key;}}
 static string Dimensions(Dictionary<string,object> row){return row["dimensions_mm"]==null?"—":String.Join(" × ",Array.ConvertAll(Rpc.Rows(row["dimensions_mm"]),v=>Convert.ToDouble(v).ToString("0.##",CultureInfo.CurrentCulture)));}
 static string UtcStamp(string raw){DateTimeOffset value;return DateTimeOffset.TryParse(raw,CultureInfo.InvariantCulture,DateTimeStyles.None,out value)?value.UtcDateTime.ToString("yyyy-MM-dd\nHH:mm:ss.fff",CultureInfo.InvariantCulture):raw;}
 async Task Reload(){
  if(System.Threading.Thread.CurrentThread.ManagedThreadId!=uiThread)throw new InvalidOperationException("Inventory UI must start on its owner thread");
  System.Threading.SynchronizationContext.SetSynchronizationContext(new WindowsFormsSynchronizationContext());if(busy)return;
  busy=true;failed=false;UpdateButtons();status.ForeColor=Color.FromArgb(65,80,95);status.Text=T("Odczyt magazynu i historii…","Reading inventory and history…");int limit=(int)historyLimit.Value;
  try{
   var state=await Task.Run(()=>backend("get_inventory",new Dictionary<string,object>()));
   var events=await Task.Run(()=>backend("get_inventory_history",new {limit=limit}));
   // Publish both reads together; a failed second read must not leave a new balance beside old history.
   inventoryData=state;historyData=events;loadedAt=DateTime.Now;loadedLimit=limit;Render();Describe();
  }catch(Exception ex){failed=true;status.ForeColor=Color.Firebrick;status.Text=T("Odczyt nieukończony. ","Read not completed. ")+ex.Message+T("\nWidoczne dane mogą być nieaktualne; odśwież przed decyzją. Nie ponowiono operacji.","\nVisible data may be outdated; refresh before making a decision. No retry was attempted.");}
  finally{busy=false;if(!IsDisposed)UpdateButtons();}
 }
 void UpdateButtons(){if(IsDisposed)return;reload.Enabled=historyLimit.Enabled=!busy;tabs.Enabled=!busy;details.Enabled=!busy&&tabs.SelectedTab==historyTab&&history.SelectedRows.Count==1;}
 void Describe(){if(!loadedAt.HasValue){status.Text=T("Brak odczytu. Użyj Odśwież. To wspólny magazyn wszystkich projektów.","Not loaded. Use Refresh. Inventory is shared by all projects.");return;}
  status.ForeColor=failed?Color.Firebrick:Color.FromArgb(55,75,95);
  status.Text=T("Odczyt: ","Loaded: ")+loadedAt.Value.ToString("G")+T(" • Partii: "," • Lots: ")+lots.Rows.Count+T(" • Rezerwacji: "," • Reservations: ")+reservations.Rows.Count+T(" • Dostaw: "," • Deliveries: ")+deliveries.Rows.Count+T(" • Historia: ostatnie "," • History: latest ")+loadedLimit+T(" wpisów (widoczne "," entries (shown ")+history.Rows.Count+").\n"+
   T("Wolne = fizyczne − aktywne rezerwacje; kwarantanna/złom nie są wolne. Dostawy oczekujące są osobno. Stan może zmienić się po odczycie.","Free = physical − active holds; quarantine/scrap are unavailable. Outstanding deliveries are separate. Balances may change after this read.");
 }
 void Render(){if(inventoryData==null)return;lots.Rows.Clear();reservations.Rows.Clear();deliveries.Rows.Clear();history.Rows.Clear();
  var byLot=new Dictionary<string,Dictionary<string,object>>();
  foreach(var value in Rpc.Rows(inventoryData["lots"])){var row=Rpc.Obj(value);byLot[ValueText(row,"id")]=row;
   int index=lots.Rows.Add(ValueText(row,"id"),ValueText(row,"item_id"),Unit(ValueText(row,"unit")),ValueText(row,"location"),Number(row,"on_hand"),Number(row,"reserved"),Number(row,"free"),Dimensions(row),State(ValueText(row,"condition")),Number(row,"revision"),Scope(ValueText(row,"scope")));
   lots.Rows[index].Cells[6].Style.BackColor=ValueText(row,"condition")!="usable"?Color.FromArgb(242,220,220):Number(row,"free")==0?Color.FromArgb(255,238,207):Color.FromArgb(222,240,227);
   lots.Rows[index].Tag=row;
  }
  foreach(var value in Rpc.Rows(inventoryData["reservations"])){var row=Rpc.Obj(value);Dictionary<string,object> lot;bool known=byLot.TryGetValue(ValueText(row,"lot_id"),out lot);
   int index=reservations.Rows.Add(ValueText(row,"id"),ValueText(row,"lot_id"),known?Unit(ValueText(lot,"unit")):"—",ValueText(row,"plan_id"),Number(row,"quantity"),State(ValueText(row,"status")),Number(row,"returned"),known?Scope(ValueText(lot,"scope")):"—");
   string state=ValueText(row,"status");reservations.Rows[index].Cells[5].Style.BackColor=state=="held"?Color.FromArgb(220,235,249):state=="issued"?Color.FromArgb(255,238,207):state=="consumed"?Color.FromArgb(222,240,227):Color.FromArgb(236,236,236);reservations.Rows[index].Tag=row;
  }
  foreach(var value in Rpc.Rows(inventoryData["deliveries"])){var row=Rpc.Obj(value);int index=deliveries.Rows.Add(ValueText(row,"id"),ValueText(row,"item_id"),Unit(ValueText(row,"unit")),Number(row,"quantity"),Number(row,"received"),Number(row,"outstanding"),ValueText(row,"due_date"),ValueText(row,"confirmation_reference"),Number(row,"revision"),Scope(ValueText(row,"scope")));deliveries.Rows[index].Tag=row;}
  foreach(var value in Rpc.Rows(historyData["events"])){var row=Rpc.Obj(value);var result=Rpc.Obj(row["result"]);var lot=result.ContainsKey("lot")?Rpc.Obj(result["lot"]):new Dictionary<string,object>();var hold=result.ContainsKey("reservation")?Rpc.Obj(result["reservation"]):new Dictionary<string,object>();var delivery=result.ContainsKey("delivery")?Rpc.Obj(result["delivery"]):new Dictionary<string,object>();
   int index=history.Rows.Add(UtcStamp(ValueText(row,"created_at")),ValueText(row,"operation_id"),Action(ValueText(result,"action")),ValueText(lot,"id"),ValueText(hold,"id"),ValueText(delivery,"id"),lot.Count>0?Unit(ValueText(lot,"unit")):Unit(ValueText(delivery,"unit")),lot.Count>0?(object)Number(lot,"on_hand"):"—",lot.Count>0?(object)Number(lot,"reserved"):"—",lot.Count>0?(object)Number(lot,"free"):"—");history.Rows[index].Tag=row;history.Rows[index].Cells[0].ToolTipText=ValueText(row,"created_at");
  }
  foreach(var grid in new[]{lots,reservations,deliveries,history})grid.ClearSelection();UpdateButtons();
 }
 void ShowDetails(){if(history.SelectedRows.Count!=1)return;var row=Rpc.Obj(history.SelectedRows[0].Tag);using(var form=new Form {Text=T("Kwit operacji — stan w chwili operacji","Operation receipt — state at operation time"),Size=new Size(950,650),MinimumSize=new Size(700,450),StartPosition=FormStartPosition.CenterParent,Font=Font}){
  form.Controls.Add(new TextBox {Dock=DockStyle.Fill,Multiline=true,ReadOnly=true,WordWrap=false,ScrollBars=ScrollBars.Both,Text=new JavaScriptSerializer().Serialize(row)});form.ShowDialog(this);
  System.Threading.SynchronizationContext.SetSynchronizationContext(new WindowsFormsSynchronizationContext());}}
 void RefreshLanguage(object sender,EventArgs e){if(IsDisposed)return;Text=T("RockPro | Wspólny magazyn i historia","RockPro | Shared inventory and history");
  heading.Text=T("ROCKPRO • MAGAZYN — PODGLĄD\nWspólny rejestr wszystkich projektów. To okno wyłącznie odczytuje dane; nie rezerwuje, nie wydaje i nie zamawia materiału.\nIlości mają jawne jednostki i źródło. Historia to kwity z chwili operacji, nie bieżący stan.","ROCKPRO • INVENTORY — READ ONLY\nShared across all projects. This window only reads data; it does not reserve, issue or purchase stock.\nQuantities show units and provenance. History contains receipts at operation time, not current balances.");
  reload.Text=T("Odśwież magazyn i historię","Refresh inventory and history");details.Text=T("Pokaż wybrany kwit","Show selected receipt");limitLabel.Text=T("Limit historii:","History limit:");
  lotTab.Text=T("Partie i wolny stan","Lots and availability");reservationTab.Text=T("Rezerwacje i wydania","Reservations and issues");deliveryTab.Text=T("Potwierdzone dostawy","Confirmed deliveries");historyTab.Text=T("Historia — kwity operacji","History — operation receipts");
  Columns(lots,new[]{"ID",T("Materiał / SKU","Item / SKU"),T("Jednostka","Unit"),T("Lokalizacja","Location"),T("Fizycznie","Physical"),T("Rezerwacje","Held"),T("Wolne","Free"),T("L × W × T [mm]","L × W × T [mm]"),T("Stan fizyczny","Condition"),T("Wersja","Revision"),T("Pochodzenie","Provenance")});
  Columns(reservations,new[]{"ID",T("Partia","Lot"),T("Jednostka","Unit"),T("Plan","Plan"),T("Ilość","Quantity"),T("Stan","Status"),T("Zwrócono","Returned"),T("Pochodzenie","Provenance")});
  Columns(deliveries,new[]{"ID",T("Materiał / SKU","Item / SKU"),T("Jednostka","Unit"),T("Zamówiono","Ordered"),T("Przyjęto","Received"),T("Oczekuje","Outstanding"),T("Termin","Due date"),T("Potwierdzenie","Reference"),T("Wersja","Revision"),T("Pochodzenie","Provenance")});
  Columns(history,new[]{T("Czas UTC","UTC time"),T("ID operacji","Operation ID"),T("Operacja","Action"),T("Partia","Lot"),T("Rezerwacja","Reservation"),T("Dostawa","Delivery"),T("Jednostka","Unit"),T("Fizycznie wtedy","Physical then"),T("Rezerwacje wtedy","Held then"),T("Wolne wtedy","Free then")});
  tips.SetToolTip(details,T("Pełny zapisany kwit z hashem polecenia; dane operatora nie są uwierzytelnionym zatwierdzeniem.","Saved receipt with command hash; operator inputs are not authenticated approvals."));
  if(!busy){Render();if(failed){status.ForeColor=Color.Firebrick;status.Text=T("Ostatni odczyt nieukończony. Widoczne dane mogą być nieaktualne. Użyj Odśwież.","Last read did not complete. Visible data may be outdated. Use Refresh.");}else Describe();}
 }
}
}
