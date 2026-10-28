# Parametry osprzętu w kopii Studio T1 — 28.10.2026

## Aktualna korekta drzewa: Wieko 1 i Podstawa

Na późniejsze polecenie konstruktora scalono stały korpus z podstawą. Aktualna
kopia ma dokładnie **Wieko 1** i **Podstawa**. Nie ma Korpusu 1/2 ani Wieka 2.
Drugie wieko powstaje dopiero przy rzeczywistej drugiej pokrywie/klapie.
Płyty boczne, rama korpusu i dolne połówki okuć należą do Podstawy; płyty pokrywy,
jej osprzęt i górne połówki okuć do Wieka 1. Stałe ID i etapy są zachowane.

PASS w API29: 41 parametrów, 72 wystąpienia, 48 obróbek, sześć prób przed i po
zapisie/otwarciu oraz powrót. Źródło i wcześniej otwarte dokumenty zachowane,
tymczasowy dodatek usunięty. Wynik jest otwarty w IronCADzie.
Pełna regresja: PASS, 12 kroków, `artifacts/verification/20261028T103109840624Z/`;
9 testów migracji obejmuje też scalenie korpusu z podstawą bez zmiany parametrów.
Dowody: `artifacts/t1-wieko-podstawa-20261028-01/result.json` i `request.json`.
Aktualny plik: `baseline-restored-12a9b7a668774473ab541c29c80a0f9f.ics`
w tym katalogu, SHA256
`d954255197192c766805d09ecf2f7de9bcc6efdd1fd8cb914883ed57eb70c13d`.
CLI `parameterize_studio_t1.py --request <poprzedni-request> --receipt <kwit>
--output <nowy-katalog> --pid <PID> --run` przenosi zapisaną, zidentyfikowaną
kopię bez zmiany parametrów. Kontrola wejścia wiąże hash pliku, grupy i ID części.

Poniższe szczegóły pierwszego odbioru zachowano jako historię; nazwy Korpus 1/2
nie są już obowiązującą regułą.

Wdrożono standard ACCESSORY_PARAMETER_RULES.md w nowej kopii wskazanego przez
użytkownika modelu `baseline-restored-8c6cb82ab5bb499b82e47d8788706a14.ics`.
Źródłowy plik, otwarte wcześniej dokumenty, drafty Studio i baza projektów
pozostają zachowane. Ta migracja nie jest zmianą kontrolek kreatora Studio.

## Co można zmieniać w tabeli IronCAD

| Grupa | Parametry i znaczenie |
| --- | --- |
| `RP_Zawiasy_*` | Rozstaw w osi X na tylnej ścianie; marginesy od lewego i prawego brzegu do zewnętrznego skraju całego zawiasu. Obie połówki i obróbki zmieniają położenie razem. |
| `RP_Uchwyty_*` | Rozstaw w osi Y na dwóch bocznych ścianach: „lewy” oznacza pierwszy brzeg, czyli przód skrzyni, „prawy” oznacza tył. Wspólna wysokość kotwy uchwytu od dolnego brzegu bocznej płyty. |
| `RP_KolaX_*` | Osobny rozstaw kół w osi X; marginesy lewy/prawy do obrysu gotowego koła w przypiętej orientacji. |
| `RP_KolaY_*` | Osobny rozstaw kół w osi Y; marginesy od przodu/tyłu. Górne gniazda i ich otwory wynikają z punktów osadzenia odpowiadających kół, z uwzględnieniem odsunięcia koła skrętnego. |

W każdej grupie `TrybOdBrzegow` jest bezwymiarowy:

- **1**: sterują `MarginesLewy` i `MarginesPrawy`, a rozstaw jest wyliczany.
- **0**: sterują `RozstawZadany` i `PrzesuniecieSrodka`, a marginesy są wyliczane.

`PrzesuniecieSrodka` mierzy się od połowy gotowej ścianki wzdłuż osi grupy.
Pola z `Rzeczywisty`/`Rzeczywista` są wynikami z równaniami — nie zastępować ich
liczbą. W tabeli pozostają oba zestawy wejść, ale działa tylko wskazany trybem.
Wartości w nieaktywnym zestawie nie sterują geometrią.

`RP_Uchwyty_TrybWysokosci`: **0** to `WysokoscOdDolu` w mm; **1** to
bezwymiarowy `UdzialWysokosci` bocznej płyty. Symetria przeciwległych ścian
pozostaje zachowana. Przemieszczenia TriBallem nie zastępują parametrów.

