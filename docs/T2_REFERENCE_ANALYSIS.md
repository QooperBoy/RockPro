# T2 — analiza rodziny i plan parametryzacji

Stan: 26.10.2026. Wykonano odczyt wzorca i mapowanie, bez zmiany geometrii.
To osobna rodzina transportowa do miksera z wyjmowanym rackiem, czapką i klapą.
Nie jest jeszcze wykonywalnym szablonem ani źródłem zatwierdzonego BOM.

## Zakres i dowody

Przejrzano mail Temat II, wszystkie trzy PDF (8 stron łącznie), pięć zdjęć
otwartego/zamkniętego wzorca oraz zapisany model z T2.zip.
Dokumentację i przekrój obejrzano jako renderowane arkusze, nie tylko tekst PDF.

W istniejącym IronCAD 2027 wykonano odczyt SDK na nowej ukrytej kopii.
Wynik: 449 węzłów, w tym korzeń sceny, 113 zespołów i 335 wystąpień części.
335 odczytanych obrysów jest liczbowo poprawnych; nie jest to kontrola pasowania.
Zachowano macierze części oraz historię cech. Pełną historię gotowych okuć
zachowano jako dowód źródłowy; nie proponuje się przebudowy ich wnętrza.

Aktywny dokument użytkownika, GUID i flaga Modified przed/po są identyczne.
Własna kopia została zamknięta, a tymczasowy AddOn usunięty. ZIP, mail,
wypakowane źródła i kopia ICS mają zweryfikowane hashe. Oryginał nie był zapisywany.

Prywatny pakiet lokalny: `artifacts/t2-analysis-20261026/`:

- `T2_ANALIZA.md`: pełna analiza, tabele, rozbieżności i plan.
- `reference_map.json`: przypięte do SHA źródła role wszystkich węzłów,
  pary zamków, kandydaci powiązań wycięć i braki.
- `parts_map.csv`: tabela do filtrowania, bez domniemanej pozycji zakupowej.
- `source_manifest.json`, `native/inventory.json`, `native/result.json`:
  źródła, odczyt i dowód zachowania kontekstu.
- `pdf_text.json`, `render/`: tekst i obrazy dokumentacji.
- `validation.json`: wynik sprawdzeń integralności i kompletności.

Pakiet zawiera dane projektu; pozostaje ignorowany przez Git. Referencje do
ID i ścieżek są ważne wyłącznie razem z hashem tej rewizji. Nie zastępują
UUID/kontraktu przyszłego wykonywalnego szablonu.

## Ustalona budowa

| Obszar | Ustalenie | Konsekwencja |
|---|---|---|
| Główne zespoły | Spód, Klapa, Czapka | Osobne komponenty i ramy złączy |
| Otwieranie | PDF podaje brak zawiasów, zdjęcia pokazują zdejmowanie | Nie narzucać osi zawiasu ani reguły płytkiej pokrywy T1 |
| Rack | Fizycznie wyjmowany, choć zagnieżdżony pod Czapka | Oddzielić własność w drzewie CAD od ruchu i etapu |
| Zamki | 6 par, jednoznaczne zgodne początki ram | 12 głównych połówek, zagnieżdżone zespoły nie tworzą kolejnych kompletów |
| Uchwyty | 3 zespoły: dwa przeciwległe na czapce i jeden na klapie | Zachować wzorzec; opcje nowych wariantów wymagają jawnej liczby/roli |
| Transport | Dwa koła narożne i teleskop | Osobny podgraf obejmujący obróbki i stan wysuwu |
| Profile | 16 części jednej rodziny i 17 drugiej | Nie dublować części i zespołów o identycznej nazwie |
| Płyty zewnętrzne | 13 części jednej grubości | Nie utożsamiać z dziesięcioma płytami szkieletu T1 |
| Wnętrze | Rack, piany, dystanse i asymetryczne podpory | Osobne grubości i reguły, niezależne od grubości poszycia |

Początki ram sześciu par zamków pokrywają się jednoznacznie w granicy 0,01 mm.
To dowód parowania, nie kontroli tolerancji, siły zamknięcia ani montażu.
Liczby części sceny i operacji nie są zakupowym BOM.

## Wycięcia i granice rozpoznania

Zmapowano trzy główne wycięcia uchwytów i dwa dodatkowe płytkie podfrezowania
ich sąsiednich podpór racka. Kontury tych podfrezowań różnią się od otworu
poszycia i między stronami. Model katalogowy potrzebuje więc zestawu celów:
typ części, kontur, rama, głębokość, wariant i rewizja, nie jednego bbox.

Zidentyfikowano po sześć cech górnych/dolnych połówek zamków w płytach,
odciążenia w profilach oraz operacje przy kołach i teleskopie.
Nie wszystkie H Block mają już potwierdzoną semantyczną własność.
Wyeksportowane szkice zamków zawierają FILLET bez pełnej geometrii tych krzywych.
Nie można traktować tego eksportu jako kompletnego neutralnego szablonu.
Przyszły wykonawca musi odczytać pełne krzywe albo kopiować całe szkice
na zweryfikowanych kopiach, zgodnie z możliwościami SDK.

