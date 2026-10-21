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
internal sealed class ScrollSafeChoice : ComboBox {
 protected override void WndProc(ref Message m){if(m.Msg==0x020A){FormScroll.Forward(this,unchecked((short)((m.WParam.ToInt64()>>16)&0xffff)));return;}base.WndProc(ref m);}
}
[ComVisible(false)]
internal sealed class LayoutForm : Form {
 readonly string projectId;
 readonly Dictionary<string,Control> fields=new Dictionary<string,Control>();
 readonly ToolTip tips=new ToolTip {AutoPopDelay=20000};
 readonly Timer timer=new Timer {Interval=450};
 readonly LayoutCanvas canvas=new LayoutCanvas();
 readonly Label status=new Label(), information=new Label();
 readonly Label[,] metricCells=new Label[2,3];
 readonly TableLayoutPanel metricTable=new TableLayoutPanel();
 string informationText="";
 readonly Button save=new StudioButton(), apply=new StudioButton();
 bool loading=true,dirty=false,working=false,calculating=false;
 int revision=0;
 public LayoutForm(string id) {
  projectId=id;Text="RockPro CAD | Przygotowanie skrzyni — urządzenia i układ";Size=new Size(1240,840);MinimumSize=new Size(1020,680);StartPosition=FormStartPosition.CenterParent;Font=new Font("Segoe UI",10);BackColor=Color.FromArgb(238,242,246);AutoScaleMode=AutoScaleMode.Dpi;
  var root=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=2,RowCount=3,Padding=new Padding(18)};
  root.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,365));root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));root.RowStyles.Add(new RowStyle(SizeType.Absolute,65));root.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.RowStyles.Add(new RowStyle(SizeType.Absolute,90));Controls.Add(root);
  var title=new Label {Text="01  /  Wyposażenie i przestrzeń\nUstal zawartość jednej skrzyni. Wszystkie wymiary w mm.",Dock=DockStyle.Fill,Font=new Font("Segoe UI",13,FontStyle.Bold),ForeColor=Color.FromArgb(31,42,55)};root.Controls.Add(title,0,0);root.SetColumnSpan(title,2);
  var scroll=new Panel {Dock=DockStyle.Fill,AutoScroll=true};root.Controls.Add(scroll,0,1);
  var stack=new FlowLayoutPanel {Dock=DockStyle.Top,AutoSize=true,FlowDirection=FlowDirection.TopDown,WrapContents=false,Padding=new Padding(4)};scroll.Controls.Add(stack);
  Section(stack,"URZĄDZENIE • uproszczona bryła");TextField(stack,"name","Nazwa urządzenia","Urządzenie");
  Number(stack,"x","Wymiar X urządzenia",345.4m,1,5000);Number(stack,"y","Wymiar Y urządzenia",241.9m,1,5000);Number(stack,"z","Wymiar Z urządzenia",88.2m,1,5000);Number(stack,"count","Sztuk w jednej skrzyni",2,1,30);
  Choice(stack,"orientation","Orientacja: X / Y / Z skrzyni",new[]{"XYZ","XZY","YXZ","YZX","ZXY","ZYX"},new[]{"X / Y / Z — standard","X / Z / Y — na boku","Y / X / Z — obrót w poziomie","Y / Z / X","Z / X / Y","Z / Y / X"});
  Section(stack,"ROZMIESZCZENIE");Choice(stack,"arrangement","Kierunek kolejnych urządzeń",new[]{"X","Y","Z"},new[]{"Obok siebie — oś X","Jeden za drugim — oś Y","Piętrowo — oś Z"});
  Number(stack,"gap","Luz między urządzeniami",20,0,500);Number(stack,"clearance","Rezerwa przy każdej ścianie",20,0,500);Number(stack,"separator","Grubość przegrody (0 = brak)",0,0,50);
  Section(stack,"BOCZNA KOMORA NA AKCESORIA");Choice(stack,"side","Położenie komory",new[]{"none","X","Y"},new[]{"Bez komory","Z boku — +X","Z tyłu — +Y"});TextField(stack,"side_name","Zawartość komory","Kable");
  Number(stack,"side_width","Szerokość zawartości w poprzek komory",80,1,5000);Number(stack,"side_depth","Długość zawartości wzdłuż komory",300,1,5000);Number(stack,"side_height","Wysokość zawartości komory",50,1,5000);
  Section(stack,"KONSTRUKCJA DO NASTĘPNEGO ETAPU");Number(stack,"thickness","Grubość sklejki",9,1,100);Number(stack,"lid_height","Zewnętrzna wysokość pokrywy",50,2,1000);
  var right=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=3,Padding=new Padding(14,0,0,0)};right.RowStyles.Add(new RowStyle(SizeType.Absolute,36));right.RowStyles.Add(new RowStyle(SizeType.Percent,100));right.RowStyles.Add(new RowStyle(SizeType.Absolute,115));root.Controls.Add(right,1,1);
  var toolbar=new Panel {Dock=DockStyle.Fill};var views=new FlowLayoutPanel {Dock=DockStyle.Fill,Padding=new Padding(0,0,42,0)};foreach(string v in new[]{"3D","Z góry","Z przodu"}){string view=v;var b=new Button {Text=v,Width=95,Height=30,FlatStyle=FlatStyle.Flat,BackColor=Color.White};b.Click+=delegate{canvas.View=view;canvas.Invalidate();};views.Controls.Add(b);}toolbar.Controls.Add(views);
  information.Text="ⓘ";information.AccessibleName="Informacje o podglądzie i ograniczeniach";information.Font=new Font("Segoe UI",16,FontStyle.Regular);information.ForeColor=Color.FromArgb(102,114,130);information.TextAlign=ContentAlignment.MiddleCenter;information.Dock=DockStyle.Right;information.Width=38;information.Cursor=Cursors.Help;information.TabStop=true;information.Click+=delegate{MessageBox.Show(this,informationText,"Podgląd — legenda i informacje");};information.KeyDown+=delegate(object sender,KeyEventArgs e){if(e.KeyCode==Keys.Enter||e.KeyCode==Keys.Space)MessageBox.Show(this,informationText,"Podgląd — legenda i informacje");};toolbar.Controls.Add(information);right.Controls.Add(toolbar,0,0);canvas.Dock=DockStyle.Fill;right.Controls.Add(canvas,0,1);
  metricTable.Dock=DockStyle.Fill;metricTable.BackColor=Color.White;metricTable.Padding=new Padding(10,6,10,6);metricTable.ColumnCount=4;metricTable.RowCount=3;metricTable.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,43));for(int i=0;i<3;i++)metricTable.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,19));
  foreach(string heading in new[]{"Wymiary [mm]","X • długość","Y • głębokość","Z • wysokość"}){int col=metricTable.Controls.Count;var label=MetricLabel(heading,true);metricTable.Controls.Add(label,col,0);}for(int row=0;row<2;row++){metricTable.RowStyles.Add(new RowStyle(SizeType.Percent,33));metricTable.Controls.Add(MetricLabel(row==0?"Wnętrze skrzyni":"Gabaryt sklejki",false),0,row+1);for(int col=0;col<3;col++){var label=MetricLabel("—",false);label.TextAlign=ContentAlignment.MiddleRight;metricCells[row,col]=label;metricTable.Controls.Add(label,col+1,row+1);}}metricTable.RowStyles.Add(new RowStyle(SizeType.Percent,34));right.Controls.Add(metricTable,0,2);SetInformation("");
  var footer=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=1,RowCount=2};footer.RowStyles.Add(new RowStyle(SizeType.Absolute,50));footer.RowStyles.Add(new RowStyle(SizeType.Percent,100));root.Controls.Add(footer,0,2);root.SetColumnSpan(footer,2);
  var buttons=new FlowLayoutPanel {Dock=DockStyle.Fill};Style(save,"Zapisz układ",false);Style(apply,"Utwórz szkielet na kopii ICS",true);buttons.Controls.Add(save);buttons.Controls.Add(apply);footer.Controls.Add(buttons,0,0);status.Dock=DockStyle.Fill;status.Font=new Font("Segoe UI",9,FontStyle.Regular);status.ForeColor=Color.FromArgb(102,114,130);status.Text="Wczytywanie układu…";footer.Controls.Add(status,0,1);
  foreach(var field in fields.Values)field.Enabled=false; save.Enabled=apply.Enabled=false;
  save.Click+=async delegate{await Persist(false);};apply.Click+=async delegate{await Persist(true);};
  timer.Tick+=async delegate{timer.Stop();await Preview();};Shown+=async delegate{await LoadLayout();};
  FormClosing+=delegate(object sender,FormClosingEventArgs e){if(working){e.Cancel=true;return;}if(dirty && MessageBox.Show(this,"Zamknąć bez zapisania zmian układu?","Niezapisany układ",MessageBoxButtons.YesNo)!=DialogResult.Yes)e.Cancel=true;};
  FormClosed+=delegate{timer.Stop();timer.Dispose();tips.Dispose();};
 }
 void Style(Button b,string text,bool primary){b.Text=text;b.Width=primary?290:180;b.Height=40;b.BackColor=primary?Color.FromArgb(237,102,21):Color.White;b.ForeColor=primary?Color.White:Color.FromArgb(31,42,55);b.FlatAppearance.MouseOverBackColor=Color.FromArgb(255,180,100);}
 void Section(FlowLayoutPanel p,string s){p.Controls.Add(new Label {Text=s,Width=325,Height=36,Padding=new Padding(0,12,0,0),Font=new Font("Segoe UI",9,FontStyle.Bold),ForeColor=Color.FromArgb(153,71,18)});}
 void Add(FlowLayoutPanel p,string key,string label,Control c){p.Controls.Add(new Label {Text=label,Width=325,Height=23,AutoEllipsis=true});c.Width=315;c.Margin=new Padding(0,0,0,9);p.Controls.Add(c);fields[key]=c;tips.SetToolTip(c,label+". Osie urządzenia są mapowane na osie skrzyni przez wybraną orientację.");}
 void Number(FlowLayoutPanel p,string k,string l,decimal v,decimal min,decimal max){var c=new ScrollSafeNumber {Minimum=min,Maximum=max,DecimalPlaces=k=="count"?0:2,Value=v};Add(p,k,l,c);c.ValueChanged+=delegate{Changed();};}
 void TextField(FlowLayoutPanel p,string k,string l,string v){var c=new TextBox {Text=v,MaxLength=100};Add(p,k,l,c);c.TextChanged+=delegate{Changed();};}
 void Choice(FlowLayoutPanel p,string k,string l,string[] values,string[] labels){var c=new ScrollSafeChoice {DropDownStyle=ComboBoxStyle.DropDownList,Tag=values};c.Items.AddRange(labels);c.SelectedIndex=0;Add(p,k,l,c);c.SelectedIndexChanged+=delegate{Changed();};}
 void Changed(){if(loading)return;dirty=true;revision++;apply.Enabled=false;canvas.Result=null;canvas.Invalidate();for(int r=0;r<2;r++)for(int c=0;c<3;c++)metricCells[r,c].Text="—";status.Text="Przeliczanie układu…";timer.Stop();timer.Start();}
 Dictionary<string,object> Spec(){var s=new Dictionary<string,object>();foreach(var pair in fields){var n=pair.Value as NumericUpDown;var c=pair.Value as ComboBox;s[pair.Key]=n!=null?(object)(pair.Key=="count"?(object)(int)n.Value:(double)n.Value):c!=null?(object)((string[])c.Tag)[c.SelectedIndex]:pair.Value.Text;}return s;}
 async Task LoadLayout(){try{var r=await Task.Run(()=>Rpc.Call("get_layout",new {project_id=projectId}));if(IsDisposed)return;var spec=Rpc.Obj(r["spec"]);foreach(var pair in fields){if(!spec.ContainsKey(pair.Key))continue;var n=pair.Value as NumericUpDown;var c=pair.Value as ComboBox;if(n!=null)n.Value=Convert.ToDecimal(spec[pair.Key]);else if(c!=null)c.SelectedIndex=Array.IndexOf((string[])c.Tag,Convert.ToString(spec[pair.Key]));else pair.Value.Text=Convert.ToString(spec[pair.Key]);}Render(r);dirty=false;}catch(Exception ex){status.Text=ex.Message;apply.Enabled=false;}finally{loading=false;if(!IsDisposed){foreach(var c in fields.Values)c.Enabled=true;save.Enabled=true;}}}
 async Task Preview(){if(calculating||working){timer.Start();return;}calculating=true;int token=revision;var spec=Spec();try{var r=await Task.Run(()=>Rpc.Call("preview_layout",new {spec=spec}));if(!IsDisposed&&token==revision)Render(r);}catch(Exception ex){if(!IsDisposed&&token==revision){status.Text="Nieprawidłowy układ: "+ex.Message;apply.Enabled=false;canvas.Result=null;canvas.Invalidate();}}finally{calculating=false;}}
 Label MetricLabel(string text,bool header){return new Label {Text=text,Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleLeft,AutoEllipsis=true,Font=new Font("Segoe UI",9,FontStyle.Regular),ForeColor=header?Color.FromArgb(120,132,145):Color.FromArgb(45,58,72),BackColor=header?Color.FromArgb(247,249,252):Color.White,Margin=new Padding(0),Padding=new Padding(7,0,7,0)};}
 void SetInformation(string warnings){informationText="LEGENDA\nNiebieski — urządzenia\nPomarańczowy — akcesoria\nSzary — przegrody\nLinia przerywana — obrys konstrukcji\n\nWYMIARY\nWnętrze: dostępna przestrzeń między płytami.\nGabaryt sklejki: wnętrze + dwie grubości płyt.\nBez wystających okuć i kół. Komora uwzględnia obrys akcesoriów i rezerwę.\n\n"+warnings;tips.SetToolTip(information,informationText);information.AccessibleDescription=informationText;}
 void Render(Dictionary<string,object> r){canvas.Result=r;canvas.Invalidate();var inner=Rpc.Rows(r["internal"]);var outer=Rpc.Rows(r["external"]);for(int c=0;c<3;c++){metricCells[0,c].Text=Convert.ToDouble(inner[c]).ToString("0.##",CultureInfo.CurrentCulture);metricCells[1,c].Text=Convert.ToDouble(outer[c]).ToString("0.##",CultureInfo.CurrentCulture);}SetInformation(String.Join("\n",Array.ConvertAll(Rpc.Rows(r["warnings"]),x=>Convert.ToString(x))));status.Text="Obrysy mieszczą się • brak przenikania. Szczegóły pod ⓘ.";apply.Enabled=!working;}
 string Dims(object o){return String.Join(" × ",Array.ConvertAll(Rpc.Rows(o),x=>Convert.ToDouble(x).ToString("0.##",CultureInfo.CurrentCulture)));}
 async Task Persist(bool cad){if(working||loading)return;working=true;timer.Stop();save.Enabled=apply.Enabled=false;foreach(var c in fields.Values)c.Enabled=false;var spec=Spec();try{status.Text="Zapis układu do wspólnej bazy…";var r=await Task.Run(()=>Rpc.Call("save_layout",new {project_id=projectId,spec=spec}));dirty=false;Render(r);if(cad){status.Text="Tworzenie kopii szkieletu i kontrola geometrii w IronCAD…";var parameters=Rpc.Obj(r["parameters"]);var result=await Task.Run(()=>Rpc.Call("change_dimensions_on_copy",new {project_id=projectId,changes=parameters,label="Szkielet z układu urządzeń"}));MessageBox.Show(this,"Szkielet zapisany na kopii:\n"+Rpc.Str(result,"copy")+"\n\nDo CAD przekazano gabaryty konstrukcji. Bryły urządzeń, przegrody i komora są zapisane w układzie i widoczne w podglądzie; ich wstawianie do ICS będzie kolejnym etapem.","Szkielet z układu");}status.Text="Układ zapisany w SQLite. "+(cad?"Kopia ICS utworzona i sprawdzona.":"Możesz wrócić do niego po ponownym otwarciu dodatku.");}catch(Exception ex){status.Text="Operacja nieukończona: "+ex.Message;MessageBox.Show(this,ex.Message,"RockPro — wynik operacji");}finally{working=false;save.Enabled=true;apply.Enabled=canvas.Result!=null;foreach(var c in fields.Values)c.Enabled=true;}}
}

[ComVisible(false)]
internal sealed class LayoutCanvas : Control {
 public Dictionary<string,object> Result;
 public string View="3D";
 public LayoutCanvas(){DoubleBuffered=true;BackColor=Color.FromArgb(249,251,253);ResizeRedraw=true;}
 static double[] Vec(object o){return Array.ConvertAll(Rpc.Rows(o),x=>Convert.ToDouble(x));}
 PointF Raw(double x,double y,double z){if(View=="Z góry")return new PointF((float)x,(float)-y);if(View=="Z przodu")return new PointF((float)x,(float)-z);return new PointF((float)((x-y)*.866),(float)((x+y)*.38-z));}
 protected override void OnPaint(PaintEventArgs e){base.OnPaint(e);var g=e.Graphics;g.SmoothingMode=SmoothingMode.AntiAlias;if(Result==null){g.DrawString("Podgląd zostanie pokazany po przeliczeniu układu",Font,Brushes.Gray,20,30);return;}
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
  using(var captionFont=new Font("Segoe UI",9,FontStyle.Regular))g.DrawString("OBRYS SKRZYNI • "+View+" • mm",captionFont,Brushes.DimGray,14,12);

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
