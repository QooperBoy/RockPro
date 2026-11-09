using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Globalization;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Runtime.InteropServices;

namespace RockPro.CAD {
[ComVisible(false)]
internal static class LayoutLanguage {
 static readonly Dictionary<string,string[]> entries=new Dictionary<string,string[]>();
 internal static string T(string pl,string en){var pair=new[]{pl,en};entries[pl]=pair;entries[en]=pair;return UiText.T(pl,en);}
 internal static string Translate(string text){string[] pair;return entries.TryGetValue(text,out pair)?UiText.T(pair[0],pair[1]):text;}
 internal static string Warnings(string text){return text.Replace("Bryły uproszczone: uwzględnij wystające złącza, uchwyty i przewody.",T("Bryły uproszczone: uwzględnij wystające złącza, uchwyty i przewody.","Simplified envelopes: include protruding connectors, handles and cables.")).Replace("Wyjmowanie urządzeń, pianki i wytrzymałość wymagają oceny konstruktora.",T("Wyjmowanie urządzeń, pianki i wytrzymałość wymagają oceny konstruktora.","Device removal, foam and strength require an engineer's review.")).Replace("Piętrowanie: zaprojektuj podparcie i dostęp do dolnych urządzeń; przegroda nie jest zweryfikowaną półką.",T("Piętrowanie: zaprojektuj podparcie i dostęp do dolnych urządzeń; przegroda nie jest zweryfikowaną półką.","Stacking: design support and access to lower devices; a divider is not a validated shelf."));}
 internal static string View(string key){return key=="Z góry"?T("Z góry","Top"):key=="Z przodu"?T("Z przodu","Front"):key;}
}

[ComVisible(false)]
internal static class FormScroll {
 internal static void Forward(Control control,int delta){
  for(Control p=control.Parent;p!=null;p=p.Parent){var panel=p as ScrollableControl;
   if(panel!=null && panel.AutoScroll && panel.VerticalScroll.Visible){
    int step=SystemInformation.MouseWheelScrollLines;
    int pixels=step<0?panel.ClientSize.Height:Math.Max(1,step)*22;
    panel.AutoScrollPosition=new Point(0,Math.Max(0,-panel.AutoScrollPosition.Y-delta*pixels/120));return;
   }
  }
 }
}
[ComVisible(false)]
internal sealed class ScrollSafeNumber : NumericUpDown {
 protected override void OnMouseWheel(MouseEventArgs e){var handled=e as HandledMouseEventArgs;if(handled!=null)handled.Handled=true;FormScroll.Forward(this,e.Delta);}
}
[ComVisible(false)]
internal class ScrollSafeChoice : ComboBox {
 protected override void WndProc(ref Message m){if(m.Msg==0x020A){FormScroll.Forward(this,unchecked((short)((m.WParam.ToInt64()>>16)&0xffff)));return;}base.WndProc(ref m);}
}
[ComVisible(false)]
internal sealed class RankedChoiceItem {
 internal string Key,Caption;internal double? Volume;internal double Score;
 public override string ToString(){return Caption+" · "+(Volume.HasValue?Volume.Value.ToString("0.0",CultureInfo.CurrentCulture)+" l"+(Score<.000001?" · min":Score>.999999?" · max":""):LayoutLanguage.T("niedostępny","unavailable"));}
}
[ComVisible(false)]
internal sealed class RankedChoice : ScrollSafeChoice {
 readonly Dictionary<string,string> captions=new Dictionary<string,string>();
 internal RankedChoice(){DrawMode=DrawMode.OwnerDrawFixed;ItemHeight=26;DropDownWidth=440;MaxDropDownItems=8;}
 internal string SelectedKey {get {var item=SelectedItem as RankedChoiceItem;return item!=null?item.Key:SelectedIndex<0?"":((string[])Tag)[SelectedIndex];}}
 internal void Initialize(string[] keys,string[] labels){for(int i=0;i<keys.Length;i++)captions[keys[i]]=labels[i];}
 internal void Relabel(){var keys=new List<string>(captions.Keys);foreach(string key in keys)captions[key]=LayoutLanguage.Translate(captions[key]);foreach(object o in Items){var item=o as RankedChoiceItem;if(item!=null)item.Caption=captions[item.Key];}Invalidate();}
 internal void SelectKey(string key){for(int i=0;i<Items.Count;i++){var item=Items[i] as RankedChoiceItem;string k=item==null?((string[])Tag)[i]:item.Key;if(k==key){SelectedIndex=i;return;}}}
 internal void Rank(object[] rows){string selected=SelectedKey;BeginUpdate();try{Items.Clear();foreach(var o in rows){var r=Rpc.Obj(o);string key=Rpc.Str(r,"key");bool valid=Convert.ToBoolean(r["valid"]);Items.Add(new RankedChoiceItem {Key=key,Caption=captions[key],Volume=valid?(double?)Convert.ToDouble(r["volume_l"]):null,Score=valid?Convert.ToDouble(r["score"]):0});}SelectKey(selected);}finally{EndUpdate();}Invalidate();}
 protected override void OnDrawItem(DrawItemEventArgs e){if(e.Index<0)return;var item=Items[e.Index] as RankedChoiceItem;bool selected=(e.State&DrawItemState.Selected)!=0;Color color=Color.FromArgb(108,120,133);if(item!=null&&item.Volume.HasValue){double s=Math.Max(0,Math.Min(1,item.Score));color=s<.5?Mix(Color.FromArgb(34,139,86),Color.FromArgb(179,126,30),s*2):Mix(Color.FromArgb(179,126,30),Color.FromArgb(193,59,55),(s-.5)*2);}using(var brush=new SolidBrush(Mix(Color.White,color,selected ? .18 : .07)))e.Graphics.FillRectangle(brush,e.Bounds);using(var brush=new SolidBrush(color))e.Graphics.FillEllipse(brush,e.Bounds.X+8,e.Bounds.Y+(e.Bounds.Height-8)/2,8,8);var rect=new Rectangle(e.Bounds.X+23,e.Bounds.Y,e.Bounds.Width-27,e.Bounds.Height);TextRenderer.DrawText(e.Graphics,Items[e.Index].ToString(),Font,rect,Color.FromArgb(40,51,65),TextFormatFlags.VerticalCenter|TextFormatFlags.EndEllipsis|TextFormatFlags.SingleLine);e.DrawFocusRectangle();}
 static Color Mix(Color a,Color b,double f){return Color.FromArgb((int)(a.R+(b.R-a.R)*f),(int)(a.G+(b.G-a.G)*f),(int)(a.B+(b.B-a.B)*f));}
}
[ComVisible(false)]
internal sealed class LayoutForm : Form {
 readonly string projectId;
 readonly Dictionary<string,Control> fields=new Dictionary<string,Control>();
 readonly ToolTip tips=new ToolTip {AutoPopDelay=20000};
 readonly Timer timer=new Timer {Interval=450};
 readonly LayoutCanvas canvas=new LayoutCanvas();
 readonly Label status=new Label(), information=new Label(),volumeSummary=new Label();
 readonly Label[,] metricCells=new Label[2,3];
 readonly TableLayoutPanel metricTable=new TableLayoutPanel();
 readonly Panel savedNotice=new Panel();
 readonly Timer savedNoticeTimer=new Timer {Interval=8000};
 string savedDatabase="";
 string informationText="";
 readonly Button save=new StudioButton(), apply=new StudioButton(),optimal=new StudioButton();
 Dictionary<string,object> bestVariant;
 bool loading=true,dirty=false,working=false,calculating=false,rankingUpdate=false;
 int revision=0;
 public LayoutForm(string id) {
  projectId=id;Text=LayoutLanguage.T("RockPro CAD | Przygotowanie skrzyni — urządzenia i układ","RockPro CAD | Case preparation — devices and layout");Size=new Size(1240,840);MinimumSize=new Size(1020,680);StartPosition=FormStartPosition.CenterParent;Font=new Font("Segoe UI",10);BackColor=Color.FromArgb(238,242,246);AutoScaleMode=AutoScaleMode.Dpi;
  var root=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=2,RowCount=3,Padding=new Padding(18)};
  root.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,365));root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));root.RowStyles.Add(new RowStyle(SizeType.Absolute,108));root.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.RowStyles.Add(new RowStyle(SizeType.Absolute,90));Controls.Add(root);
  var title=new Label {Text=LayoutLanguage.T("01 / Przygotowanie skrzyni\nPodaj wymiary i liczbę urządzeń, wybierz ułożenie oraz miejsce na akcesoria.\nZapisz układ lub utwórz kopię szkieletu CAD. Podgląd nie jest projektem produkcyjnym. Wymiary: mm.","01 / Case preparation\nEnter device dimensions and quantity, then choose their arrangement and space for accessories.\nSave the layout or create a CAD shell copy. This preview is not a production design. Dimensions: mm."),Dock=DockStyle.Fill,Font=new Font("Segoe UI",10,FontStyle.Regular),ForeColor=Color.FromArgb(31,42,55)};root.Controls.Add(title,0,0);root.SetColumnSpan(title,2);
  var scroll=new Panel {Dock=DockStyle.Fill,AutoScroll=true};root.Controls.Add(scroll,0,1);
  var stack=new FlowLayoutPanel {Dock=DockStyle.Top,AutoSize=true,FlowDirection=FlowDirection.TopDown,WrapContents=false,Padding=new Padding(4)};scroll.Controls.Add(stack);
  Section(stack,LayoutLanguage.T("URZĄDZENIE • uproszczona bryła","DEVICE • simplified envelope"));TextField(stack,"name",LayoutLanguage.T("Nazwa urządzenia","Device name"),UiText.T("Urządzenie","Device"));
  Number(stack,"x",LayoutLanguage.T("Wymiar X urządzenia","Device dimension X"),345.4m,1,5000);Number(stack,"y",LayoutLanguage.T("Wymiar Y urządzenia","Device dimension Y"),241.9m,1,5000);Number(stack,"z",LayoutLanguage.T("Wymiar Z urządzenia","Device dimension Z"),88.2m,1,5000);Number(stack,"count",LayoutLanguage.T("Sztuk w jednej skrzyni","Devices per case"),2,1,30);
  Choice(stack,"orientation",LayoutLanguage.T("Orientacja: X / Y / Z skrzyni","Device axes mapped to case X / Y / Z"),new[]{"XYZ","XZY","YXZ","YZX","ZXY","ZYX"},new[]{LayoutLanguage.T("X / Y / Z — standard","X / Y / Z — standard"),LayoutLanguage.T("X / Z / Y — na boku","X / Z / Y — on its side"),LayoutLanguage.T("Y / X / Z — obrót w poziomie","Y / X / Z — horizontal rotation"),"Y / Z / X","Z / X / Y","Z / Y / X"});
  Section(stack,LayoutLanguage.T("ROZMIESZCZENIE","ARRANGEMENT"));Choice(stack,"arrangement",LayoutLanguage.T("Kierunek kolejnych urządzeń","Direction of repeated devices"),new[]{"X","Y","Z"},new[]{LayoutLanguage.T("Obok siebie — oś X","Side by side — X axis"),LayoutLanguage.T("Jeden za drugim — oś Y","Front to back — Y axis"),LayoutLanguage.T("Piętrowo — oś Z","Stacked — Z axis")});
  Style(optimal,LayoutLanguage.T("Zastosuj najmniejszą objętość","Use the smallest volume"),false);optimal.Width=315;optimal.Enabled=false;stack.Controls.Add(optimal);tips.SetToolTip(optimal,LayoutLanguage.T("Porównuje wszystkie 18 kombinacji: 6 orientacji × 3 kierunki. Zmienia jednocześnie orientację i kierunek, zachowując pozostałe ustawienia.","Compares all 18 combinations: 6 orientations × 3 directions. Changes both choices and keeps other settings."));optimal.Click+=delegate{if(bestVariant==null)return;rankingUpdate=true;try{((RankedChoice)fields["orientation"]).SelectKey(Rpc.Str(bestVariant,"orientation"));((RankedChoice)fields["arrangement"]).SelectKey(Rpc.Str(bestVariant,"arrangement"));}finally{rankingUpdate=false;}Changed();};
  Number(stack,"gap",LayoutLanguage.T("Luz między urządzeniami","Gap between devices"),20,0,500);Number(stack,"clearance",LayoutLanguage.T("Rezerwa przy każdej ścianie","Clearance at each wall"),20,0,500);Number(stack,"separator",LayoutLanguage.T("Grubość przegrody (0 = brak)","Divider thickness (0 = none)"),0,0,50);
  Section(stack,LayoutLanguage.T("BOCZNA KOMORA NA AKCESORIA","SIDE COMPARTMENT FOR ACCESSORIES"));Choice(stack,"side",LayoutLanguage.T("Położenie komory","Compartment position"),new[]{"none","X","Y"},new[]{LayoutLanguage.T("Bez komory","No compartment"),LayoutLanguage.T("Z boku — +X","At the side — +X"),LayoutLanguage.T("Z tyłu — +Y","At the back — +Y")});TextField(stack,"side_name",LayoutLanguage.T("Zawartość komory","Compartment contents"),UiText.T("Kable","Cables"));
  Number(stack,"side_width",LayoutLanguage.T("Szerokość zawartości w poprzek komory","Contents width across compartment"),80,1,5000);Number(stack,"side_depth",LayoutLanguage.T("Długość zawartości wzdłuż komory","Contents length along compartment"),300,1,5000);Number(stack,"side_height",LayoutLanguage.T("Wysokość zawartości komory","Contents height"),50,1,5000);
  Section(stack,LayoutLanguage.T("KONSTRUKCJA DO NASTĘPNEGO ETAPU","PLYWOOD SHELL SETTINGS"));Number(stack,"thickness",LayoutLanguage.T("Grubość sklejki","Plywood thickness"),9,1,100);Number(stack,"lid_height",LayoutLanguage.T("Zewnętrzna wysokość pokrywy","External lid height"),50,2,1000);
  var right=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=3,Padding=new Padding(14,0,0,0)};right.RowStyles.Add(new RowStyle(SizeType.Absolute,36));right.RowStyles.Add(new RowStyle(SizeType.Percent,100));right.RowStyles.Add(new RowStyle(SizeType.Absolute,145));root.Controls.Add(right,1,1);
  var toolbar=new Panel {Dock=DockStyle.Fill};var views=new FlowLayoutPanel {Dock=DockStyle.Fill,Padding=new Padding(0,0,42,0)};foreach(string v in new[]{"3D","Z góry","Z przodu"}){string view=v;var b=new Button {Text=LayoutLanguage.View(v),Width=95,Height=30,FlatStyle=FlatStyle.Flat,BackColor=Color.White};b.Click+=delegate{canvas.View=view;canvas.Invalidate();};views.Controls.Add(b);}toolbar.Controls.Add(views);
  information.Text="ⓘ";information.AccessibleName=LayoutLanguage.T("Informacje o podglądzie i ograniczeniach","Preview information and limitations");information.Font=new Font("Segoe UI",16,FontStyle.Regular);information.ForeColor=Color.FromArgb(102,114,130);information.TextAlign=ContentAlignment.MiddleCenter;information.Dock=DockStyle.Right;information.Width=38;information.Cursor=Cursors.Help;information.TabStop=true;information.Click+=delegate{MessageBox.Show(this,informationText,LayoutLanguage.T("Podgląd — legenda i informacje","Preview — legend and information"));};information.KeyDown+=delegate(object sender,KeyEventArgs e){if(e.KeyCode==Keys.Enter||e.KeyCode==Keys.Space)MessageBox.Show(this,informationText,LayoutLanguage.T("Podgląd — legenda i informacje","Preview — legend and information"));};toolbar.Controls.Add(information);right.Controls.Add(toolbar,0,0);canvas.Dock=DockStyle.Fill;right.Controls.Add(canvas,0,1);
  metricTable.Dock=DockStyle.Fill;metricTable.BackColor=Color.White;metricTable.Padding=new Padding(10,6,10,6);metricTable.ColumnCount=4;metricTable.RowCount=4;metricTable.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,43));for(int i=0;i<3;i++)metricTable.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,19));
  foreach(string heading in new[]{LayoutLanguage.T("Wymiary [mm]","Dimensions [mm]"),LayoutLanguage.T("X • długość","X • length"),LayoutLanguage.T("Y • głębokość","Y • depth"),LayoutLanguage.T("Z • wysokość","Z • height")}){int col=metricTable.Controls.Count;var label=MetricLabel(heading,true);metricTable.Controls.Add(label,col,0);}for(int row=0;row<2;row++){metricTable.RowStyles.Add(new RowStyle(SizeType.Percent,25));metricTable.Controls.Add(MetricLabel(row==0?LayoutLanguage.T("Wnętrze skrzyni","Case interior"):LayoutLanguage.T("Konstrukcja z zewnątrz","Shell exterior"),false),0,row+1);for(int col=0;col<3;col++){var label=MetricLabel("—",false);label.TextAlign=ContentAlignment.MiddleRight;metricCells[row,col]=label;metricTable.Controls.Add(label,col+1,row+1);}}metricTable.RowStyles.Add(new RowStyle(SizeType.Percent,25));metricTable.RowStyles.Add(new RowStyle(SizeType.Percent,25));volumeSummary.Dock=DockStyle.Fill;volumeSummary.Font=new Font("Segoe UI",9,FontStyle.Regular);volumeSummary.Padding=new Padding(7,0,0,0);volumeSummary.TextAlign=ContentAlignment.MiddleLeft;metricTable.Controls.Add(volumeSummary,0,3);metricTable.SetColumnSpan(volumeSummary,4);right.Controls.Add(metricTable,0,2);SetInformation("");
  var footer=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=2};footer.RowStyles.Add(new RowStyle(SizeType.Absolute,50));footer.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.Controls.Add(footer,0,2);root.SetColumnSpan(footer,2);
  var buttons=new FlowLayoutPanel {Dock=DockStyle.Fill};Style(save,LayoutLanguage.T("Zapisz układ","Save layout"),false);Style(apply,LayoutLanguage.T("Utwórz szkielet na kopii ICS","Create shell in an ICS copy"),true);tips.SetToolTip(save,LayoutLanguage.T("Zapisuje parametry i nową wersję układu w bazie projektu. Nie zmienia modelu CAD.","Saves settings and a new layout version in the project database. Does not change the CAD model."));tips.SetToolTip(apply,LayoutLanguage.T("Najpierw zapisuje układ, następnie tworzy kopię znanego szkieletu ICS o wyliczonych wymiarach. Nie wstawia urządzeń, przegród ani okuć.","Saves the layout, then creates a copy of the supported ICS shell with the calculated dimensions. Does not insert devices, dividers or hardware."));buttons.Controls.Add(save);buttons.Controls.Add(apply);footer.Controls.Add(buttons,0,0);status.Dock=DockStyle.Fill;status.Font=new Font("Segoe UI",9,FontStyle.Regular);status.ForeColor=Color.FromArgb(102,114,130);status.Text=LayoutLanguage.T("Wczytywanie układu…","Loading layout…");footer.Controls.Add(status,0,1);
  foreach(var field in fields.Values)field.Enabled=false; save.Enabled=apply.Enabled=false;
  save.Click+=async delegate{await Persist(false);};apply.Click+=async delegate{await Persist(true);};
  timer.Tick+=async delegate{timer.Stop();await Preview();};Shown+=async delegate{await LoadLayout();};
  FormClosing+=delegate(object sender,FormClosingEventArgs e){if(working){e.Cancel=true;return;}if(dirty && MessageBox.Show(this,LayoutLanguage.T("Zamknąć bez zapisania zmian układu?","Close without saving layout changes?"),LayoutLanguage.T("Niezapisany układ","Unsaved layout"),MessageBoxButtons.YesNo)!=DialogResult.Yes)e.Cancel=true;};
  UiText.LanguageChanged+=RefreshLanguage;
  FormClosed+=delegate{UiText.LanguageChanged-=RefreshLanguage;timer.Stop();timer.Dispose();savedNoticeTimer.Dispose();tips.Dispose();};
 }
 void Style(Button b,string text,bool primary){b.Text=text;b.Width=primary?290:180;b.Height=40;b.BackColor=primary?Color.FromArgb(237,102,21):Color.White;b.ForeColor=primary?Color.White:Color.FromArgb(31,42,55);b.FlatAppearance.MouseOverBackColor=Color.FromArgb(255,180,100);}
 void Section(FlowLayoutPanel p,string s){p.Controls.Add(new Label {Text=s,Width=325,Height=36,Padding=new Padding(0,12,0,0),Font=new Font("Segoe UI",9,FontStyle.Bold),ForeColor=Color.FromArgb(153,71,18)});}
 void Add(FlowLayoutPanel p,string key,string label,Control c){p.Controls.Add(new Label {Text=label,Width=325,Height=23,AutoEllipsis=true});c.Width=315;c.Margin=new Padding(0,0,0,9);p.Controls.Add(c);fields[key]=c;tips.SetToolTip(c,FieldHelp(key));}
 string FieldHelp(string key){switch(key){
case "x":case "y":case "z":return LayoutLanguage.T("Wymiar urządzenia przed obrotem, w mm. Uwzględnij wystające złącza i uchwyty.","Device dimension before rotation, in mm. Include protruding connectors and handles.");
case "count":return LayoutLanguage.T("Liczba identycznych urządzeń w jednej skrzyni, nie liczba zamawianych skrzyń.","Number of identical devices in one case, not the number of cases ordered.");
case "orientation":return LayoutLanguage.T("Kolejność mapuje wymiary urządzenia na X, Y i Z skrzyni. Kolor porównuje objętość, nie bezpieczeństwo.","The order maps device dimensions to case X, Y and Z. Colour compares volume, not safety.");
case "arrangement":return LayoutLanguage.T("Oś kolejnych urządzeń. Piętrowanie wymaga sprawdzenia podparcia i wyjmowania.","Axis along which devices repeat. Stacking requires a support and removal check.");
case "gap":return LayoutLanguage.T("Wolna odległość między urządzeniami w mm. Grubość przegrody jest doliczana osobno.","Free distance between devices in mm. Divider thickness is added separately.");
case "clearance":return LayoutLanguage.T("Wolne miejsce przy każdej ścianie w mm. To rezerwa wymiarowa, nie wygenerowana pianka.","Free space at each wall in mm. Dimensional clearance, not generated foam.");
case "separator":return LayoutLanguage.T("Grubość przegród w podglądzie w mm. Wartość 0 usuwa przegrody. Nie są jeszcze wstawiane do ICS.","Preview divider thickness in mm. Set 0 to remove dividers. They are not yet inserted into ICS.");
case "thickness":return LayoutLanguage.T("Stała grubość wszystkich płyt szkieletu w mm. Zmienia gabaryt zewnętrzny, nie wymiary urządzeń.","Uniform shell panel thickness in mm. Changes exterior dimensions, not device dimensions.");
case "lid_height":return LayoutLanguage.T("Zewnętrzna wysokość pokrywy w mm. Dzieli wysokość konstrukcji między pokrywę i dół.","External lid height in mm. Splits shell height between lid and base.");
case "side":return LayoutLanguage.T("Jedna komora obok urządzeń. Przy opcji Bez komory dalsze pola tej sekcji nie wpływają na wynik.","One compartment beside the devices. With No compartment selected, other fields in this section do not affect the result.");
case "side_width":case "side_depth":case "side_height":return LayoutLanguage.T("Obrys wszystkich akcesoriów w komorze w mm. Rezerwa doliczana jest osobno.","Envelope of all accessories in the compartment in mm. Clearance is added separately.");
default:return LayoutLanguage.T("Nazwa pomocnicza zapisywana z układem. Wpisz własny opis.","A descriptive name saved with the layout. Enter your own wording.");}}
 void Number(FlowLayoutPanel p,string k,string l,decimal v,decimal min,decimal max){var c=new ScrollSafeNumber {Minimum=min,Maximum=max,DecimalPlaces=k=="count"?0:2,Value=v};Add(p,k,l,c);c.ValueChanged+=delegate{Changed();};}
 void TextField(FlowLayoutPanel p,string k,string l,string v){var c=new TextBox {Text=v,MaxLength=100};Add(p,k,l,c);c.TextChanged+=delegate{Changed();};}
 void Choice(FlowLayoutPanel p,string k,string l,string[] values,string[] labels){ScrollSafeChoice c=(k=="orientation"||k=="arrangement")?(ScrollSafeChoice)new RankedChoice():new ScrollSafeChoice();c.DropDownStyle=ComboBoxStyle.DropDownList;c.Tag=values;var ranked=c as RankedChoice;if(ranked!=null)ranked.Initialize(values,labels);c.Items.AddRange(labels);c.SelectedIndex=0;Add(p,k,l,c);c.SelectedIndexChanged+=delegate{Changed();};}
 void Changed(){if(loading||rankingUpdate)return;savedNotice.Visible=false;savedNoticeTimer.Stop();status.ForeColor=Color.FromArgb(102,114,130);optimal.Enabled=false;volumeSummary.Text=LayoutLanguage.T("Przeliczanie rankingu…","Comparing layout options…");dirty=true;revision++;apply.Enabled=false;canvas.Result=null;canvas.Invalidate();for(int r=0;r<2;r++)for(int c=0;c<3;c++)metricCells[r,c].Text="—";status.Text=LayoutLanguage.T("Przeliczanie układu…","Calculating layout…");timer.Stop();timer.Start();}
 Dictionary<string,object> Spec(){var s=new Dictionary<string,object>();foreach(var pair in fields){var n=pair.Value as NumericUpDown;var c=pair.Value as ComboBox;s[pair.Key]=n!=null?(object)(pair.Key=="count"?(object)(int)n.Value:(double)n.Value):c is RankedChoice?(object)((RankedChoice)c).SelectedKey:c!=null?(object)((string[])c.Tag)[c.SelectedIndex]:pair.Value.Text;}return s;}
 long layoutRevision=0;
 async Task LoadLayout(){try{var r=await Task.Run(()=>Rpc.Call("get_layout",new {project_id=projectId}));if(IsDisposed)return;layoutRevision=Convert.ToInt64(r["revision"]);Text=LayoutLanguage.T("RockPro CAD | Układ urządzeń — wersja ","RockPro CAD | Device layout — version ")+layoutRevision;var spec=Rpc.Obj(r["spec"]);foreach(var pair in fields){if(!spec.ContainsKey(pair.Key))continue;var n=pair.Value as NumericUpDown;var c=pair.Value as ComboBox;if(n!=null)n.Value=Convert.ToDecimal(spec[pair.Key]);else if(c is RankedChoice)((RankedChoice)c).SelectKey(Convert.ToString(spec[pair.Key]));else if(c!=null)c.SelectedIndex=Array.IndexOf((string[])c.Tag,Convert.ToString(spec[pair.Key]));else pair.Value.Text=Convert.ToString(spec[pair.Key]);}Render(r);dirty=false;}catch(Exception ex){status.Text=ex.Message;apply.Enabled=false;}finally{loading=false;if(!IsDisposed){foreach(var c in fields.Values)c.Enabled=true;save.Enabled=true;}}}
 async Task Preview(){if(calculating||working){timer.Start();return;}calculating=true;int token=revision;var spec=Spec();try{var r=await Task.Run(()=>Rpc.Call("preview_layout",new {spec=spec}));if(!IsDisposed&&token==revision)Render(r);}catch(Exception ex){if(!IsDisposed&&token==revision){status.Text=LayoutLanguage.T("Nieprawidłowy układ: ","Invalid layout: ")+ex.Message;apply.Enabled=false;canvas.Result=null;canvas.Invalidate();}}finally{calculating=false;}}
 Label MetricLabel(string text,bool header){return new Label {Text=text,Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleLeft,AutoEllipsis=true,Font=new Font("Segoe UI",9,FontStyle.Regular),ForeColor=header?Color.FromArgb(120,132,145):Color.FromArgb(45,58,72),BackColor=header?Color.FromArgb(247,249,252):Color.White,Margin=new Padding(0),Padding=new Padding(7,0,7,0)};}
 void SetInformation(string warnings){informationText=LayoutLanguage.T("LEGENDA\nNiebieski: urządzenia. Pomarańczowy: akcesoria. Szary: przegrody.\nLinia przerywana: obrys konstrukcji.\n\nWYMIARY\nWnętrze to przestrzeń między płytami. Wymiar zewnętrzny konstrukcji to wnętrze + dwie grubości płyt; bez okuć i kół.\n\nPodgląd używa prostopadłościennych obrysów. Konstruktor musi sprawdzić wyjmowanie, podparcie, pianki i wytrzymałość.","LEGEND\nBlue: devices. Orange: accessories. Grey: dividers.\nDashed line: shell envelope.\n\nDIMENSIONS\nThe interior is the space between panels. The shell exterior equals the interior + two panel thicknesses; excluding hardware and wheels.\n\nThis preview uses box envelopes. An engineer must check removal, support, foam and strength.");informationText+="\n\n"+LayoutLanguage.Warnings(warnings);tips.SetToolTip(information,informationText);information.AccessibleDescription=informationText;}
 void RefreshLanguage(object sender,EventArgs e){if(IsDisposed)return;bool wasLoading=loading;loading=true;try{Relabel(this);Text=LayoutLanguage.T("RockPro CAD | Układ urządzeń — wersja ","RockPro CAD | Device layout — version ")+layoutRevision;foreach(var field in fields.Values){var ranked=field as RankedChoice;if(ranked!=null)ranked.Relabel();}if(canvas.Result!=null)Render(canvas.Result);else SetInformation("");canvas.Invalidate();}finally{loading=wasLoading;}}
 void Relabel(Control parent){foreach(Control c in parent.Controls){if(!(c is TextBox)&&!(c is NumericUpDown)&&!(c is ComboBox))c.Text=LayoutLanguage.Translate(c.Text);if(!String.IsNullOrEmpty(c.AccessibleName))c.AccessibleName=LayoutLanguage.Translate(c.AccessibleName);string tip=tips.GetToolTip(c);if(tip.Length>0)tips.SetToolTip(c,LayoutLanguage.Translate(tip));var choice=c as ComboBox;if(choice!=null&&!(choice is RankedChoice)){int index=choice.SelectedIndex;for(int i=0;i<choice.Items.Count;i++)choice.Items[i]=LayoutLanguage.Translate(Convert.ToString(choice.Items[i]));choice.SelectedIndex=index;}Relabel(c);}}
 void Render(Dictionary<string,object> r){UpdateRanking(r);canvas.Result=r;canvas.Invalidate();var inner=Rpc.Rows(r["internal"]);var outer=Rpc.Rows(r["external"]);for(int c=0;c<3;c++){metricCells[0,c].Text=Convert.ToDouble(inner[c]).ToString("0.##",CultureInfo.CurrentCulture);metricCells[1,c].Text=Convert.ToDouble(outer[c]).ToString("0.##",CultureInfo.CurrentCulture);}SetInformation(String.Join("\n",Array.ConvertAll(Rpc.Rows(r["warnings"]),x=>Convert.ToString(x))));status.Text=LayoutLanguage.T("Uproszczone obrysy mieszczą się bez przenikania. Ograniczenia: ⓘ.","Simplified envelopes fit without overlap. See ⓘ for limitations.");apply.Enabled=!working;}
 void UpdateRanking(Dictionary<string,object> r){
  var rank=Rpc.Obj(r["ranking"]);bestVariant=Rpc.Obj(rank["best"]);rankingUpdate=true;try{((RankedChoice)fields["orientation"]).Rank(Rpc.Rows(rank["orientations"]));((RankedChoice)fields["arrangement"]).Rank(Rpc.Rows(rank["arrangements"]));}finally{rankingUpdate=false;}
  double current=Convert.ToDouble(r["volume_l"]),best=Convert.ToDouble(bestVariant["volume_l"]),delta=(current/best-1)*100;bool isBest=delta<.000001;
  volumeSummary.Text=LayoutLanguage.T("Objętość: ","Volume: ")+current.ToString("0.0")+LayoutLanguage.T(" l   •   minimum: "," L   •   minimum: ")+best.ToString("0.0")+" l"+(isBest?LayoutLanguage.T("   •   minimum osiągnięte","   •   minimum reached"):"   •   +"+delta.ToString("0.0")+"%");volumeSummary.ForeColor=isBest?Color.FromArgb(34,139,86):Color.FromArgb(153,94,35);optimal.Enabled=!working;
  tips.SetToolTip(volumeSummary,LayoutLanguage.T("Objętość zewnętrzna = X × Y × Z / 1 000 000 litrów. Minimum spośród 18 kombinacji przy tych samych luzach, przegrodach i komorze. Ranking listy orientacji zachowuje bieżący kierunek; ranking kierunków zachowuje bieżącą orientację. Zielony: najmniejsza, czerwony: największa objętość w danej liście. Remisy mają ten sam kolor. Brak oceny wytrzymałości lub sposobu wyjmowania.","External volume = X × Y × Z / 1,000,000 litres. Minimum of 18 combinations with the same gaps, dividers and compartment. Each list keeps the other choice fixed. Green: smallest volume; red: largest in that list. Ties share a colour. Strength and removal are not assessed."));
 }
 string Dims(object o){return String.Join(" × ",Array.ConvertAll(Rpc.Rows(o),x=>Convert.ToDouble(x).ToString("0.##",CultureInfo.CurrentCulture)));}
 void ShowSavedNotice(string database){
  savedDatabase=database;
  if(savedNotice.Parent==null){
   savedNotice.BackColor=Color.FromArgb(232,247,237);savedNotice.BorderStyle=BorderStyle.FixedSingle;
   savedNotice.Size=new Size(530,166);savedNotice.Visible=false;Controls.Add(savedNotice);
   savedNoticeTimer.Tick+=delegate{savedNoticeTimer.Stop();savedNotice.Visible=false;};
   Resize+=delegate{PositionSavedNotice();};
  }
  savedNotice.Controls.Clear();
  var heading=new Label {Text=UiText.T("✓ Zapisano układ — wersja ","✓ Layout saved — version ")+layoutRevision,
   Left=14,Top=10,Width=470,Height=26,Font=new Font("Segoe UI",10,FontStyle.Bold),ForeColor=Color.FromArgb(25,111,65)};
  var location=new TextBox {Text=database,ReadOnly=true,Multiline=true,Left=14,Top=42,Width=498,Height=45,
   BorderStyle=BorderStyle.None,BackColor=savedNotice.BackColor,Font=new Font("Segoe UI",9)};
  var explanation=new Label {Text=UiText.T("Lokalna baza projektu. Model CAD pozostaje bez zmian.","Local project database. The CAD model is unchanged."),Left=14,Top=91,Width=498,Height=25,Font=new Font("Segoe UI",9)};
  var copy=new StudioButton {Text=UiText.T("Kopiuj ścieżkę","Copy path"),Left=14,Top=120,Width=155,Height=32,BackColor=Color.White};
  copy.Click+=delegate{try{Clipboard.SetText(savedDatabase);}catch(Exception ex){MessageBox.Show(this,ex.Message,UiText.T("Schowek","Clipboard"));}};
  var close=new StudioButton {Text=UiText.T("Zamknij","Dismiss"),Left=405,Top=120,Width=107,Height=32,BackColor=Color.White};
  close.Click+=delegate{savedNoticeTimer.Stop();savedNotice.Visible=false;};
  savedNotice.Controls.AddRange(new Control[]{heading,location,explanation,copy,close});
  tips.SetToolTip(location,database);PositionSavedNotice();savedNotice.Visible=true;savedNotice.BringToFront();
  savedNoticeTimer.Stop();savedNoticeTimer.Start();
 }
 void PositionSavedNotice(){savedNotice.Location=new Point(Math.Max(10,ClientSize.Width-savedNotice.Width-22),Math.Max(10,ClientSize.Height-savedNotice.Height-96));}
 async Task Persist(bool cad){if(working||loading)return;working=true;timer.Stop();savedNotice.Visible=false;savedNoticeTimer.Stop();status.ForeColor=Color.FromArgb(102,114,130);save.Enabled=apply.Enabled=false;foreach(var c in fields.Values)c.Enabled=false;optimal.Enabled=false;var spec=Spec();try{status.Text=LayoutLanguage.T("Zapis układu do wspólnej bazy…","Saving layout to the shared database…");var r=await Task.Run(()=>Rpc.Call("save_layout",new {project_id=projectId,spec=spec,expected_revision=layoutRevision}));layoutRevision=Convert.ToInt64(r["revision"]);Text=LayoutLanguage.T("RockPro CAD | Układ urządzeń — wersja ","RockPro CAD | Device layout — version ")+layoutRevision;dirty=false;Render(r);savedDatabase=Rpc.Str(r,"database");if(cad){status.Text=LayoutLanguage.T("Tworzenie kopii szkieletu i kontrola geometrii w IronCAD…","Creating a shell copy and checking geometry in IronCAD…");var parameters=Rpc.Obj(r["parameters"]);var result=await Task.Run(()=>Rpc.Call("change_dimensions_on_copy",new {project_id=projectId,changes=parameters,label="Szkielet z układu urządzeń",layout_revision=layoutRevision}));MessageBox.Show(this,LayoutLanguage.T("Szkielet zapisany na kopii:\n","Shell saved in a copy:\n")+Rpc.Str(result,"copy")+LayoutLanguage.T("\n\nDo CAD przekazano gabaryty konstrukcji. Bryły urządzeń, przegrody i komora są zapisane w układzie i widoczne w podglądzie; ich wstawianie do ICS będzie kolejnym etapem.","\n\nShell dimensions were sent to CAD. Device envelopes, dividers and the compartment are saved in the layout and shown in the preview; inserting them into ICS is not implemented yet."),LayoutLanguage.T("Szkielet z układu","Shell from layout"));}status.ForeColor=Color.FromArgb(25,111,65);if(!cad)ShowSavedNotice(savedDatabase);status.Text=LayoutLanguage.T("Układ zapisany w SQLite. ","Layout saved in the database. ")+(cad?LayoutLanguage.T("Kopia ICS utworzona i sprawdzona.","ICS copy created and checked."):LayoutLanguage.T("Możesz wrócić do niego po ponownym otwarciu dodatku.","You can reopen this layout later."));}catch(Exception ex){savedNotice.Visible=false;status.ForeColor=Color.FromArgb(174,44,44);status.Text=LayoutLanguage.T("Operacja nieukończona: ","Operation not completed: ")+ex.Message;MessageBox.Show(this,ex.Message+(ex.Message.Contains("LAYOUT_CONFLICT")?LayoutLanguage.T("\n\nTwoje pola pozostają w formularzu. Skopiuj potrzebne wartości, zamknij i otwórz konfigurator, aby wczytać aktualną wersję. Nie ponawiamy zapisu automatycznie.","\n\nYour entries remain in the form. Copy values you need, then close and reopen the configurator to load the current version. Saving is not retried automatically."):""),LayoutLanguage.T("RockPro — wynik operacji","RockPro — operation result"));}finally{working=false;save.Enabled=true;apply.Enabled=canvas.Result!=null;optimal.Enabled=canvas.Result!=null&&bestVariant!=null;foreach(var c in fields.Values)c.Enabled=true;}}
}