Podpory kół podążają za rzędami X; ich początek i długość w Y wynikają z położeń
obu kół i istniejących zapasów montażowych. Na górze tego wariantu występują
gniazda, a nie osobne listwy pod koła. Profile obwodowe podążają za gabarytami.

Układ ma stałą topologię: 2 zawiasy, 2 uchwyty na każdą z dwóch ścian,
4 koła i 4 gniazda. Zmiana liczby wymaga nowego planu i przebudowy — nie ma
fikcyjnego parametru, który zmienia wyłącznie liczbę w tabeli.

## Drzewo i geometria

Pierwsza kopia miała `Korpus 1` (korpus), `Korpus 2` (pokrywa) i `Podstawa`.
Koła/podpory i dolna płyta są w podstawie; gniazda i górne narożniki w pokrywie.
Etapy procesu pozostają metadanymi części, nie grupami nadrzędnymi CAD.
Historia obróbek pozostaje w obrabianych płytach/profilach.

Wnętrze zachowano: **600 × 500 × 800 mm**, pokrywa **115 mm**, sklejka **9,8 mm**.
Wartości początkowe: rozstaw zawiasów 319,6 mm, uchwytów 259,8 mm,
kół X i Y po 319,6 mm; wysokość kotwy uchwytu nad dolnym brzegiem płyty 362,708 mm.
Koło i gniazdo mają różne kotwy: rozstaw punktów osadzenia na górze nie musi
być identyczny z rozstawem osi mocowania kół.

Nie zmieniano konturów źródłowych wycięć ani wnętrza katalogowych okuć.
Test ich położeń nie jest potwierdzeniem nowego wymagania pełnego licowania
i zakończenia profilu przy zewnętrznym kołnierzu zawiasu; to osobny odbiór.

Preflight migracji kontroluje przypiętą recepturę, dodatnie wymiary,
prześwity i obrysy okuć/gniazd/podpór. Nie jest stale działającym monitorem
kolizji przy dowolnej ręcznej edycji tabeli IronCAD. Odbiór produkcyjny pozostaje
po stronie konstruktora.

## Dowody

- Odczyt SDK kopii źródła: 269 węzłów, brak błędów, bez zapisu/zmiany źródła.
- Migracja: 41 parametrów z polskimi komentarzami; 72 wystąpienia i 48 obróbek.
- Native PASS: margines zawiasów, tryb rozstawu zawiasów, uchwyty z wysokością,
  koła X, koła Y, gabaryty z proporcjonalną wysokością uchwytów. Te same sześć
  prób po zapisie i ponownym otwarciu, bez naprawczego odtwarzania powiązań.
- Native PASS: powrót, końcowy zapis/otwarcie, rzeczywiste wartości 41 parametrów,
  pozycje/obroty części i obróbek, długości profili i obrysy płyt.
- PASS: kontrola obrazu eksportowanego z końcowego modelu.
- PASS: zachowane źródło i 11 wcześniej otwartych dokumentów; własny tymczasowy
  dodatek usunięty, pozostała liczba wpisów 0.
- PASS: pełny harness, 12 kroków, `artifacts/verification/20261028T101758157247Z/`.
  Nowych 8 testów obejmuje tryby, osie, wycięcia, niezmienność, odrzucanie
  kolizji i niezgodnego źródła. Kompilacja natywnego wykonawcy również PASS.
  Wcześniejsze próby harnessu są historyczne: sandbox blokował localhost,
  następnie poprawiono inicjalizację ścieżki importu nowego testu.

Prywatne dane: `artifacts/accessory-survey-20261028/` i
`artifacts/t1-accessory-parameters-20261028-01/`; kwit `result.json` podaje
dokładny plik i SHA. Końcowy plik to
`baseline-restored-cfa082ca9f514daca122739a786f3c79.ics`, SHA256
`d2f62dd13329d72e827be2a41dfea6dd131257f4d2f9f349ff55b89eb72e2106`.

Kod: `accessory_parameters.py`, `scripts/parameterize_studio_t1.py` oraz tryb
`accessory-update` w `scripts/native/StudioCad2027.cs`. CLI wymaga istniejącego
PID 2027, przypiętego requestu i inwentarza z tego samego modelu. Zapisuje nowy
katalog; `--run` uruchamia jednego wykonawcę SDK. Nigdy nie nadpisuje wejścia.
