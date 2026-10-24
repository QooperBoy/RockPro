# Prototyp EB-L630U — 24.10.2026

HISTORYCZNY: proporcja pokrywy została odrzucona przez użytkownika.
Obowiązuje docs/CASE_DEFAULTS.md i Prototyp_02_plytka_pokrywa.
Poprzedni PASS dotyczył pomiarów, nie akceptacji konstrukcji.

Nowy model w workspace `projekty/Epson_EB-L630U/Prototyp_01/`:
`RockPro_EB-L630U_650x500x708.ics`. Oryginały T_1 i poprzednie wersje są zachowane.

## Parametry i pochodzenie

- Obrys urządzenia 440 × 339 × 136 mm według
  [Epson](https://www.epson.eu/en_EU/products/projector/professional/eb-l630u-projector/p/31706).
- Obrys sklejki 650 × 500 × 708 mm; korpus 300 mm, pokrywa 408 mm,
  sklejka 9,8 mm, szczelina złącza 8,63 mm, rozsunięcie prezentacji 0 mm.
- Kolor wszystkich dziesięciu płyt i dwóch podkładek RGB(64,128,128), #408080.
- Minimum pokrywy 408 = 3 × 136 mm dla obecnych okuć. H2026 nie jest zamontowany.
  Walidator generatora odmawia zbyt niskiej pokrywy. Bezpośrednia edycja tabeli
  parametrów CAD wymaga ponownej walidacji; notatka parametru opisuje minimum.
- Wzorzec T_1 zachowuje wygląd, typy okuć i rodzinę konstrukcyjną. Jego płyty
  mają obrys 914 × 602 mm. Nowy prototyp jest mniejszym wariantem tej rodziny,
  wykonanym ze sprawdzonej parametrycznej wersji v3 i jej przypiętych assetów.

Wolny obrys korpusu przed dodaniem wnętrza wynosi 630,4 × 480,4 × 290,2 mm.
Sprawdzono miejsce na obrys urządzenia z umownymi dodatkami: 30 mm na każdą
stronę, 50 mm pod urządzeniem i 20 mm nad nim. Pianka ani model projektora nie
są narysowane; jest to kontrola gabarytu, nie gotowe gniazdo transportowe.
Wysokość 708 mm nie obejmuje kół ani wystających okuć.

## Rozmieszczenie i sprawdzenia

Pierwsza próba wykryła nakładanie konserwatywnych obrysów obu uchwytów H7159
z dolnymi połówkami zamków o około 16,78 mm w Z. Uchwyty obniżono z połowy
wysokości korpusu do `0.4*RP_BaseHeight`. Dla korpusu 300 mm ich kotwy mają
wysokość 120 mm. Rozstaw X i symetria pozostają parametryczne.

PASS: sześć etapów natywnych — wariant, zmiana samych parametrów, powrót,
zapis/otwarcie, zmiana po otwarciu, powrót po otwarciu. Wariant próbny:
700 × 550 mm, korpus 330 mm, pokrywa 440 mm, rozsunięcie 50 mm.
Kontrola obejmuje 10 płyt, 32 profile/wzmocnienia i 14 elementów transportowych,
kotwy wcześniejszych okuć, symetrię uchwytów, parowanie zawiasów i kolor płyt.

PASS: brak nieoczekiwanych nakładań konserwatywnych obrysów gotowych uchwytów,
zamków, zawiasów, kół i gniazd w wariancie docelowym oraz powiększonym.
Celowo parowane połówki tego samego zamka/zawiasu wyłączono z tej kontroli.
Nie jest to pełny test kolizji BRep: nie obejmuje wycięć w drewnie, styków
profili, zakresu obrotu zawiasów, skrętu kół ani certyfikacji piętrowania.

PASS: rzeczywisty podgląd przód/bok i tył w IronCAD; zapisano PNG obok modelu.
Model pozostawiono otwarty do odbioru. DLL dodatku nie była przeładowywana.

PASS: 11 testów reguł pokrywy/profili/transportu oraz pełny harness:
`artifacts/verification/20261024T153411808927Z/results.json`.
Pierwsze ręczne wywołanie testu pokrywy wymagało dodania katalogu mcp do
PYTHONPATH, zgodnie ze sposobem uruchomienia używanym przez harness.

## Powtórzenie i kolejne kroki

`scripts/prototype_epson_case.py` przyjmuje `--source`, `--receipt`,
`--output-dir` oraz jawne `--native`. Bez ostatniej flagi pokazuje tylko plan.
Wymaga zgodnego hasha i raportu `full_case_transport_v3`, tworzy nowy katalog,
używa blokady jednego wykonawcy i sprząta wyłącznie własne dokumenty.
Nowa reguła uchwytów i pełne pomiary są w lokalnym `prototype_report.json`.
Pierwsza nieudana kopia jest zachowana w prywatnych artifacts, poza dostawą.

Kolejno: potwierdzić montaż H2026, dobrać i narysować wnętrze/piankę,
wykonać wycięcia okuć i szczegóły profili/mocowań, a następnie zintegrować
pełny generator z panelem. Prototyp nie ma zatwierdzenia produkcyjnego.