[ComVisible(false)]
internal sealed class LayoutCanvas : Control {
 public Dictionary<string,object> Result;
 public string View="3D";
 public LayoutCanvas(){DoubleBuffered=true;BackColor=Color.FromArgb(249,251,253);ResizeRedraw=true;}
 static double[] Vec(object o){return Array.ConvertAll(Rpc.Rows(o),x=>Convert.ToDouble(x));}
 PointF Raw(double x,double y,double z){if(View=="Z góry")return new PointF((float)x,(float)-y);if(View=="Z przodu")return new PointF((float)x,(float)-z);return new PointF((float)((x-y)*.866),(float)((x+y)*.38-z));}
 protected override void OnPaint(PaintEventArgs e){base.OnPaint(e);var g=e.Graphics;g.SmoothingMode=SmoothingMode.AntiAlias;if(Result==null){g.DrawString(LayoutLanguage.T("Podgląd zostanie pokazany po przeliczeniu układu","The preview appears after the layout is calculated"),Font,Brushes.Gray,20,30);return;}
  var ext=Vec(Result["external"]);var inside=Vec(Result["internal"]);double t=Convert.ToDouble(Rpc.Obj(Result["spec"])["thickness"]);
  var pts=new List<PointF>();foreach(double x in new[]{0.0,ext[0]})foreach(double y in new[]{0.0,ext[1]})foreach(double z in new[]{0.0,ext[2]})pts.Add(Raw(x,y,z));
  float minx=float.MaxValue,maxx=float.MinValue,miny=float.MaxValue,maxy=float.MinValue;foreach(var p in pts){minx=Math.Min(minx,p.X);maxx=Math.Max(maxx,p.X);miny=Math.Min(miny,p.Y);maxy=Math.Max(maxy,p.Y);}
  float scale=Math.Min((Width-95)/Math.Max(1,maxx-minx),(Height-100)/Math.Max(1,maxy-miny));
  Func<double,double,double,PointF> project=(x,y,z)=>{var q=Raw(x,y,z);return new PointF((q.X-(minx+maxx)/2)*scale+Width/2,(q.Y-(miny+maxy)/2)*scale+Height/2);};
  // Per-pixel depth resolves intersecting projections of long partition faces.
  // Camera ray is parallel to (1, 1, .76), the null space of Raw().
  using(var raster=new DepthRaster(Width,Height)){
   foreach(var obj in Rpc.Rows(Result["boxes"])){var b=Rpc.Obj(obj);var p=Vec(b["pos"]);var d=Vec(b["size"]);string kind=Rpc.Str(b,"kind");Color color=kind=="device"?Color.FromArgb(64,143,180):kind=="accessory"?Color.FromArgb(239,143,65):Color.FromArgb(158,166,179);
    var points=new PointF[8];var depth=new double[8];for(int i=0;i<8;i++){double x=p[0]+t+((i&1)!=0?d[0]:0),y=p[1]+t+((i&2)!=0?d[1]:0),z=p[2]+t+((i&4)!=0?d[2]:0);points[i]=project(x,y,z);depth[i]=View=="Z góry"?z:View=="Z przodu"?-y:x+y+.76*z;}
    int[][] fs=View=="Z góry"?new[]{new[]{4,5,7,6}}:View=="Z przodu"?new[]{new[]{0,1,5,4}}:new[]{new[]{1,3,7,5},new[]{2,3,7,6},new[]{4,5,7,6}};
    for(int f=0;f<fs.Length;f++){var face=fs[f];var shade=Color.FromArgb(Math.Min(255,color.R+f*15),Math.Min(255,color.G+f*15),Math.Min(255,color.B+f*15));raster.Quad(points,depth,face,shade);}
   }
   raster.Draw(g);
  }
  using(var pen=new Pen(Color.FromArgb(115,100,111,122),1.1f)){pen.DashStyle=DashStyle.Dash;for(int i=0;i<8;i++)foreach(int axis in new[]{1,2,4})if((i&axis)==0){int j=i|axis;g.DrawLine(pen,project((i&1)!=0?ext[0]:0,(i&2)!=0?ext[1]:0,(i&4)!=0?ext[2]:0),project((j&1)!=0?ext[0]:0,(j&2)!=0?ext[1]:0,(j&4)!=0?ext[2]:0));}}
  using(var captionFont=new Font("Segoe UI",9,FontStyle.Regular))g.DrawString(LayoutLanguage.T("OBRYS SKRZYNI • ","CASE ENVELOPE • ")+LayoutLanguage.View(View)+" • mm",captionFont,Brushes.DimGray,14,12);

 }
}
}

