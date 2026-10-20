using System;
using System.Windows.Forms;
using RockPro.CAD;
class Preview { [STAThread] static void Main(){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new RockProPanel(null));} }
