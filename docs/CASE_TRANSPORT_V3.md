# Zawiasy, koła i gniazda — pełna skrzynia v3

Kontynuacja ROC-17 po [profilach v2](CASE_PROFILES_V2.md). Model użytkowy powstaje
na nowej kopii, bez zmiany poprzednich wersji. Zachowano siedem parametrów sceny
i osobny kontrakt pełnej skrzyni; stary adapter szkieletu i DLL pozostają bez zmian.

## Zakres wykonania

`core_case/transport_rules.py` definiuje dwie pary 270836 (góra/dół), cztery całe
zespoły kół, cztery gniazda oraz dwie nowe podkładki drewniane pod koła.
`scripts/extend_case_transport.py` przyjmuje przypięty hash v2, raport, jawny
katalog eksportów, szablon płyty i nowy katalog wyjściowy. Domyślnie PLAN ONLY;
`--native` wykonuje operację. Wymagane są źródłowe dane, nie dopasowanie po nazwie.

Natywne części eksportowano ze świeżej kopii zapisanej rewizji Epson. Wybrano
korzenie fizycznych połówek zawiasu, nie pusty zespół 2643 i nie B1930.
Ogólna nazwa zespołu koła Assembly1 nie jest potwierdzonym SKU. Jawnie pozostaje
`wheel_sku=null`, bez podawania nośności czy zgody zakupowej.
Prywatne eksporty, identyfikatory i surowe pomiary są w
`artifacts/hinge-transport-20261024-01/`.

## Bazy i reguły

- Zawiasy zachowują współosiowość połówek oraz symetrię całych obrysów w X.
  Kotwy są względem tylnej ściany i złącza korpusu/wieka. RP_DisplayGap rozsuwa
  górne połówki z wiekiem; nie jest symulacją obrotowego otwierania.
- Koła montowane są w siatce z odsadzeniami 150 mm w X i 100 mm w Y.
  Lewe i prawe zespoły mają właściwe obroty; nie odbija się geometrii ani nie
  skaluje istniejących części. Dwie podkładki mają 120 mm szerokości, 18 mm
  grubości i długość RP_Depth − 40 mm. Ich górne płaszczyzny leżą na spodzie dna.
- Natywny odczyt walca bieżni: promień 50 mm, rzeczywista oś i położenie w części
  oraz macierz względem zespołu. Z tego wyprowadzono punkt podparcia koła,
  uwzględniając mimośród 36 mm względem płyty montażowej. Cztery punkty mają
  wspólną wysokość −150,1 mm względem spodu skrzyni i symetrię X/Y.
- Gniazda źródłowe PN-W0968Z zawierają część 38083. Zmierzona spodnia płaszczyzna
  kołnierza ma w tym assetcie ID 44 oraz własną bazę montażową.
  Jej rzeczywiste wierzchołki i zorientowana normalna są sprawdzane na wysokości
  górnej płyty. Kotwy XY gniazd odpowiadają punktom podparcia kół, nie środkom
  obrysów całych zespołów.

Zbieżność XY nie jest potwierdzeniem mechanicznego pasowania podczas piętrowania.
Kieszenie/wycięcia w drewnie, dobór mocowań, nośność, skręt kół, kolizje i wysokość
piętrzenia pozostają poza tym przyrostem. Produkcja i stacking-fit są false.

## Sprawdzenia

Testy reguł obejmują współosiowość połówek, ruch rozsuniętego wieka, symetrię
czterech punktów podparcia, wspólną płaszczyznę gruntu, rejestrację XY gniazd
i odmowę błędnego promienia lub odwróconego kołnierza. Oczekiwania są obliczane
niezależnie od planu.

Wykonawca kontroluje rozmiary i macierze wewnętrzne wszystkich dodanych gotowych
części, bieżnię i płaszczyzny gniazd, poprzednie kotwy oraz przekroje profili.
Próba natywna obejmuje wariant, zmianę parametrów, powrót, zapis/otwarcie oraz
zmianę samych parametrów po otwarciu. Własne dokumenty zamykane są również po
błędzie; nieoczekiwane zmiany zachowywane są w nowej kopii. PASS powstaje dopiero
po sprzątaniu, kontroli hashy i niezmienności aktywnego dokumentu.

Model i końcowy raport: workspace
`projekty/Skrzynia_2000x3000x4000/Wersja_03_zawiasy_kola_gniazda/`.

PASS natywny: wszystkie sześć etapów (wariant, resize, powrót, otwarcie,
resize po otwarciu, powrót po otwarciu). Nowy zakres ma 14 głównych wystąpień
i 72 części fizyczne. Sprawdzono także poprzednie płyty, okucia i 32 elementy
profili/wzmocnień. Oryginały i assety są niezmienione, własne dokumenty zamknięto.

Pierwszy harness uruchomiono zbyt wcześnie podczas trwającej operacji natywnej:
`artifacts/verification/20261024T144739153496Z/` zatrzymał się na prawidłowej
odmowie globalnej blokady przez testy źródła. Po zakończeniu wykonawcy wszystkie
siedem etapów przeszło: `artifacts/verification/20261024T144849825744Z/`.
Nie wyłączano ani nie osłabiano blokady. Późniejsze odświeżenie grafiki wykonano
rekurencyjnie przez part.Update/assembly.Update i SetDirtyFlag przed aktualizacją
sceny; miary geometrii są kontrolowane także po tym odświeżeniu.

Końcowy harness po poprawieniu kolejności odświeżania: wszystkie siedem etapów
PASS w `artifacts/verification/20261024T145850794694Z/results.json`.
PASS dodatkowy: miary po odświeżeniu grafiki i po kolejnym zapisie/otwarciu.
Widok natywny z przodu/boku i od tyłu sprawdzono; pomocnicze wymiary ukryto
w prezentacji. Wynik pozostawiono otwarty do odbioru użytkownika.
