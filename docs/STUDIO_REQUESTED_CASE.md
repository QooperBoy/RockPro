# Studio — próbna skrzynia Penn / Adam Hall, 28.10.2026

Recepta `penn-30-rubber-feet-v1` jest koncepcją rozmieszczenia, nie dopuszczeniem
nowych SKU do produkcji. Osobny draft zachowuje starsze projekty. Wnętrze:
800 × 650 × 800 mm; zdejmowane wieko 115 mm; zielona sklejka 9,8 mm.

- H2026: 4 kompletne uchwyty, po dwa na przeciwległych bokach wieka.
  Zachowana siatka źródłowa; cena H2026Z jest jawnym założeniem wariantu.
  Przenoszenie korpusu przez zdejmowane wieko i zamki wymaga odbioru nośności.
- C1339/30Z: 8 narożników; offset 30 mm. Nie podstawiaj kątownika EG-0113 35 mm.
- 944/537/10MOL3K: 4 zamki, po dwa z przodu i z tyłu na złączu.
  Zachowany kod Excela; alias producenta L944/537/10MOL3K.
- D0536/07K: 2 wentylacje na przeciwległych bokach. Brak ceny.
  Gabaryty 178 × 127 mm z rysunku /07Z do potwierdzenia dla /07K.
- 4903M8AH: 8 nóżek Ø20 × 9 mm; do zakupu jedno opakowanie, nie osiem.

Poza uchwytem modele są uproszczonymi bryłami wymiarowymi, nie CAD-em producenta.
Promień kopuły narożnika i nominalne wysunięcie 6 mm są założeniami podglądu;
rzeczywisty prześwit nóżek trzeba zmierzyć. Profil 30 × 30 mm nie ma dobranego SKU.
Górne odcinki są przerwane przy obrysach zamków z rezerwą 5 mm.
Nie zatwierdzono wycięć, profilu zamknięcia, osi podziału miski ani dokładnego montażu.
Kontrola końcowa ujawnia ten stan, a `production_approved` pozostaje `false`.

Zasoby lokalne odtwarza `scripts/build_requested_case_assets.py` (Python z Pillow).
Nie zmienia on CAD źródłowego. Indeks obrazów/siatek ma SHA-256, ładowany jest
wyłącznie z `artifacts/studio-requested-parts/images`; nie publikować całych artifacts.
Katalog firmowy zachowuje wszystkie rekordy; definicje montażowe o tych samych
ID nie są drugi raz dopisywane jako pozycje tylko do przeglądania.

`scripts/export_requested_case.py <folder>` zapisuje nowy draft, JSON oraz dane
kontrolne, po kopii SQLite. `--refresh` aktualizuje wyłącznie wskazany wcześniej
draft z kontrolą rewizji; poprzednie rewizje i pozostałe projekty zostają zachowane.
Excel to snapshot z ilościami, opakowaniami i cenami; nie jest importem zmian do 3D.
Ceny nie mają określonej waluty ani netto/brutto, więc suma jest tylko częściowa.

## Przygotowanie natywne 2027 — niepełny transfer

`artifacts/requested-native-20261028/body-01` zawiera dziesięć natywnych paneli
z parametrami tego draftu; pomiar, zmiana wymiarów oraz zapis/otwarcie PASS.
To korpus bez okuć i wycięć, nie ukończona skrzynia.
`scripts/native/ExtractRequestedHandle2027.cs` wyodrębnia tylko kompletny H2026
z przypiętego źródła M03. Próba `handle-02` potwierdza dwie bryły po ponownym
otwarciu, niezmienność źródła i wszystkich wcześniej otwartych dokumentów.
Pierwsza próba miała błędny tryb współdzielenia pliku podczas liczenia SHA;
zachowana jest jako FAIL, mimo że sam eksport i odczyt brył się powiodły.
Nie oznacza to zatwierdzenia bazy montażowej ani szablonu wycięcia H2026.

Pozostałe cztery SKU wymagają modeli producenta. Portal 3D ContentCentral
żąda zalogowania; nie zastępować pobrania STEP geometrią podglądu eDrawings.
Pełny transfer pozostaje zablokowany do dostarczenia modeli i potwierdzenia
konturów montażowych. Raport `TRANSFER_STATUS.json` obok folderu projektu
zachowuje ten status; plik korpusu ma jawne oznaczenie `KORPUS_BEZ_OKUC`.