Mapa jest `inventory_draft`, z `executable_template=false` i
`production_approved=false`. Nie rozszerzono allowlisty MCP ani dodatku.
Nie wykonano ruchu uchwytu, automatycznego podążania otworu ani zmiany wymiarów T2.

## Rozbieżności wymagające rozstrzygnięcia

1. Mail źródłowy wprost wskazuje rozbieżne wymiary urządzenia i oczekiwanie
   na pomiar fizycznego sprzętu. Dopasowanie wnętrza pozostaje niepotwierdzone.
2. Oznaczenia uchwytów, zamków, profili i narożników różnią się w PDF i CAD.
   Alias jest kandydatem, nie dowodem zamienności SKU.
3. Kilka formatek klapy/czapki i części racka ma inne wymiary na rysunku
   niż lokalne obrysy CAD. Nie zakładać, że obrys zastępuje kontur; rozstrzygnąć
   rewizję, fazowanie, osadzenie i tolerancje. Szczegóły są w prywatnym raporcie.
4. Podpory racka mają różne grubości stron w CAD, a dokumentacja podaje
   wspólny materiał. Zachować konflikt, nie ujednolicać w generatorze.
5. Dokumentacja wymaga sprawdzenia wycięć kół i teleskopu przy frezowaniu.
   Brakuje zatwierdzonych tolerancji, udźwigu i toru ruchu teleskopu.

## Kolejne zadania według zależności

| ID lokalne | Zadanie | Kryterium następnego przyrostu |
|---|---|---|
| T2-01 | Uzgodnić źródła i warianty materiałów/okuć | Rozbieżności jawnie rozstrzygnięte lub zachowane jako blokery; żadne null nie staje się zerem |
| T2-02 | Kontrakt osobnej rodziny | Spód, czapka, klapa i rack mają stabilne role, ramy oraz dwa jawne złącza; brak sztucznej osi zawiasu |
| T2-03 | Planer wymiarów, profili i formatek | Zewnętrzne wymiary, wnętrze, osadzenia i różne grubości liczone przed CAD; brak ukrytego powiększania |
| T2-04 | Katalog montażowy z wieloma celami | Uchwyty i 6 par zamków wybierają pełne kontury wraz z obróbką płyt/profili/podpór; niepotwierdzone aliasy blokują wydanie |
| T2-05 | Podgraf transportu | Para kół, teleskop i jego obróbki mają wspólne kotwy i kontrole toru; brak automatycznych gniazd kół z T1 |
| T2-06 | Wnętrze i wyjmowany rack | Oddzielny ruch racka od czapki, dostęp do sprzętu, złączy i uchwytów oraz plan wyjmowania |
| T2-07 | Parametryczny prototyp na kopii | Zmiana i powrót wymiarów, pomiar, zapis/otwarcie oraz rzeczywisty widok; źródła i ręczne zmiany zachowane |
| T2-08 | Etapy, BOM i dokumenty | Ten sam graf definiuje CAD/podgląd/obróbki; brak zakupowych pozycji wycięć i podwójnego liczenia okuć |

Można rozpocząć T2-02 i szkielet T2-03 bez pomiaru sprzętu, z jawnym statusem
niepotwierdzonego dopasowania. Nie oznacza to zgody na produkcję.
Sam audyt nie wdraża jeszcze tych ośmiu przyrostów.

## Etapy i architektura

Utrzymać znaczenie dotychczasowych etapów: dane/obliczenia → poszycie → profile
→ narożniki/wzmocnienia → uchwyty → zamknięcia → transport (etap 6)
→ wnętrze/rack → kontrola/wydanie. Kolory etapów służą podglądowi procesu.
W nowym prototypie obowiązuje domyślny zielony materiał; historyczny czarny
wzorzec pozostaje zachowany.

To graf zależności, nie sztywna pętla według numerów. Podfrezowanie pod uchwyt
w podporze wymaga wcześniejszej definicji podpory, choć rack jest prezentowany
później. Plan ma znać wszystkie cele przed montażem. Okucie i jego obróbki
tworzą jedną zmianę, także gdy cele leżą w innych grupach podglądu.
Ukrycie okucia w gotowej skrzyni nie usuwa otworu; cofnięcie operacji to inna
czynność. Reguły wspólne: [ROC-41](ROC41_CUTOUTS_AND_JOINTS.md).

## Wynik weryfikacji

- PASS: natywny odczyt kopii, integralność źródeł, unikalność mapy,
  liczbowe obrysy, sześć par początków ram, zachowanie kontekstu i sprzątanie.
- PASS: offline kontrola mapy i wynik `validation.json`.
- NOT RUN: parametryzacja T2, kolizje/luzy mechaniczne, demontaż w CAD,
  nowy interfejs, animacja, udźwig oraz dokumenty produkcyjne.

Pełny harness/build nie był wymagany: w tym przyroście nie zmieniono kodu
produktu, geometrii ani instalacji. Dokumentacja podlega audytowi repozytorium.
Stała dostępność dodatku RockPro pozostaje osobnym niezakończonym zadaniem;
odczyt przez tymczasowy most nie dowodzi autostartu zarządzanego dodatku.
