# ROC-28/29 — dane historyczne i import BOM

## Dostępne źródła i brakujące dane

Indeks lokalnych katalogów AI_CAD, Projekt, Modele i Prezentacje obejmuje
3 wiadomości EML i 5 PDF; nie znaleziono arkuszy XLS/XLSX/CSV. Zachowana baza
wdrożenia ma 5 kart projektów. Liczba kart nie dowodzi zakończenia zleceń.
Nie potwierdzono pięciu zakończonych zleceń wielosztukowych z BOM, rewizją,
datami, zużyciem płyt, rzeczywistym rozkrojem, kosztem i transportem.

| Pole benchmarku ROC-28 | Stan |
| --- | --- |
| Identyfikator i potwierdzenie zakończenia zlecenia | brak potwierdzonej piątki |
| Ilość skrzyń, rewizja i zakupowy BOM | pojedyncze źródła, brak pełnego zestawu |
| Rzeczywisty rozkrój i zużycie płyt/resztek | brak |
| Cena, waluta, data ważności, MOQ/opakowanie, dostawa | brak kompletnego cennika |
| Rzeczywisty koszt i transport | brak |

Nie uzupełniamy tych pól wartościami fikcyjnymi. Wyciągnięta z PDF lista
formatek nie jest zatwierdzonym BOM: nadal nieznane są potwierdzone indeksy
materiałów, grain, technologia i terminy. Szczegóły indeksu i liczników baz
są prywatnie w artifacts/overnight-20261024/historical-*.json.

## Kontrakt implementacji ROC-29

`mcp/material_service.py` przyjmuje plik JSON v1 w `Integracja/imports`, do 2 MB,
bez zależności od CAD. `preview_bom_file` zwraca hash źródła. Operator przekazuje
go oraz odczytaną rewizję do `import_bom_file`; brak automatycznego ponowienia CAS.
Oryginalne bajty i dokument są niezmienne w tej samej bazie SQLite co karty.

Dokument ma project_id, source_revision, model_sha256, units=mm, case_quantity,
scope (`source_input` lub `synthetic_test`), rows i approval. Approval zawiera
status=approved, reference, by i content_sha256 obliczony kanonicznie z dokumentu
bez approval. To zachowane oświadczenie importera, nie uwierzytelniona zgoda
produkcyjna. Wynik zawsze ma production_approved=false.

Wiersz: id, material_id, finish, technology_id, thickness_mm, cut_length_mm,
cut_width_mm, per_case_quantity, grain_axis (X/Y/free), rotation_allowed,
required_date (ISO), dimension_source=technology. Nie przyjmujemy wymiarów
cięcia z obrysu zespołu. Identyfikatory są techniczne ASCII; nazwy handlowe
pozostają w źródłowym katalogu, nie służą do niejawnego scalania materiałów.

Ponowienie source_revision z identyczną treścią zwraca istniejący kwit; zmiana
treści pod tym samym oznaczeniem jest błędem. Nowa rewizja zastępuje bieżące
zapotrzebowanie projektu, zachowując historię. Powtórzenie starego importu
nie przywraca go jako bieżącego. Import dezaktualizuje etapy materiałów/produkcji.

`aggregate_bom_demand` czyta spójnie ostatnią rewizję każdego zlecenia.
Ilość wynosi per_case_quantity × case_quantity, z pełnym śladem każdego wiersza.
Grupuje tylko identyczne materiał, wykończenie, grubość, technologię, grain,
obrót, wymiary cięcia i dokładny termin. Nie miesza syntetycznych i rzeczywistych
danych. Wynik i powiązania z BOM/modelami mają hash do kontroli dalszych etapów.

PASS: siedem testów izolowanej SQLite/MCP obejmujących ponowienia, zmianę rewizji,
CAS, zmianę pliku po podglądzie, ilości/grupy i odrzucenie obrysu CAD.
NOT RUN: zatwierdzony wielozleceniowy import klienta i odbiór produkcji.
