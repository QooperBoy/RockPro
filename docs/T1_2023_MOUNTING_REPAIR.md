# T1 w IronCAD 2023 — montaż i polskie parametry

Późniejsze uzupełnienie: [CASE_STRUCTURE.md](CASE_STRUCTURE.md) dodaje cztery
brakujące wycięcia 27095 w tylnej sklejce, sześć grup sceny i obowiązkową
kontrolę 24 obróbek. Odbudowa powiązań po grupowaniu oraz natywny resize/restore
PASS. Poniższy raport 20 obróbek opisuje wcześniejszy checkpoint.

26.10.2026. Naprawiono własną, niezapisaną Scene14 w IronCAD 2023 PU1 SP1
(25.0.12.18734). Nie zapisano ICS ani nie zmieniano T1_mvp_v_4_3 w IronCAD 2027.
Nie używano sterowania pulpitem.

## Kod

- `core_case/t1_mounting.py`: zmierzone bazy 410429/38083, krawędź EG-0113,
  luzy podpór i strefy zawiasów; polskie nazwy i komentarze PARAMETERS_PL.
- `core_case/transport_rules.py`: długość podpór D−70 zamiast D−40 mm,
  uwzględniająca wewnętrzną krawędź profilu na 33 mm i luz 2 mm.
- `scripts/prepare_scene14_repair.py`: plan przypięty do inwentarza 72 elementów
  i GUID prototypu. Nie jest adapterem dowolnego ICS.
- `scripts/native/RepairT1Mounting2023.cs`: naprawa przez istniejący pojedynczy
  wykonawca `run_t1_machining_job.py`, niezależne kontrole i polskie nazwy drzewa.

Historyczny `artifacts/.../prepare_unsaved.py` zawiera błędne reguły Scene14;
nie używać go jako poprawionego generatora. Nowe bazy dotyczą konkretnych SKU.
Stary kontrakt sześciu parametrów MCP i zainstalowana DLL pozostają odrębne.

## Poprawki

1. Narożniki: powierzchnie skrzydeł na lokalnych X/Y/Z=16,5 mm przylegają
   do właściwych powierzchni sklejki; kontrolowane są także ich normalne.
2. Zawiasy: cztery przerwy w tylnych profilach, szerokość 102 mm + dwa luzy,
   przemieszczane wraz z odsunięciem zawiasów.
3. Gniazda: spód kołnierza, powierzchnia 44 na lokalnym Z=−33,28911847248 mm,
   leży na wierzchu sklejki. Zachowano wspólny układ XY z kołami.
4. Podpory: ich końce zatrzymują się przed profilami z zadanym luzem,
   domyślnie 2 mm. Przy głębokości 500 mm długość podpory wynosi 430 mm.

Położenia w 2023 używają jawnych lokalnych parametrów RP_PolozenieX/Y/Z,
zależnych od polskich parametrów sceny. Sprawdzono rzeczywisty ruch po zmianie
parametrów. Lokalne parametry mają komentarz, że nie należy zmieniać ich ręcznie.

Nowe wycięcia powstają ze zregenerowanego prostopadłościanu w tymczasowej części,
kopiowanego jako odejmowanie do profilu. Tymczasowa część jest usuwana.
Reset SizeBox niezregenerowanej ujemnej operacji w obróconym profilu dawał
nieprawidłowe wymiary i przesunięcie przekroju; zachowano dowód nieudanej próby.

## Parametry i wymiary

12 polskich nazw ASCII zapewnia stabilne ścieżki wyrażeń; komentarze zawierają
pełne polskie znaki. Nazwy i opisy mają jedno źródło: PARAMETERS_PL.
Stare nazwy usunięto dopiero po sprawdzeniu zmiany wymiarów i powrotu.
600 × 500 × 350 mm oznacza obrys sklejki zamkniętej skrzyni: korpus 235 mm
+ pokrywa 115 mm, bez kół, podpór i wystających okuć. Rozsunięcie pokrywy
służy prezentacji, nie zmienia wymiarów cięcia. 115 mm pozostaje zachowanym
podwyższonym wariantem; ogólna polityka płytkiej pokrywy nadal obowiązuje.

## Dowody

PASS: testy reguł i pełny harness przed CAD.
PASS natywny: docelowe wymiary, zmiana L/D/B/H, odsunięć uchwytów/zamków/zawiasów,
luzu i rozsunięcia pokrywy, powrót oraz kontrola po usunięciu starych nazw.
Każdy przebieg: pozycje/orientacje 72 elementów, wymiary płyt/podpór,
24 płaszczyzny narożników, 4 gniazd, 4 luzy podpór, 4 pary zawias–profil bez kolizji.
Końcowy odczyt potwierdził 12 nazw i komentarzy, 20 pozycji wycięć i 24 długości profili.
Przy operacjach „przez część” sprawdzono pozycję parametryczną i rzeczywiste
położenie w płaszczyźnie przekroju; automatyczne przesunięcie kotwy wzdłuż
normalnej nie jest przesunięciem konturu otworu.

Dowody prywatne: `artifacts/scene14-repair-20261026/native-05/result.json`
oraz `final-readback.json` w katalogu nadrzędnym. Wcześniejsze błędy zachowane.
NOT RUN: zapis/ponowne otwarcie (zakaz użytkownika), odbiór wizualny i produkcyjny.
Kontrole nie stanowią ciągłej blokady wszystkich kolizji podczas dowolnej edycji tabeli.
