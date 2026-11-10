# RockPro — porównanie Linear z lokalnym wykonaniem, 24.10.2026

Aktualna kontynuacja: pełne prototypy z profilami, zawiasami i kołami oraz
poprawiona płytka pokrywa EB-L630U są opisane w CASE_DEFAULTS.md.
Następny rozpoczęty przyrost ROC-40: rzeczywisty odczyt ręcznych zmian
pozycji jawnie wskazanych okuć, bez automatycznego cofania pracy konstruktora.
Status całego ROC-40 i integracja ekranu decyzji pozostają otwarte.
PASS natywny wąskiego przyrostu: przesunięcie H7159 o 12 mm wykryte jako
konflikt, zachowane po zapisie/otwarciu, prototyp bez zmian.
Szczegóły: [NATIVE_MANUAL_CHANGES.md](NATIVE_MANUAL_CHANGES.md).

Nowszy przyrost: [świeży pomiar bazy H7159 i natywna para](H7159_FRESH_MOUNT.md).
Pozostaje pełny POC z płytami oraz uzgodnienie sześciu raportów i sidecaru;
statusy całych zadań nie są zamknięte.

Źródło kolejności: [projekt RockPro CAD](https://linear.app/rock-pro/project/rockpro-cad-d99cc3102643/overview),
lista 39 zadań oraz opisy ROC-42, ROC-17, ROC-20 i ROC-40. API Linear nadal wskazuje
workspace modivo; Rock_Pro jest dostępne przez zalogowaną przeglądarkę. Nie
zmieniono statusów i nie oznaczono odbiorów użytkownika jako Done.

W Linear: Done — ROC-15 i ROC-43; In Progress — ROC-16/17/19/20/22/26/40/42;
Todo — ROC-38. Pozostałe zadania są w Backlog. Epiki ROC-5–10 porządkują zakres,
nie są osobnymi przyrostami do wykonania przed wszystkimi podzadaniami.

## Porównanie z dowodami

| Zadania | Co rzeczywiście jest lokalnie | Co pozostaje |
| --- | --- | --- |
| ROC-15, ROC-43 | Kontrakt jednostek, rewizji i wymiarów; zamrożone przypadki i planer. Bieżący harness PASS. | Nie traktować danych syntetycznych jako zatwierdzenia Epson. |
| ROC-20 | Dodatek zarejestrowany i załadowany tutaj; MCP odczytuje i zmienia szkielet na kopii, zapis/otwarcie oraz snapshot SQLite PASS. Kolejka, blokada i dziennik operacji istnieją w kodzie. | Rozszerzenie dowodu na aktualny montaż katalogowy; utrzymać obsługę nieznanego wyniku. |
| ROC-22 | Wersje, CAS karty/etapów/układu, historia, snapshoty i odzyskiwanie prototypu są zaimplementowane i testowane. Opis projektu o braku CAS karty/etapów jest starszy od kodu. | Odbiór procesu akceptacji i pełnego wydania. |
| ROC-16 | Szkielet dziesięciu płyt działa tutaj; pełny planer i zastępczy prototyp 37 grup/67 brył mają starsze raporty natywne. | Pełna rzeczywista rodzina, stabilne odniesienia katalogowe i odbiór konstruktora. |
| ROC-42 | Pełny builder/validator manifestu i historyczny inwentarz 403 węzłów istnieją. | Jedna zapisana rewizja dla inwentarza/eksportu, uzgodnienie ID, role, ramy, parowanie i nierozpoznane części. To bieżący przyrost. |
| ROC-17 | Rzeczywiste narożniki, zatrzaski i H7159 mają osobne POC; kostka 1000 mm ma historyczny raport. Nie są wspólnym ukończonym generatorem. | Powiązanie źródła, wspólny montaż; potem profile/wzmocnienia, zawiasy oraz koła/gniazda. |
| ROC-19 | Testy kontraktów, symetrii, planera, geometrii i prototypów istnieją. | Odbiór rzeczywistej rodziny i produkcyjnego BOM. |
| ROC-40 | Planer zachowuje jawne decyzje i wykrywa konflikty grup. | Pomiar i trójstronne uzgadnianie rzeczywistych ręcznych zmian CAD oraz ekran decyzji. Po kotwach ROC-16/17. |
| ROC-26 | Ograniczony serwer MCP udostępnia 21 narzędzi; panel korzysta ze wspólnego backendu. | Nadzorowany agent i odbiór całego cyklu propozycja–akceptacja–wykonanie. Brak samodzielnego zatwierdzania wydań. |
| ROC-38 | Techniczny test szkieletu/snapshotu wykonano tutaj. | Odbiór użytkownika oraz pełna ścieżka konfiguratora i konfliktu zapisu; statusu nie zamykamy automatycznie. |
| ROC-11–14 | SDK/środowisko i próbki są przeniesione, dodatki lokalnie zinwentaryzowane; baza procesu znajduje się w materiałach. | Potwierdzenia klienta, technologii/licencji WoodLAB i zakresu rodziny. Nie zgadywać brakujących danych biznesowych. |
| ROC-18 | Jedna wspólna baza istnieje. | Walidowany import/eksport Excel z wersjami i jednostkami. |
| ROC-21 | ICS, pomiary i raporty prototypu istnieją. | Produkcyjne rysunki, formatki i BOM z jednej zatwierdzonej rewizji, sprawdzenie WoodLAB. |
| ROC-23–25 | Ręczne obrysy urządzeń, 18 wariantów układu; pełny prototyp ma zastępcze bryły wyposażenia. | Katalog ze źródłami, rekomendacje archiwalne i produkcyjne wnętrze/pianki. |
| ROC-27–33 | Brak potwierdzonego lokalnego przepływu produkcyjnego materiałów. | Audyt WoodLAB PLAN i dane historyczne → import BOM → rozkrój → rezerwacje → propozycje zakupów → test zmiany rewizji. |
| ROC-34–37 | To stanowisko ma działające środowisko testowe. | Odbiory rodziny/AI/materiałów, szkolenie i plan utrzymania; nie utożsamiać z odbiorem stanowiska Kuby. |
| ROC-39 | Archiwum i korespondencja zachowane lokalnie. | Kontrolowany import na kopii danych i wdrożenie u klienta. |
| ROC-41 | Wycięcia i styki są wyłączone z obecnego MVP. | Osobny etap po montażu i odbiorze okuć. |

## Kolejność wykonania

1. ROC-42: świeży inwentarz i pozycje jednej zapisanej rewizji, bez zmiany źródła.
2. ROC-42/17: jawne uzgodnienie korzenia H7159 i powiązanie eksportu z tym
   inwentarzem. Wykorzystać istniejące `catalog_assets`, nie budować od nowa
   odebranych POC. Utrzymać brak zgody produkcyjnej do odbioru.
3. ROC-17/16: wspólny montaż odebranych rodzin na kopii, podstawowy resize
   i zapis/otwarcie; potem uzupełnienie profili, zawiasów i kół/gniazd.
4. ROC-40: rzeczywiste ręczne zmiany i rozstrzyganie konfliktów przed przeliczeniem.
5. ROC-21/18: spójne dokumenty, BOM i Excel; następnie odbiór rodziny.
6. ROC-23–26 i materiałowy ROC-27–33 według danych i zależności; pilotaże na końcu.

ROC-38 pozostaje osobnym odbiorem użytkownika. Wyniki techniczne ani zgoda na
kontynuację nie są podpisem zatwierdzającym produkcję. Równolegle nie uruchamiamy
kilku wykonawców CAD.

## Rozpoczęty przyrost

Dodano [przechwycenie zapisanej rewizji](SOURCE_REVISION_CAPTURE.md), dziewięć
testów guardów/wyboru oraz dwa testy sprzątania dokumentów eksportera.

PASS natywny: `artifacts/saved-source-native-20261024-02/capture_receipt.json`.
Jedna kopia źródła przypięta SHA256 z archiwum; 403/403 węzły, 289 wystąpień
części, 113 zespołów, w tym 11 pustych. Szkic manifestu jest poprawny i kompletny
rachunkowo. Zachowano 35 błędnych obrysów części oraz wszystkie diagnostyki
transformacji i obrysów z czytnika pozycji. Nie przyznano zgód ani ilości BOM.

Wyjaśniono odmowę pierwszego przebiegu: korzeń H7159 ma zgodne ID 11797 i ścieżkę
[1,6], poprawną ramę świata, lecz odbitą ramę rodzica. Nowy wybór zachowuje ten
niezmieniony mirror jako dowód, zamiast prostować macierz lub geometrię.
Przypadki skalowania i odbicia ramy świata nadal są odrzucane.

PASS wybór: `artifacts/h7159-saved-binding-20261024-01/selection_receipt.json`.
PASS eksport/import/przesunięcie/zapis/otwarcie: `artifacts/saved-source-native-20261024-02/h7159-export-20261024-01/native_receipt.json`.
13 rzeczywistych części; zachowano topologię, objętości, lokalne obrysy i
wewnętrzne transformacje. Błąd pozycji i rotacji: 0. Wyeksportowany asset pochodzi
z dokładnie tej samej zapisanej rewizji co świeży inwentarz. Wszystkie własne
dokumenty tych operacji zamknięto; oryginał i przypięta kopia niezmienione.

`catalog_native` zamyka teraz wyłącznie przejęte przez operację dokumenty,
zachowuje niespodziewanie zmodyfikowane kopie w nowych plikach i zapisuje PASS
dopiero po skutecznym sprzątaniu. Nie zmienia aktywnego planera ani DLL.

Pozostało do następnego przyrostu ROC-42/17: świeże świadectwa płaszczyzn montażu,
POC pary uchwytów z nowym assetem oraz uzgodnienie sześciu raportów istniejącego
`catalog_assets` i sidecaru z nowym manifestem. Stare raporty nie są przepinane
na nowy asset tylko dlatego, że geometria lub nazwa wygląda podobnie. Cały
ROC-42/17 pozostaje In Progress, pełny generator nie jest gotowy produkcyjnie.

Bazowy harness przed zmianą: `artifacts/verification/20261024T122404043794Z/` —
repository/backend/parts/core-design/core-contracts/qa/harness PASS. Zastane trzy
zmienione pliki są zachowane. Historię źródła odtworzono z bundle bez checkoutu
nadpisującego dane i bez ponownego stosowania patcha; bieżąca gałąź to
`codex/roc42-catalog-continuation`.

Harness po zmianach: `artifacts/verification/20261024T124333856134Z/results.json` —
wszystkie siedem etapów PASS. Po końcowej aktualizacji dokumentacji wykonano
osobny audyt struktury i odnośników: `repository-final.json` w tym samym katalogu,
PASS bez błędów. `git diff --check` PASS. Sumy SHA256 trzech zastanych plików
roboczych są nadal zgodne z inwentarzem transferu. Nie wykonywano push ani
publikacji prywatnych modeli, baz i dowodów.

## Nice to have dodane 24.10.2026

[Animacja otwierania na zawiasach](CASE_OPENING_ANIMATION.md): SmartMotion,
zmierzona oś sworzni, później Mechanism Mode. Utworzono [ROC-44](https://linear.app/rock-pro/issue/ROC-44/nice-to-have-animacja-otwierania-pokrywy-wokol-osi-zawiasow) w projekcie RockPro CAD, Backlog, Low. Rozpoznanie dokumentacji i SDK
wykonane, animacja sceny i eksport NOT RUN.
