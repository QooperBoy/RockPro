# EB-L630U — uchwyty na przeciwległych ścianach

Nowy domyślny układ użytkownika: po dwa H7159 na lewej i prawej ścianie,
prostopadłych do tylnej ściany zawiasów. Łącznie cztery, dwie osoby mogą
podejść do przeciwległych boków. Środki D/4 i 3D/4, wysokość B/2.

Jawna opcja konstruktora: handles_per_wall=1, po jednym wyśrodkowanym
na każdej z tych ścian, łącznie dwa. Zmiana liczby wymaga generacji nowej
kopii; zmiana gabarytu przesuwa istniejące uchwyty przez natywne wyrażenia.

Kierunki montażu: kołnierze na X=0 i X=L, normalne -X/+X, uchwyty pionowe.
Macierze są obrotami właściwymi; geometria katalogowa nie jest skalowana
ani odbijana. Wykorzystano dwa istniejące całe zespoły i dwa świeże eksporty
H7159, przypięte SHA256 do zmierzonego datum. Każdy ma 13 części.

core_case/handle_rules.py sprawdza znany kołnierz 161 × 107 mm, zapas
35 mm od profili i 20 mm pomiędzy kołnierzami. Brak miejsca daje odmowę,
a nie automatyczne zmniejszenie liczby lub geometrii. Testy sprawdzają obie
ściany, kierunki, symetrię i zależność od gabarytu oraz opcję pojedynczą.

Wykonawca: scripts/prototype_epson_case.py z --handles-per-wall 1 lub 2,
--depth-mm, --handle-asset i --handle-datum. Domyślnie PLAN ONLY, wykonanie
wymaga --native, przypiętego raportu pełnej wersji v3 i nowego katalogu.
Wszystkie importy kończą się przed ponownym związaniem wyrażeń. Parametry
resizingu nie przepisują kotew. Poprzednie modele i assety są zachowane.

Instrukcje agenta zaktualizowano w obu AGENTS.md i docs/CASE_DEFAULTS.md.
Wybór liczby jest konfiguracją generatora, nie nowym polem działającej DLL.
Wycięcia pod wpuszczane uchwyty, mocowania i nośność pozostają oddzielnym
etapem; kontrola obrysów nie jest pełnym audytem kolizji ani zgodą produkcyjną.

## Wyniki natywne

PASS: sześć etapów zmiany parametrów i zapisu/otwarcia dla obu wariantów.
Główny model: projekty/Epson_EB-L630U/Prototyp_03_uchwyty_boczne/,
650 × 500 × 381 mm, cztery uchwyty, 66 głównych wystąpień.
Opcja pojedyncza: projekty/Epson_EB-L630U/Opcja_uchwytow_1_na_sciane/,
650 × 420 × 381 mm, dwa uchwyty, 64 główne wystąpienia.
Każdy ma własny prototype_report.json; zachowano źródłowy model i asset.
Zmiany AGENTS.md dotyczą przyszłych generacji, nie historycznych raportów.

PASS: rzeczywisty widok prawego i lewego boku wariantu czterech uchwytów;
podglad_przod_prawa.png i podglad_tyl_lewa.png są obok modelu. Wariant z
jednym na ścianę ma osobny podgląd. Po kontroli zapisano pliki, odczytano
ponownie kotwy/obroty i sprawdzono hashe oryginałów. Główna wersja pozostaje
otwarta w IronCAD, opcję pojedynczą zamknięto po zapisaniu.
PASS pełny harness: artifacts/verification/20261024T173117882904Z/results.json.
Nie zmieniano działającej DLL ani bazy klienta.