namespace RockPro.CAD {
// Opaque envelope renderer with an interpolated depth buffer. No geometry changes.
[ComVisible(false)]
internal sealed class DepthRaster : IDisposable {
 readonly int width,height;
 readonly int[] pixels;
 readonly double[] depths;
 readonly List<Tuple<PointF,PointF,double,double>> edges=new List<Tuple<PointF,PointF,double,double>>();
 public DepthRaster(int w,int h){width=w;height=h;pixels=new int[w*h];depths=new double[w*h];for(int i=0;i<depths.Length;i++)depths[i]=double.NegativeInfinity;}
 public int Pixel(int x,int y){return pixels[y*width+x];}
 public void Quad(PointF[] p,double[] z,int[] f,Color c){Triangle(p[f[0]],p[f[1]],p[f[2]],z[f[0]],z[f[1]],z[f[2]],c.ToArgb());Triangle(p[f[0]],p[f[2]],p[f[3]],z[f[0]],z[f[2]],z[f[3]],c.ToArgb());for(int i=0;i<4;i++){int a=f[i],b=f[(i+1)%4];edges.Add(Tuple.Create(p[a],p[b],z[a],z[b]));}}
 void Triangle(PointF a,PointF b,PointF c,double za,double zb,double zc,int color){
  double area=(b.Y-c.Y)*(a.X-c.X)+(c.X-b.X)*(a.Y-c.Y);if(Math.Abs(area)<1e-8)return;
  int x0=Math.Max(0,(int)Math.Floor(Math.Min(a.X,Math.Min(b.X,c.X)))),x1=Math.Min(width-1,(int)Math.Ceiling(Math.Max(a.X,Math.Max(b.X,c.X))));
  int y0=Math.Max(0,(int)Math.Floor(Math.Min(a.Y,Math.Min(b.Y,c.Y)))),y1=Math.Min(height-1,(int)Math.Ceiling(Math.Max(a.Y,Math.Max(b.Y,c.Y))));
  for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++){double px=x+.5,py=y+.5;double u=((b.Y-c.Y)*(px-c.X)+(c.X-b.X)*(py-c.Y))/area,v=((c.Y-a.Y)*(px-c.X)+(a.X-c.X)*(py-c.Y))/area,w=1-u-v;if(u< -1e-6||v< -1e-6||w< -1e-6)continue;double d=u*za+v*zb+w*zc;int k=y*width+x;if(d>depths[k]){depths[k]=d;pixels[k]=color;}}
 }
 public void Draw(Graphics g){
  // Test edge fragments against the same depth buffer, so hidden edges stay hidden.
  foreach(var edge in edges){double dx=edge.Item2.X-edge.Item1.X,dy=edge.Item2.Y-edge.Item1.Y;int n=Math.Max(1,(int)Math.Ceiling(Math.Max(Math.Abs(dx),Math.Abs(dy))*2));for(int i=0;i<=n;i++){double f=(double)i/n;int x=(int)Math.Floor(edge.Item1.X+dx*f),y=(int)Math.Floor(edge.Item1.Y+dy*f);if(x<0||y<0||x>=width||y>=height)continue;int k=y*width+x;double d=edge.Item3+(edge.Item4-edge.Item3)*f;if(d>=depths[k]-1.5){pixels[k]=Color.FromArgb(80,98,114).ToArgb();}}}
  using(var bitmap=new Bitmap(width,height,System.Drawing.Imaging.PixelFormat.Format32bppArgb)){var data=bitmap.LockBits(new Rectangle(0,0,width,height),System.Drawing.Imaging.ImageLockMode.WriteOnly,System.Drawing.Imaging.PixelFormat.Format32bppArgb);try{for(int y=0;y<height;y++)Marshal.Copy(pixels,y*width,IntPtr.Add(data.Scan0,y*data.Stride),width);}finally{bitmap.UnlockBits(data);}g.DrawImageUnscaled(bitmap,0,0);}
 }
 public void Dispose(){}
}
}
