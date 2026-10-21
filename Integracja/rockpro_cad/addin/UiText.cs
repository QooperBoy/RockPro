using System;
using System.IO;
namespace RockPro.CAD {
 internal static class UiText {
  static bool english=Load();
  internal static bool IsEnglish {get{return english;}}
  internal static event EventHandler LanguageChanged;
  internal static string T(string pl,string en){return english?en:pl;}
  static string SettingPath {get{return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"RockPro","CAD","ui-language.txt");}}
  static bool Load(){try{return File.Exists(SettingPath)&&File.ReadAllText(SettingPath).Trim()=="en";}catch{return false;}}
  internal static void SetLanguage(bool value){SetLanguage(value,true);}
  internal static void SetLanguage(bool value,bool persist){if(english==value)return;if(persist){Directory.CreateDirectory(Path.GetDirectoryName(SettingPath));File.WriteAllText(SettingPath,value?"en":"pl");}english=value;var changed=LanguageChanged;if(changed!=null)changed(null,EventArgs.Empty);}
 }
}
