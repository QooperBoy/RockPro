using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace RockPro.CAD {
[System.Runtime.InteropServices.ComVisible(false)]
internal sealed class DeviceVariantsForm : Form {
 sealed class DeviceItem {
  internal Dictionary<string,object> Data;
  public override string ToString(){var name=Rpc.Obj(Data["identity"]);return Rpc.Str(name,"manufacturer")+" "+Rpc.Str(name,"model")+" / "+Rpc.Str(name,"variant");}
 }
 readonly string projectId;
 readonly Func<string,object,Dictionary<string,object>> backend;
 readonly int uiThread=System.Threading.Thread.CurrentThread.ManagedThreadId;
 readonly ComboBox devices=new ScrollSafeChoice {DropDownStyle=ComboBoxStyle.DropDownList};
 readonly CheckedListBox orientations=new CheckedListBox {CheckOnClick=true},arrangements=new CheckedListBox {CheckOnClick=true};
 readonly Dictionary<string,NumericUpDown> inputs=new Dictionary<string,NumericUpDown>();
 readonly CheckBox lidOverride=new CheckBox(),limitEnvelope=new CheckBox();
 readonly Label source=new Label(),status=new Label(),heading=new Label();
 readonly Button reload=new Button(),next=new Button(),sources=new Button(),calculate=new Button(),accept=new Button();
 readonly DataGridView variants=new DataGridView();
 readonly LayoutCanvas canvas=new LayoutCanvas();
 readonly ToolTip tips=new ToolTip();
 readonly List<Label> captions=new List<Label>();
 Dictionary<string,object> baseSpec=new Dictionary<string,object>();
 readonly List<Dictionary<string,object>> proposals=new List<Dictionary<string,object>>();
 string nextCursor;
 bool busy,loading,showing;
 internal Dictionary<string,object> SelectedSpec,SelectedBinding;
 internal long BaseLayoutRevision;
 static string T(string pl,string en){return LayoutLanguage.T(pl,en);}
 internal DeviceVariantsForm(string id):this(id,Rpc.Call,true){}
 internal DeviceVariantsForm(string id,Func<string,object,Dictionary<string,object>> call,bool autoLoad){
  projectId=id;backend=call;Text=T("RockPro CAD | Warianty z katalogu urządzeń","RockPro CAD | Catalog layout proposals");
  Size=new Size(1240,870);MinimumSize=new Size(1000,710);StartPosition=FormStartPosition.CenterParent;AutoScaleMode=AutoScaleMode.Dpi;
  Font=new Font("Segoe UI",10);BackColor=Color.FromArgb(242,246,249);Padding=new Padding(18);
  var root=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=2,RowCount=3};root.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,340));root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
  root.RowStyles.Add(new RowStyle(SizeType.Absolute,95));root.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.RowStyles.Add(new RowStyle(SizeType.Absolute,105));Controls.Add(root);
  heading.Text=T("ROCKPRO • WARIANTY UKŁADU\nWymiary z konkretnego rekordu urządzenia → do 3 propozycji → świadomy wybór i edycja. Nic nie zapisuje się automatycznie.\nObrysy bez okuć/kół. Kontrola +Z zakłada otwartą lub zdjętą pokrywę; nie jest odbiorem wytrzymałości ani produkcji.","ROCKPRO • LAYOUT PROPOSALS\nDimensions from a specific device record → up to 3 proposals → explicit selection and editing. Nothing is saved automatically.\nEnvelopes exclude fittings/wheels. +Z checks assume an open/removable lid; no structural or production approval.");
  heading.Dock=DockStyle.Fill;heading.Padding=new Padding(10);heading.BackColor=Color.FromArgb(255,235,214);root.Controls.Add(heading,0,0);root.SetColumnSpan(heading,2);
  var scroll=new Panel {Dock=DockStyle.Fill,AutoScroll=true};root.Controls.Add(scroll,0,1);
  var settings=new FlowLayoutPanel {Dock=DockStyle.Top,AutoSize=true,WrapContents=false,FlowDirection=FlowDirection.TopDown,Padding=new Padding(3,8,12,8)};scroll.Controls.Add(settings);
  Add(settings,T("Urządzenie i wariant","Device and variant"),devices);devices.DropDownWidth=700;
  source.Size=new Size(305,105);settings.Controls.Add(source);
  Style(reload,T("Wczytaj aktualne dane","Reload current data"));Style(next,T("Kolejna strona katalogu","Next catalog page"));Style(sources,T("Pokaż źródła wymiarów","Show dimension sources"));settings.Controls.Add(reload);settings.Controls.Add(next);settings.Controls.Add(sources);
  AddNumber(settings,"count",T("Urządzeń w jednej skrzyni","Devices per case"),1,1,30,0);
  AddNumber(settings,"gap",T("Odstęp między urządzeniami [mm]","Device gap [mm]"),20,0,500,2);
  AddNumber(settings,"clearance",T("Luz przy ściankach [mm]","Wall clearance [mm]"),20,0,500,2);
  AddNumber(settings,"separator",T("Grubość przegród [mm]","Divider thickness [mm]"),0,0,50,2);
  AddNumber(settings,"lid_height",T("Wysokość pokrywy [mm]","Lid height [mm]"),25,2,1000,2);
  AddNumber(settings,"lid_hinge_height",T("Minimum montażu zawiasu [mm]","Hinge mounting minimum [mm]"),0,0,1000,2);
  lidOverride.Text=T("Jawne odstępstwo proporcji pokrywy","Explicit lid proportion override");lidOverride.Size=new Size(305,45);settings.Controls.Add(lidOverride);
  AddNumber(settings,"removal",T("Dodatkowy luz chwytu XY [mm]","Additional XY hand clearance [mm]"),10,0,500,2);
  orientations.Items.AddRange(new object[]{"XYZ","XZY","YXZ","YZX","ZXY","ZYX"});orientations.SetItemChecked(0,true);orientations.Height=125;
  Add(settings,T("Dozwolone orientacje (wybierz jawnie)","Allowed orientations (explicit choice)"),orientations);
  arrangements.Items.AddRange(new object[]{"X","Y","Z"});arrangements.SetItemChecked(0,true);arrangements.SetItemChecked(1,true);arrangements.Height=70;
  Add(settings,T("Dozwolone kierunki urządzeń","Allowed arrangement axes"),arrangements);
  limitEnvelope.Text=T("Ogranicz gabaryt konstrukcji","Limit shell exterior");limitEnvelope.Size=new Size(305,35);settings.Controls.Add(limitEnvelope);
  foreach(string axis in new[]{"X","Y","Z"})AddNumber(settings,"max"+axis,T("Maksimum ","Maximum ")+axis+" [mm]",1000,1,10000,2);
  var right=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=2,Padding=new Padding(12,8,0,0)};right.RowStyles.Add(new RowStyle(SizeType.Absolute,180));right.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.Controls.Add(right,1,1);
  variants.Dock=DockStyle.Fill;variants.ReadOnly=true;variants.AllowUserToAddRows=false;variants.AllowUserToDeleteRows=false;variants.RowHeadersVisible=false;
  variants.MultiSelect=false;variants.SelectionMode=DataGridViewSelectionMode.FullRowSelect;variants.AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill;
  variants.AutoSizeRowsMode=DataGridViewAutoSizeRowsMode.AllCells;variants.DefaultCellStyle.WrapMode=DataGridViewTriState.True;variants.DefaultCellStyle.Padding=new Padding(5,8,5,8);variants.BackgroundColor=Color.White;
  variants.ColumnHeadersHeightSizeMode=DataGridViewColumnHeadersHeightSizeMode.AutoSize;
  foreach(string col in new[]{T("Orientacja","Orientation"),T("Kierunek","Axis"),T("Konstrukcja XYZ [mm]","Shell XYZ [mm]"),T("Objętość [l]","Volume [L]"),T("Wyjmowanie","Removal")})variants.Columns.Add(col,col);
  right.Controls.Add(variants,0,0);canvas.Dock=DockStyle.Fill;right.Controls.Add(canvas,0,1);
  var footer=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=2};footer.RowStyles.Add(new RowStyle(SizeType.Absolute,48));footer.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.Controls.Add(footer,0,2);root.SetColumnSpan(footer,2);
  var actions=new FlowLayoutPanel {Dock=DockStyle.Fill};Style(calculate,T("Oblicz do 3 propozycji","Calculate up to 3 proposals"));Style(accept,T("Wybierz i edytuj układ","Select and edit layout"));accept.BackColor=Color.FromArgb(237,102,21);accept.ForeColor=Color.White;actions.Controls.Add(calculate);actions.Controls.Add(accept);footer.Controls.Add(actions,0,0);status.Dock=DockStyle.Fill;status.Padding=new Padding(0,8,0,0);footer.Controls.Add(status,0,1);
  reload.Click+=async delegate{await Run(LoadData);};next.Click+=async delegate{await Run(async delegate{await LoadPage(nextCursor);});};sources.Click+=async delegate{await Run(ShowSources);};calculate.Click+=async delegate{await Run(Calculate);};
  accept.Click+=delegate{if(SelectedSpec!=null){DialogResult=DialogResult.OK;Close();}};
  devices.SelectedIndexChanged+=delegate{if(!loading){InvalidateProposals();DescribeDevice();}};
  foreach(var input in inputs.Values)input.ValueChanged+=delegate{InvalidateProposals();};lidOverride.CheckedChanged+=delegate{InvalidateProposals();};limitEnvelope.CheckedChanged+=delegate{InvalidateProposals();};
  orientations.ItemCheck+=delegate{InvalidateProposals();};arrangements.ItemCheck+=delegate{InvalidateProposals();};
  variants.SelectionChanged+=delegate{if(!showing)SelectProposal();};Shown+=async delegate{System.Threading.SynchronizationContext.SetSynchronizationContext(new WindowsFormsSynchronizationContext());if(autoLoad)await Run(LoadData);};
  FormClosing+=delegate(object sender,FormClosingEventArgs e){if(busy)e.Cancel=true;};UiText.LanguageChanged+=RefreshLanguage;FormClosed+=delegate{UiText.LanguageChanged-=RefreshLanguage;tips.Dispose();};UpdateButtons();
 }
 void Add(FlowLayoutPanel parent,string title,Control control){var caption=new Label {Text=title,Width=305,Height=35,Padding=new Padding(0,9,0,0)};captions.Add(caption);parent.Controls.Add(caption);control.Width=300;control.Margin=new Padding(0,0,0,8);parent.Controls.Add(control);}
 void AddNumber(FlowLayoutPanel parent,string key,string title,decimal value,decimal minimum,decimal maximum,int decimals){var input=new ScrollSafeNumber {Minimum=minimum,Maximum=maximum,Value=value,DecimalPlaces=decimals};inputs.Add(key,input);Add(parent,title,input);}
 void RefreshLanguage(object sender,EventArgs e){if(IsDisposed)return;Text=LayoutLanguage.Translate(Text);
  foreach(Control control in new Control[]{heading,reload,next,sources,calculate,accept,lidOverride,limitEnvelope})control.Text=LayoutLanguage.Translate(control.Text);
  foreach(var caption in captions)caption.Text=LayoutLanguage.Translate(caption.Text);
  foreach(DataGridViewColumn column in variants.Columns)column.HeaderText=LayoutLanguage.Translate(column.HeaderText);DescribeDevice();}
 static void Style(Button button,string text){button.Text=text;button.Width=300;button.Height=40;button.Margin=new Padding(0,0,8,5);button.BackColor=Color.White;}
 async Task<Dictionary<string,object>> Call(string name,object args){return await Task.Run(()=>backend(name,args));}
 async Task Run(Func<Task> action){if(System.Threading.Thread.CurrentThread.ManagedThreadId!=uiThread)throw new InvalidOperationException("Device UI operation must start on its owner thread");System.Threading.SynchronizationContext.SetSynchronizationContext(new WindowsFormsSynchronizationContext());if(busy)return;busy=true;UpdateButtons();try{await action();}catch(Exception ex){status.ForeColor=Color.Firebrick;status.Text=ex.Message+T("\nNie zapisano danych ani nie odświeżono numeru wersji w tle.","\nNo data saved or revision refreshed in the background.");}finally{busy=false;if(!IsDisposed)UpdateButtons();}}
 void UpdateButtons(){if(IsDisposed)return;reload.Enabled=!busy;next.Enabled=!busy&&nextCursor!=null;sources.Enabled=calculate.Enabled=!busy&&devices.SelectedItem!=null;accept.Enabled=!busy&&SelectedSpec!=null;devices.Enabled=!busy;foreach(var n in inputs.Values)n.Enabled=!busy;orientations.Enabled=arrangements.Enabled=lidOverride.Enabled=limitEnvelope.Enabled=!busy;}
 void InvalidateProposals(){if(loading)return;showing=true;try{SelectedSpec=SelectedBinding=null;proposals.Clear();variants.Rows.Clear();canvas.Result=null;canvas.Invalidate();}finally{showing=false;}status.Text=T("Ustawienia zmienione. Oblicz propozycje ponownie.","Settings changed. Calculate proposals again.");UpdateButtons();}
 async Task LoadData(){var saved=await Call("get_layout",new {project_id=projectId});BaseLayoutRevision=Convert.ToInt64(saved["revision"]);baseSpec=RevisionUi.Clone(Rpc.Obj(saved["spec"]));
  loading=true;try{foreach(var pair in inputs)if(baseSpec.ContainsKey(pair.Key))pair.Value.Value=Convert.ToDecimal(baseSpec[pair.Key]);if(baseSpec.ContainsKey("lid_constructor_override"))lidOverride.Checked=Convert.ToBoolean(baseSpec["lid_constructor_override"]);}finally{loading=false;}
  await LoadPage(null);status.Text=T("Wczytano katalog i układ v","Catalog and layout loaded, v")+BaseLayoutRevision+T(". Wybierz dozwolone warianty i oblicz propozycje.",". Choose allowed variants and calculate proposals.");}
 async Task LoadPage(string cursor){var args=new Dictionary<string,object>{{"limit",100}};if(cursor!=null)args["after_catalog_id"]=cursor;var result=await Call("list_device_records",args);
  InvalidateProposals();loading=true;try{devices.Items.Clear();foreach(var value in Rpc.Rows(result["devices"]))devices.Items.Add(new DeviceItem {Data=Rpc.Obj(value)});if(devices.Items.Count>0)devices.SelectedIndex=0;}finally{loading=false;}
  nextCursor=Rpc.Str(result,"next_cursor");if(nextCursor.Length==0)nextCursor=null;DescribeDevice();}
 void DescribeDevice(){var item=devices.SelectedItem as DeviceItem;if(item==null){source.Text=T("Brak urządzeń w tej stronie katalogu.","No devices on this catalog page.");return;}
  var fields=Rpc.Obj(item.Data["fields"]);var text=new StringBuilder();foreach(string axis in new[]{"X","Y","Z"}){var field=Rpc.Obj(fields[axis]);string state=Rpc.Str(field,"status");text.Append(axis+": "+(field["value"]==null?T("brak","missing"):Rpc.Str(field,"value"))+" mm · "+(state=="source_checked"?T("sprawdzone w źródle","source checked"):state=="conflict"?T("sprzeczne","conflict"):T("niepotwierdzone","unconfirmed"))+"\n");}
  text.Append(T("Wersja danych: ","Data revision: ")+Rpc.Str(item.Data,"revision"));source.Text=text.ToString();tips.SetToolTip(devices,item.ToString());}
 static object[] Checked(CheckedListBox list){var values=new List<object>();foreach(var value in list.CheckedItems)values.Add(value);return values.ToArray();}
 async Task Calculate(){InvalidateProposals();var item=devices.SelectedItem as DeviceItem;if(item==null)return;var spec=RevisionUi.Clone(baseSpec);
  foreach(var pair in inputs)if(pair.Key!="removal"&&!pair.Key.StartsWith("max"))spec[pair.Key]=pair.Key=="count"?(object)(int)pair.Value.Value:(double)pair.Value.Value;spec["lid_constructor_override"]=lidOverride.Checked;
  var constraints=new Dictionary<string,object>{{"allowed_orientations",Checked(orientations)},{"allowed_arrangements",Checked(arrangements)},
    {"removal_clearance_mm",(double)inputs["removal"].Value},{"max_external_mm",limitEnvelope.Checked?(object)new[]{(double)inputs["maxX"].Value,(double)inputs["maxY"].Value,(double)inputs["maxZ"].Value}:null}};
  var result=await Call("preview_catalog_layouts",new {catalog_id=Rpc.Str(item.Data,"catalog_id"),expected_device_revision=item.Data["revision"],spec=spec,constraints=constraints});ShowProposals(result);}
 void ShowProposals(Dictionary<string,object> result){showing=true;try{proposals.Clear();variants.Rows.Clear();SelectedSpec=SelectedBinding=null;canvas.Result=null;
  foreach(var value in Rpc.Rows(result["variants"])){var proposal=Rpc.Obj(value);proposals.Add(proposal);var data=Rpc.Obj(proposal["layout"]);variants.Rows.Add(Rpc.Str(proposal,"orientation"),Rpc.Str(proposal,"arrangement"),String.Join(" × ",Array.ConvertAll(Rpc.Rows(data["external"]),x=>Convert.ToDouble(x).ToString("0.##",CultureInfo.CurrentCulture))),Convert.ToDouble(data["volume_l"]).ToString("0.0"),T("+Z / AABB","+Z / AABB"));}
  variants.Tag=Rpc.Obj(result["device_binding"]);variants.ClearSelection();variants.CurrentCell=null;canvas.Invalidate();
  var warnings=new List<string>();foreach(var value in Rpc.Rows(result["release_blockers"]))warnings.Add(Convert.ToString(value));
  if(proposals.Count==0){foreach(var value in Rpc.Rows(result["rejected"]))warnings.Add(Rpc.Str(Rpc.Obj(value),"reason"));status.ForeColor=Color.Firebrick;status.Text=T("Brak dopuszczonego wariantu; potrzebna zmiana ograniczeń lub projekt ręczny. ","No allowed layout; change constraints or design manually. ")+String.Join("; ",warnings.ToArray());}
  else{status.ForeColor=Color.FromArgb(55,85,110);status.Text=T("Propozycje: ","Proposals: ")+proposals.Count+T(". Wybierz wiersz, aby obejrzeć układ i przejść do edycji. Bez automatycznego wyboru i zapisu.",". Select a row to view and edit it. No automatic selection or saving.")+(warnings.Count>0?"\n"+String.Join("; ",warnings.ToArray()):"");}
  }finally{showing=false;UpdateButtons();}}
 void SelectProposal(){if(variants.SelectedRows.Count==0||variants.SelectedRows[0].Index>=proposals.Count)return;var chosen=proposals[variants.SelectedRows[0].Index];var data=Rpc.Obj(chosen["layout"]);
  SelectedSpec=RevisionUi.Clone(Rpc.Obj(data["spec"]));SelectedBinding=RevisionUi.Clone(Rpc.Obj(variants.Tag));canvas.Result=data;canvas.Invalidate();UpdateButtons();}
 async Task ShowSources(){var item=devices.SelectedItem as DeviceItem;if(item==null)return;var record=await Call("get_device_record",new {catalog_id=Rpc.Str(item.Data,"catalog_id"),revision=item.Data["revision"]});
  var evidence=Rpc.Obj(record["record"]);var refs=new Dictionary<string,Dictionary<string,object>>();foreach(var value in Rpc.Rows(evidence["sources"])){var row=Rpc.Obj(value);refs[Rpc.Str(row,"id")]=row;}
  var text=new StringBuilder(item+"\n\n");foreach(var value in Rpc.Rows(evidence["observations"])){var row=Rpc.Obj(value);var reference=refs[Rpc.Str(row,"source_id")];text.AppendLine(Rpc.Str(row,"field")+": "+Rpc.Str(row,"value")+" "+Rpc.Str(row,"unit")+" — "+Rpc.Str(row,"confirmation"));text.AppendLine(Rpc.Str(reference,"reference")+" / "+Rpc.Str(reference,"locator"));text.AppendLine();}
  using(var form=new Form {Text=T("RockPro | Źródła i jednostki","RockPro | Sources and units"),Size=new Size(900,620),MinimumSize=new Size(650,420),StartPosition=FormStartPosition.CenterParent,Font=Font}){
   form.Controls.Add(new TextBox {Multiline=true,ReadOnly=true,Dock=DockStyle.Fill,ScrollBars=ScrollBars.Both,Text=text.ToString(),WordWrap=false});form.ShowDialog(this);System.Threading.SynchronizationContext.SetSynchronizationContext(new WindowsFormsSynchronizationContext());}}
}
}
