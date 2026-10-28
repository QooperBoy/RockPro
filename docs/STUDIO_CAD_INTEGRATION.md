# Studio → IronCAD 2027 — ROC-46

**28.10, późniejsza migracja wskazanej kopii T1:** wdrożono fizyczne zespoły
oraz natywne parametry rozstawów/marginesów osprzętu, z dowodem po reopen.
Patrz [T1_ACCESSORY_PARAMETERS.md](T1_ACCESSORY_PARAMETERS.md). To osobny tryb
migracji kopii; nie oznacza dodania nowych kontrolek do kreatora ani odbioru
nowych konturów zakończeń profili. Poniższy odbiór ROC-46 pozostaje historyczny.

**Doprecyzowanie użytkownika 28.10.2026, po poniższym odbiorze:** obowiązuje
drzewo fizycznych zespołów `Wieko 1…N` (tylko rzeczywiste pokrywy) i `Podstawa`
(cały stały korpus), zgodnie z późniejszą korektą nazw, oraz licowanie okuć;
profile mają kończyć się przy zewnętrznym kołnierzu zawiasu, nie przy otworze
w sklejce. Zobacz CASE_STRUCTURE.md i CASE_DEFAULTS.md. Poniższe wyniki
dokumentują poprzednią implementację sześciu grup i nie potwierdzają jeszcze
wdrożenia tych nowych wymagań. W tej aktualizacji zapisano reguły, bez zmiany CAD.

