import re
p='Integracja/rockpro_cad/addin/RockProPanel.cs';s=open(p,encoding='utf-8-sig').read()
s=s.replace('string source="",currentView="Projekt",operationNotice="";bool busy=false;', 'string source="",currentView="Projekt",operationNotice="";bool busy=false;\n ComboBox language; Label sidebarNote;')
s=s.replace('var note=Label(UiText.T("MVP', 'var note=Label(UiText.T("MVP')
s=s.replace('nav.Controls.Add(note);outer.Controls.Add(nav,0,1);','nav.Controls.Add(note);sidebarNote=note;\n  var languageTitle=Label("Język / Language",9,Color.White);languageTitle.Size=new Size(205,24);nav.Controls.Add(languageTitle);language=new ComboBox {Width=205,DropDownStyle=ComboBoxStyle.DropDownList};language.Items.AddRange(new object[]{"Polski","English"});language.SelectedIndex=UiText.IsEnglish?1:0;tips.SetToolTip(language,"Język interfejsu / Interface language. Wpisane dane pozostają bez zmian / Entered data stay unchanged.");language.SelectedIndexChanged+=delegate{if(busy)return;try{UiText.SetLanguage(language.SelectedIndex==1);}catch(Exception ex){language.SelectedIndex=UiText.IsEnglish?1:0;MessageBox.Show(this,UiText.T("Nie udało się zapisać języka. ","Could not save language preference. ")+ex.Message);}};nav.Controls.Add(language);outer.Controls.Add(nav,0,1);')
s=s.replace('var b=Button(n,delegate','var b=Button(NavCaption(n),delegate').replace('b.Width=208;b.Height=44;','b.Tag=n;b.Width=208;b.Height=44;')
s=s.replace('ShowView("Projekt");Shown+=','UiText.LanguageChanged+=OnLanguageChanged;FormClosed+=delegate{UiText.LanguageChanged-=OnLanguageChanged;};\n  ShowView("Projekt");Shown+=')
s=s.replace('bool active=c.Text==name;','bool active=Convert.ToString(c.Tag)==name;')
s=s.replace('refresh.Enabled=false;progress.Visible=true;','refresh.Enabled=false;language.Enabled=false;progress.Visible=true;').replace('refresh.Enabled=true;progress.Visible=false;','refresh.Enabled=true;language.Enabled=true;progress.Visible=false;')
insert=r'''
 static string NavCaption(string key){switch(key){case "Projekt":return UiText.T("Projekt","Project");case "Układ urządzeń":return UiText.T("Układ urządzeń","Device layout");case "Etapy":return UiText.T("Etapy","Stages");case "Parametry":return UiText.T("Parametry","Parameters");case "Snapshoty":return UiText.T("Archiwum CAD","CAD archive");default:return UiText.T("Dostępne funkcje","Available features");}}
 sealed class FieldDraft {internal Control Original;internal string Text;internal decimal Number;internal int Index;internal bool Enabled;}
 static void CaptureFields(Control root,List<FieldDraft> fields){foreach(Control c in root.Controls){if(c is TextBox || c is NumericUpDown || c is ComboBox)fields.Add(new FieldDraft {Original=c,Text=c.Text,Number=c is NumericUpDown?((NumericUpDown)c).Value:0,Index=c is ComboBox?((ComboBox)c).SelectedIndex:-1,Enabled=c.Enabled});else CaptureFields(c,fields);}}
 void OnLanguageChanged(object sender,EventArgs e){
  if(IsDisposed)return;if(InvokeRequired){BeginInvoke(new EventHandler(OnLanguageChanged),sender,e);return;}
  // Rebuild only presentation; restore every draft and the original concurrency baselines.
  var draft=new List<FieldDraft>();CaptureFields(body,draft);var originalCard=RevisionUi.Clone(cardBase);var originalStages=new Dictionary<string,Dictionary<string,object>>();foreach(var p in stageBases)originalStages[p.Key]=RevisionUi.Clone(p.Value);
  ShowView(currentView);var replacement=new List<FieldDraft>();CaptureFields(body,replacement);
  for(int i=0;i<Math.Min(draft.Count,replacement.Count);i++){Control c=replacement[i].Original;if(c is NumericUpDown)((NumericUpDown)c).Value=draft[i].Number;else if(c is ComboBox)((ComboBox)c).SelectedIndex=draft[i].Index;else c.Text=draft[i].Text;c.Enabled=draft[i].Enabled;}
  cardBase=originalCard; // Do not adopt a newer version merely because the display language changed.
  foreach(var p in originalStages)stageBases[p.Key]=p.Value;
  Text=UiText.T("RockPro CAD | Stanowisko konstruktora","RockPro CAD | Designer workspace");
  foreach(Control c in nav.Controls)if(c is Button){string key=Convert.ToString(c.Tag);c.Text=String.IsNullOrEmpty(key)?UiText.T("+ Nowy projekt","+ New project"):NavCaption(key);tips.SetToolTip(c,c.Text);}
  refresh.Text=UiText.T("Połącz / Odśwież","Connect / Refresh");tips.SetToolTip(refresh,refresh.Text);
  sidebarNote.Text=UiText.T("MVP\n\nCAD: szkielet 10 płyt\nLokalna baza projektów\nAI: dostęp przez MCP\n\nOkucia i rysunki nie są jeszcze generowane.","MVP\n\nCAD: 10-panel structure\nLocal project database\nAI access through MCP\n\nHardware and drawings are not generated yet.");
  connection.Text=UiText.T("Stan połączenia: użyj Odśwież, aby sprawdzić","Connection status: use Refresh to check");summary.Text=UiText.T("Projekty w bazie: ","Projects in database: ")+projects.Count;bottom.Text=UiText.T("Zmieniono język. Niezapisane wpisy zostały zachowane.","Language changed. Unsaved entries were preserved.");language.SelectedIndex=UiText.IsEnglish?1:0;
 }
'''
s=s.replace(' Label Label(string s,int size,Color color)',insert+'\n Label Label(string s,int size,Color color)')
# Module field captions remain tied to translated module categories.
s=s.replace('StartsWith("Okucia")','StartsWith(UiText.T("Okucia","Hardware"))')
# Clarify guidance and prevent snapshot drafts lost on navigation as well.
s=s.replace('Heading(s,"Układ urządzeń",','Heading(s,UiText.T("Układ urządzeń","Device layout"),')
s=s.replace('Heading(s,"Zakres integracji",','Heading(s,UiText.T("Dostępne funkcje","Available features"),')
# Add explicit purpose after card header; keep all user-entered values unchanged.
s=s.replace('title=Field(s,', 'var help=Label(UiText.T("Uzupełnij dane zlecenia. Liczba skrzyń oznacza liczbę kompletnych sztuk, a nie urządzeń w jednej skrzyni. Zapis utrwala dane projektu i powiązanie z plikiem ICS.","Enter order details. Number of cases means complete cases, not devices inside one case. Saving records project details and the assigned ICS file."),10,Muted);help.Size=new Size(700,65);help.AutoEllipsis=false;s.Controls.Add(help);\n  title=Field(s,')
s=s.replace('b.Size=new Size(690,48);','b.Size=new Size(720,76);b.AutoEllipsis=false;')
# Replace awkward Polish wording only inside T first argument, not stable identifiers.
s=s.replace('UiText.T("Dokonano: ",','UiText.T("Zakończono: ",')
s=s.replace('UiText.T("BRAK BACKENDU",','UiText.T("PLANOWANE",').replace('UiText.T("POŁĄCZONE",','UiText.T("DOSTĘPNE",').replace('UiText.T("CZĘŚCIOWO",','UiText.T("CZĘŚCIOWO DOSTĘPNE",')
s=s.replace('UiText.T("Automatyczne harnessy i porównania",','UiText.T("Automatyczne kontrole i porównania",')
s=s.replace('UiText.T("Excel i BOM",','UiText.T("Excel i zestawienie materiałów",')
s=s.replace('UiText.T("Historia snapshotów",','UiText.T("Archiwalne kopie CAD",').replace('UiText.T("Nazwa snapshotu",','UiText.T("Nazwa kopii archiwalnej",').replace('UiText.T("Zapisz snapshot CAD",','UiText.T("Zapisz kopię archiwalną",')
s=s.replace('UiText.T("Zachowaj moje wpisy",','UiText.T("Wróć bez zapisywania",')
s=s.replace('UiText.T("Nowy projekt • dane nie są zapisywane, dopóki nie klikniesz Zapisz kartę.",','UiText.T("Nowy projekt • uzupełnij dane, przypisz zapisany plik ICS i wybierz Zapisz kartę projektu.",')
s=s.replace('UiText.T("Odsunięcie prezentacyjne pokrywy • oś Z",','UiText.T("Odsunięcie pokrywy tylko w podglądzie • oś Z",')
open(p,'w',encoding='utf-8-sig').write(s)
