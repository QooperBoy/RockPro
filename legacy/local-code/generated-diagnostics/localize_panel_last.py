import json
p='Integracja/rockpro_cad/addin/RockProPanel.cs';s=open(p,encoding='utf-8-sig').read()
s=s.replace('nav=new FlowLayoutPanel {Dock=DockStyle.Fill,','nav=new FlowLayoutPanel {Dock=DockStyle.Fill,AutoScroll=true,')
s=s.replace('static string Caption(string key)', 'internal static string Caption(string key)')
s=s.replace('case "revision":return UiText.T("Wersja","Version");default:return key;', 'case "revision":return UiText.T("Wersja","Version");case "id":return "ID";case "created_at":return UiText.T("Data zapisu (UTC)","Saved at (UTC)");case "label":return UiText.T("Nazwa kopii","Copy name");case "validation":return UiText.T("Kontrola CAD","CAD check");case "integrity":return UiText.T("Integralność pliku","File integrity");case "path":return UiText.T("Plik archiwum","Archive file");case "report_path":return UiText.T("Plik raportu","Report file");case "sha256":return UiText.T("Suma kontrolna SHA256","SHA256 checksum");default:return key;')
s=s.replace('sb.AppendLine(key+": "+Rpc.Str(d,key))','sb.AppendLine(RevisionUi.Caption(key)+": "+Rpc.Str(d,key))')
s=s.replace('info.Controls.Add(copy);info.Controls.Add(all);','info.Controls.Add(copy);info.Controls.Add(all);var purpose=Label(UiText.T("Szczegóły zapisanej kopii. Dane są tylko do odczytu; przyciski kopiują ścieżkę lub cały opis.","Saved copy details. Read-only data; buttons copy the file path or the complete description."),10,Muted);purpose.SetBounds(16,66,840,48);purpose.AutoEllipsis=false;info.Height=122;info.Controls.Add(purpose);')
s=s.replace('UiText.T("Wróć bez zapisywania","Keep my unsaved entries")','UiText.T("Wróć bez zapisywania","Return without saving")')
# Add a useful hover to every project entry, not just button-caption duplication.
s=s.replace('s.Controls.Add(t);return t;', 'tips.SetToolTip(t,UiText.T("Uzupełnij pole i zapisz kartę, aby zachować zmianę. Zmiana języka nie usuwa wpisanej treści.","Fill in this field and save the card to keep your change. Switching language preserves your text."));s.Controls.Add(t);return t;')
open(p,'w',encoding='utf-8-sig').write(s)