[ROC-46](https://linear.app/rock-pro/issue/ROC-46/studiocad-generowac-kompletna-skrzynie-z-kreatora-w-ironcad-2027)
łączy zapisaną rewizję kreatora z nową sceną CAD. Adapter obejmuje T1:
jedno górne wieko na zawiasach, sklejkę 9,8 mm, H7159, 17251S i 270836 oraz
EG-0113, EG-0500/1 i /2, 410429, B1930/B1121, podpory, źródłowe koła Epson
i W0968Z. Inny SKU lub rodzina wymaga osobnego powiązania. 27095 ma własną
znaną receptę, lecz nie jest obsługiwany przez ten adapter.

**Stan odbioru: PASS** — generowanie z przycisku Studio, pełny model,
zmiana gabarytów/powrót, zapis/ponowne otwarcie i ponowna zmiana parametrów.
To nie jest odbiór produkcyjny konstruktora.

## Przepływ

1. Zapis draftu w istniejącej bazie. „Sprawdź plan CAD” przypina ID, rewizję,
   SHA draftu, katalog, kompilator, manifest źródeł i kod wykonawcy.
2. Plan rozlicza wszystkie wybory, pozycje i obróbki. Pełna kompilacja zestawu T1
   odblokowuje „Wygeneruj całą skrzynię”. Edycja draftu unieważnia plan.
3. Trwała kolejka w tej samej SQLite przyjmuje operation_id. Worker poza HTTP/DB
   uruchamia proces SDK ze wspólną blokadą CAD.
4. Wykonawca sprawdza API29/PID hosta i SHA wejść, tworzy nową scenę oraz sześć
   grup. Każdy etap obejmuje swoje części i wycięcia.
5. Kontrole obejmują podzespoły katalogowe, pozycje/obroty, obrysy płyt,
   długości profili, negatywne cechy i ich kotwy, resize/powrót oraz zapis/reopen.
6. Kwit wiąże wynik z SHA planu i wskazuje plik. Błąd/timeout daje outcome_unknown
   i blokuje ponowienie do uzgodnienia. Restart nie odtwarza rozpoczętych operacji.

Endpointy: wizard/native-plan, wizard/native-build, wizard/native-jobs/<id>.
Przyjmują zapisane ID/SHA, nie ścieżki ani kod. Token sesji, Origin, kontrola
rewizji/CAS i pełne ponowne przeliczenie planu pozostają obowiązkowe. Prywatne
ścieżki źródeł nie trafiają do planu przeglądarki.

## Wymiary i wspólny podgląd

Studio podaje użyteczne wnętrze korpusu X/Y/Z. Dla tego zestawu W=X+2t,
D=Y+2t, B=Z+t (dno); wysokość obudowy bez transportu to B+L.
Dziesięć płyt nie nakłada się objętościami. Szczelina 8,63 mm pochodzi
z przypiętej receptury profili, a nie z rozsunięcia prezentacyjnego.
Podfrezowania są osobnymi operacjami; cztery ściany wieka tracą dodatkowo
0,1 mm przy osadzeniu. Półfabrykat i końcowe obrysy są sprawdzane osobno.

Polskie parametry sceny: RP_SzerokoscWnetrza, RP_GlebokoscWnetrza,
RP_WysokoscWnetrza, RP_WysokoscPokrywy, RP_GruboscSklejki. Komentarze
wyjaśniają osie i pomiar. Grubość 9,8 mm jest stałą tego pasowania;
zmiana zestawu/grubości wymaga nowego planu Studio. Pokrywa i jej jawny
override wynikają z aktualnego draftu.

Ramy profili/wzmocnień/transportu podglądu odpowiadają natywnym bazom.
Siatka koła ma przypięte do SHA przeliczenie UVN→source.local. Podgląd skaluje
tylko długość profilu, według zmierzonego obrysu siatki. Gniazdo jest nad punktem
kontaktu koła, a jego płaszczyzna osadzenia leży na górnej powierzchni wieka.

Liczności podglądu i sceny mogą się różnić: segmenty profilu odpowiadają ciągłemu
profilowi z wycięciem, a para zamka/zawiasu ma dwie natywne połówki. Plan zawiera
structure_mapping. Żadna wybrana pozycja nie może pozostać niezmontowana.
Zestawienie nie obejmuje nieznanych nitów/wkrętów i nie jest zakupowym BOM.

## Ochrona danych i wykonanie

Snapshot: codex/snapshot-before-roc46-native-20261027. Nowe wyniki i próby zapisu
ROC-46 trafiają wyłącznie do nowych katalogów. Oryginały i wcześniej otwarte,
niezapisane dokumenty pozostają zachowane. Po błędzie własny model trafia do
nowego recovery przed zamknięciem. Wejścia otwierane są z unikalnych kopii tylko
do odczytu. Automatyczne zmiany ich cache SDK nie są zapisywane przez przebudowę
historii katalogowej; oryginalne bajty kopii pozostają na dysku. Regenerowane są
tylko nowe płyty i jawnie edytowane, czyste profile, bez wnętrza katalogowych okuć.

StudioCad2027.cs jest kompilowany z przypiętych bajtów. Runner weryfikuje SHA
siebie, wykonawcy i bridge. Interop powstaje z aktualnego TLB instalacji,
a nie starego przykładu SDK. Brak fallbacku do 2023 i uruchamiania drugiego hosta.

## Uruchomienie i dowody

Uruchom normalnie IronCAD 2027. scripts/Start-StudioCad.ps1 przyjmuje -Bundle,
-Database, -CadAssets, opcjonalnie -Python, -Previews, -PartImages i -SourceParts.
Ścieżki wskazują istniejące prywatne zasoby. Manifest podaje lokalny operator,
nie HTTP. Serwer wybiera jedną działającą instancję 2027. Baza jest współdzielona
z dotychczasowym Studio, a nowe tabele są addytywne. Nie zastępować danych demem.

Kod: studio_cad.py, studio_native_t1.py, studio_native.py, studio_cad_jobs.py,
reference_studio.py i scripts/native/StudioCad2027.cs. Historyczny pierwszy
przyrost: artifacts/studio-cad-20261027/. Bieżące próby: artifacts/roc46-*;
wyniki z przycisku: artifacts/studio-native/. CAD, manifesty, bazy i logi są
prywatne, poza Gitem.

## Naprawy ujawnione w próbach natywnych

- CopyFeatureTo odejmowało w starym położeniu i zwracało E_FAIL. Teraz dokładny
  profil jest kopiowany i ustawiany przed włączeniem odejmowania.
- Automatyczne równania przesuwały ekstruzję płyty. Jej położenie jest jawnie zerowe.
- Nowa ekstruzja miała fabryczny sizebox, co powiększało wycięcia. Najpierw
  materializacja/reset, potem powiązanie wymiarów.
- Sam Part.Update/Regenerate nie przeliczał gabarytów sceny. Aktualizacja sceny
  poprzedza regenerację własnych części.
- Kolejne importy kasowały wcześniej utworzone równania cech. Powiązania są
  odtwarzane dopiero po ostatnim imporcie, w finalnej hierarchii. Po ponownym
  otwarciu nie są naprawiane: próba sprawdza ich trwałość.
- SHA otwartego wyniku wymaga współdzielenia odczytu/zapisu z hostem. Zapis
  wyników nadal odbywa się wyłącznie pod nowe nazwy.

Szafa, konstrukcja trzyczęściowa i inne SKU pozostają zablokowane. Ruch TriBallem
nie przelicza układu: zmiany wynikają z tabeli parametrów sceny lub nowego
zapisanego planu Studio. Akceptacja produkcyjna należy do konstruktora.

## Jawne odzyskiwanie kolejki

Po znanej nieudanej i posprzątanej budowie można lokalnie wywołać
scripts/reconcile_studio_cad_job.py --database <baza> --operation <ID> --evidence <katalog>.
CLI bierze blokadę CAD, weryfikuje przypięty request/kod/plan, oryginalne źródła,
raport niepowodzenia, kopię recovery i sprzątnięcie dodatku. Zapisuje osobny
status failed_reconciled z passed=false oraz addytywny audyt poprzedniego stanu.
Nie obsługuje queued/running ani przypadków bez kompletnych dowodów; nie ma
publicznego endpointu ani automatycznego retry. Udane uzgodnienie umożliwia nowe
zlecenie po poprawce, a nie zmienia nieudanej próby na sukces.

Kompilator stosuje dopuszczalne jednostronne próby przy granicy 15% pokrywy,
bez modyfikowania override. Przed planem kontroluje obrysy górnych gniazd
136 × 90 mm, już po przeliczeniu rzeczywistych punktów osadzenia, z luzem 2 mm.
Nie powiększa sam skrzyni i nie przesuwa kół, aby ominąć konflikt.

## Odbiór z przycisku — 28 października 2026

- Draft 70a10d97998143749cdfe9ae793e3bdc, rewizja 6.
- Operacja fe2d6b09344c46c5878d32db9cf2066f, status succeeded.
- Plan SHA a4c66665a8ef26214ada5bca3849d9bf91cc5f0bb0f1e506d1bad5941e4b1f8a.
- Wnętrze 600 × 500 × 800 mm, pokrywa 115 mm, sklejka 9,8 mm.
- 72 wystąpienia (12 płyt/podpór + 60 części katalogowych), 48 obróbek;
  zachowane 244 wewnętrzne części źródłowych podzespołów i płyt.
- Baseline, resize, powrót, reopen, resize po reopen, powrót i pomiar końcowego
  zapisanego pliku: PASS. Po reopen nie odtwarzano naprawczo powiązań.
- SHA wyniku 5f14516a294f6d587ed5ce4dab3e087477ec545bddf9e2dfb5bbb57219bdf525.
- Oryginalne źródła oraz 10 wcześniej otwartych dokumentów zachowane.
  W bazie pozostało identycznych wszystkich 10 draftów i 18 historycznych rewizji.
- Raport: artifacts/studio-native/verification-summary.json. Pełne dane:
  studio-26a21292a8114979baeb481c57fff92f-e2f72898/result.json w tym katalogu.
  Native-source.cs, request, compile, progress i addon_cleanup wiążą wynik
  z faktyczną wersją kodu. Pozostałe próby roc46-* są diagnostyką historyczną.
- Studio-ROC46-success.png pokazuje status sukcesu kreatora;
  RockPro_Studio_T1.png w katalogu zlecenia jest eksportem obrazu z IronCADa.

Pierwsza próba e8307c83926149deab8f5304e3dd47fa pozostaje nieudana:
failed_reconciled, passed=false, z odrębnym audytem i zachowaną kopią recovery.
Odbiór dotyczy wyłącznie wskazanego adaptera T1, nie produkcji, innych rodzin
ani nieobsługiwanych SKU. Nie wykonywano push.

Końcowa regresja kodu: PASS, 12 kroków w
artifacts/verification/20261027T232115451805Z/results.json. Osobno PASS:
cztery testy generowania interop (scripts/test_t1_local_interop.py), kontrola
składni JS i launchera PowerShell oraz końcowy audyt SQLite/kwitu CAD.
Wcześniejsze nieudane raporty pozostają historyczne: zajęta blokada podczas
równoległej próby CAD oraz test samych paneli używający transportu w zbyt wąskiej
skrzyni. Test paneli izoluje teraz geometrię płyt, a gniazda mają oddzielne próby
odrzucenia kolizji i dokładnej granicy 2 mm. Nie pominięto wymaganych kontroli.
