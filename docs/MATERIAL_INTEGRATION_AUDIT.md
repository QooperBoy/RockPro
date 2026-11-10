# ROC-27 — WoodLAB PLAN i technologia rozkroju

## Wynik lokalnego rozpoznania 24.10.2026

W rejestrach zainstalowanych aplikacji HKLM x64/x86 i HKCU potwierdzono IronCAD
2027 oraz jego składniki. Nie znaleziono wpisu WoodLAB PLAN, woodLAB ani innego
optymalizatora. To wynik dla tego komputera, nie dowód braku licencji klienta.
Nie odczytywano kluczy licencyjnych ani nie zmieniano konfiguracji aplikacji.

Próba natywnego połączenia trzech zleceń z resztką: NOT RUN, ponieważ brak
zainstalowanego/udostępnionego PLAN i potwierdzonego profilu importu. Nie zastąpiono
jej wymyślonym wynikiem optymalizacji. Parametry rzeczywistej piły/CNC są nieznane.

## Potwierdzone możliwości producenta

Oficjalny opis woodLAB.eu:
https://www.woodlab.eu/En/cutting-optimizer-software-for-wood-material-and-panel-for-saw-machine-and-saw-beam.asp
Opisuje przepływ BOM CAD do listy TXT/ASCII, import/eksport Excel/ASCII,
rozdzielenie materiału i grubości, rzaz, kierunek usłojenia, przycinanie,
raporty i postprocesory. Nie jest to specyfikacja konkretnego API ani dowód
uprawnień zainstalowanej licencji.

Oficjalny opis woodLABPLAN:
https://www.woodlabplan.eu/En/properties-history-store-saw-cutting-optimizer-report.asp
Opisuje magazyn i odzysk resztek oraz import danych przez mapowania ASCII/Excel.
Sprawdzono 24.10.2026. Nie zakładamy zgodności wszystkich opcji ze starszą licencją.

## Decyzja integracyjna

Pierwszy wybór: adapter do istniejącego PLAN przez potwierdzony na stanowisku
profil ASCII/Excel. Nie kupować kolejnej licencji i nie wybierać zewnętrznego
solvera przed próbą tych możliwości na faktycznej instalacji produkcyjnej.
Na tym stanowisku implementować neutralny kontrakt, walidatory i plan prób;
nie generować niepotwierdzonego formatu maszynowego ani G-code.

## Kontrakt pośredni materiałów v1

- Źródło: project_id, revision_id, model_sha256, bom_sha256, source_row_id.
- Formatka: material_id, thickness_mm, length_mm, width_mm, quantity, grain_axis
  (X/Y/free), rotation_allowed oraz identyfikowalne przypisanie do zlecenia.
- Materiał zatwierdzony jest identyfikatorem kartoteki; nazwa/kolor CAD to osobne
  surowe pole. Nie zastępuje go przybliżona nazwa ani RGB sklejki.
- Płyta/resztka: stock_id, material_id, thickness_mm, length_mm, width_mm,
  available_quantity, grain_axis, is_offcut. Nie sumować rezerwacji z dostępnością.
- Technologia: jawne kerf_mm, cztery marginesy trim_mm, typ dopuszczalnych cięć,
  profil maszyny/postprocesora i wersja. Brak wartości pozostaje null i blokuje
  produkcyjny rozkrój. Nie przyjmujemy 0 jako fikcyjnego braku rzazu.
- Wynik solvera: plan_id, hashe wejść/profilu, elementy z source_row_id i numerem
  wystąpienia, stock_id i współrzędne/orientacja, resztki, odpad, cięcia i diagnostyka.
  Niezależna kontrola: obrys, nakładania, rzaz, marginesy, grain i pełny bilans ID.

## Próba do wykonania po uzyskaniu dostępu

Trzy jawnie wersjonowane zlecenia, wspólny materiał/grubość i jedna zinwentaryzowana
resztka. Najpierw kontrola importowanych ilości, potem PLAN, odczyt wyniku i bilans.
Zmiana rewizji jednego zlecenia ma unieważnić plan/rezerwacje bez naruszenia innych.
Nie rezerwować ani nie zamawiać materiału na podstawie szkicu bez zatwierdzenia.

## Braki do rozstrzygnięcia rano

Wersja/licencja PLAN i dostęp do instalacji klienta; próbka eksportu/importu;
formaty płyt i surowe kartoteki materiałowe; rzaz/marginesy; wymagany typ cięć
oraz rzeczywisty postprocesor. Dopiero to rozstrzyga, czy potrzeba opcji licencyjnej.

Dowód lokalnej instalacji: artifacts/overnight-20261024/material-environment.json.
