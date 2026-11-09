import json,sys
from pathlib import Path
from wholecase_common import *
sys.stdout.reconfigure(encoding='utf-8')
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'));folder=Path(cfg['folder']);m=json.loads((folder/'skeleton_manifest.json').read_text(encoding='utf-8'));legacy,base,doc=connect(m['file']);doc.Save();print('Saved final model',doc.Name)
text='''ROCKPRO — PARAMETRYCZNY SZKIELET MVP

Otwórz RockPro_Epson_szkielet_MVP.ics.
Tabela: prawy przycisk na pustym tle sceny -> Parametry...
Edytuj kolumnę Równanie; Zastosuj.

RP_Length = 914 mm — wspólna długość
RP_Depth = 602 mm — wspólna głębokość
RP_BaseHeight = 239.24 mm — wysokość dolnej konstrukcji
RP_LidHeight = 104.13 mm — wysokość górnej konstrukcji
RP_Thickness = 9.8 mm — grubość wszystkich płyt
RP_DisplayGap = 30 mm — przerwa prezentacyjna między połowami (0 mm zamyka szkielet)

Rozpoznanie_plyt.html zawiera 10 płyt odczytanych z obecnego projektu.
Epson_source_snapshot.ics zachowuje bieżący stan oryginalnej sceny w momencie rozpoczęcia pracy.

Zakres: 10 pełnych prostopadłościennych płyt, bez wycięć, okuć, pianek i metadanych WoodLAB.
W źródle tylna płyta dołu jest przesunięta o -3.02 mm w osi wysokości. W nowym szkielecie została jawnie wyrównana do pozostałych ścian. Grubość 9.8 mm pochodzi z geometrii, nie ze specyfikacji materiału.

Weryfikacja: 9 wariantów (bazowy, długość, głębokość, dwie wysokości osobno, grubość, łączony, mniejszy, powrót), zapis/ponowne otwarcie, zmiana po otwarciu. Niezależny agent potwierdził rzeczywistą geometrię i natywne formuły. Raport: independent_live_review.json. Native UI edit nieprzetestowana; zmiany wykonywano przez API.

Generator: ../../build_clean_skeleton.py. Działa na zapisanym stanie skeleton_state.json i czystym szablonie katalogowym. Rejestruje zależności po zakończeniu importu wszystkich części, nie wymaga działającego Pythona do przechowywania formuł. Nie jest jeszcze uniwersalnym rozpoznawaniem dowolnych skrzyń ani serwerem MCP.
'''
(folder/'START_HERE.txt').write_text(text,encoding='utf-8')
p=folder/'Rozpoznanie_plyt.html';s=p.read_text(encoding='utf-8');s+='''<h2>Gotowy szkielet MVP</h2><p>Plik: <b>RockPro_Epson_szkielet_MVP.ics</b>. Dwa zespoły po pięć płyt. Parametry: RP_Length, RP_Depth, RP_BaseHeight, RP_LidHeight, RP_Thickness, RP_DisplayGap.</p><p><b>Testy API: PASS.</b> Dziewięć wariantów wymiarów, ponowne otwarcie i zmiana po otwarciu. Niezależny agent potwierdził geometrię, styki i zapisane wyrażenia. Edycja z okna tabeli parametrów nie została osobno zweryfikowana.</p>''';p.write_text(s,encoding='utf-8')
