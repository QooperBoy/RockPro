using System;
using System.Drawing;
using System.Reflection;
using System.Windows.Forms;
using RockPro.CAD;
class LayoutUiChecks {
 [STAThread] static void Main(){Application.EnableVisualStyles();
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
  Console.WriteLine("PASS: depth buffer in both orders; number and choice wheel suppression; form scrolling");
 }
}
