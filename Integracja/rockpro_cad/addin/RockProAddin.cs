using System;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using interop.ICApiIronCAD;

[assembly: ComVisible(true)]
[assembly: AssemblyVersion("0.1.0.0")]
namespace RockPro.CAD {
    internal class PictureConverter : AxHost {
        private PictureConverter() : base("") {}
        internal static stdole.IPictureDisp Convert(Image image) {
            return (stdole.IPictureDisp)GetIPictureDispFromPicture(image);
        }
    }
    [Guid("B7659903-7C95-4E26-923F-DB5119AD1460")]
    [ProgId("RockPro.CAD.Addin")]
    [ClassInterface(ClassInterfaceType.None)]
    public class Addin : IZAddinServer {
        private ZAddinSite site;
        private ZCommandHandler command;
        private RockProPanel panel;
        internal static readonly string Root = Path.GetFullPath(Path.Combine(
            Path.GetDirectoryName(typeof(Addin).Assembly.Location), "..", ".."));
        internal static void Log(string text) {
            try { Directory.CreateDirectory(Path.Combine(Root,"logs"));
                File.AppendAllText(Path.Combine(Root,"logs","addin.log"),
                    DateTime.Now.ToString("s")+" "+text+Environment.NewLine); } catch {}
        }
        public void InitSelf(ZAddinSite addinSite) {
            try {
                site=addinSite;
                var logo=Image.FromFile(Path.Combine(Root,"assets","rockpro-logo.png"));
                command=site.CreateCommandHandler("RockProCAD.Connect","RockPro CAD",
                    "RockPro CAD — projekty, układ i parametry / projects, layout and parameters","RockPro CAD",
                    PictureConverter.Convert(logo),PictureConverter.Convert(logo));
                command.Enabled=true;
                command.OnClick += OnClick;
                command.OnUpdate += OnUpdate;
                IZEnvironment env=site.Application.EnvironmentMgr.get_Environment(eZEnvType.Z_ENV_SCENE);
                ZControlBar bar=env.AddControlBar(site,"RockPro CAD");
                bar.Controls.Add(ezControlType.Z_CONTROL_BUTTON,command.ControlDescriptor,null);
                env.GetRibbonBar(eZRibbonBarType.Z_RIBBONBAR).AddButton(command.ControlDescriptor);
                Log("InitSelf OK; ribbon command registered");
            } catch(Exception e) {Log("InitSelf ERROR "+e);MessageBox.Show(e.Message,"RockPro CAD");}
        }
        private void OnUpdate() {if(command!=null) command.Enabled=true;}
        private void OnClick() {
            try {
                if(panel==null || panel.IsDisposed) panel=new RockProPanel(site.Application);
                panel.Show();panel.BringToFront();
                Log("Panel shown");
            } catch(Exception e) {Log("Panel ERROR "+e);MessageBox.Show(e.Message,"RockPro CAD");}
        }
        public void DeInitSelf() {
            if(panel!=null) {panel.Close();panel.Dispose();panel=null;}
            if(command!=null) {command.OnClick-=OnClick;command.OnUpdate-=OnUpdate;command=null;}
            site=null;Log("DeInitSelf OK");
        }
    }
}
