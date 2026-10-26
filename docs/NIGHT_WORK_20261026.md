# RockPro — praca nocna 26.10.2026

Zakres: samodzielne naprawy kodu, pomiary procesu, przygotowanie mapowania
siedmiu rodzin oraz szeroki research architektury i rynku. Pytania konstruktora
zostają w ROC-45 na 27.10.2026; nie wypełniamy ich domysłami.

Punkt powrotu: lokalna gałąź `codex/snapshot-before-night-expansion-20261026`
na `484bf64`. To snapshot historii kodu, nie zapis otwartych modeli CAD ani
backup prywatnej bazy. Bieżąca gałąź: `codex/t2-parametryzacja`.

## Przyrosty

1. [Integralność standardu montażu i importu](MOUNT_STANDARD_REVIEW_20261026.md):
   spójność macierzy, pełne powiązanie planu z bajtami inwentarza, prawdziwy stan
   odczytu historii, ścieżki i kompletność archiwum Windows.
2. [Rzetelne statusy i raport czasu](PROCESS_EVIDENCE_20261026.md):
   błędy nie znikają po późniejszym sukcesie, niepowiązany log nie zatwierdza
   modelu, pomiary nie dublują czasu faz nadrzędnych i podrzędnych.
3. [Podgląd i architektura](ARCHITECTURE_REVIEW_20261026.md):
   niezmienna, zweryfikowana rewizja siatki przez całą sesję; plan połączenia
   istniejących modułów bez drugiego generatora czy osobnej bazy projektu.
4. [Research rynku](MARKET_RESEARCH_20261026.md):
   24 porównane rozwiązania i 41 linków źródłowych, własny rozwój vs integracje,
   trzy horyzonty i konkretne demonstracje. To rekomendacje, nie zakup lub instalacja.
5. [Karty rodzin](FAMILY_REVIEW_PACKET.md): powtarzalny generator lokalnego
   pakietu do rozmowy z konstruktorem; 7 modeli, 26 propozycji ról powiązanych
   z rzeczywistymi ID/ścieżkami, wszystkie pytania Q01–Q26. Żadna rola nie została
   automatycznie zatwierdzona. 53 braki odczytu historii cech są widoczne.
6. [Rozpoznanie ICAPI](IRONCAD_EXTENSION_OPTIONS_20261026.md): sprawdzone
   metadane obu zainstalowanych TLB, wspólne API parametrów/wycięć/rysunków/BOM
   oraz funkcje dostępne tylko w 29. Przykładowy wrapper w folderze 2027 ma
   wersję 27; właściwy wrapper 29 wygenerowano wyłącznie do analizy offline.
   Nie podmieniono działającego adaptera.
7. [Graf obróbek](MACHINING_DEPENDENCY_GRAPH.md): właściciel, cel i zależności
   każdej operacji; odmowa cykli, sierot i niespójnych etapów. Wycięcie dziedziczy
   etap okucia, a koła, gniazda i podpory pozostają w etapie 6. To nowy pomocniczy
   moduł offline, jeszcze bez adaptera receptur i wykonawcy CAD.
8. [Powtarzalny raport ICAPI](ICAPI_CAPABILITY_REPORT.md): kontrola metadanych,
   wersji hosta oraz hashy, brak automatycznego wyboru innego API. Każda funkcja
   ma osobno stan dowodu metadanych i próby natywnej.
9. [Benchmark montażu](OFFLINE_MOUNT_BENCHMARK.md): na M02 mediana pięciu prób
   wyniosła 20,47 ms dla budowy standardu, 27,07 ms dla walidacji i 40,57 ms dla
   planowania translacji z walidacją. Tych czasów nie sumujemy. To punkt
   odniesienia skryptów, nie pomiar generowania skrzyni w IronCAD.

W pracy uczestniczyły trzy agenty: architektura, rynek oraz walidacja montażu.
Koordynator przejrzał zmiany i raporty; poprawki obserwatora dostały dodatkowy
niezależny przegląd. Wszyscy pracowali poza natywnym CAD.

## Dowody

**PASS:** końcowy harness `artifacts/verification/20261026T213941196853Z/results.json`.
Dwanaście kroków: repository, backend, parts, core-design, core-contracts,
model-bundle, family-review, process-report, icapi-capabilities, mount-benchmark,
QA i harness. Zestawy unittest wykonały łącznie 700 testów;
liczba jest wynikiem tego przebiegu, nie stałą bramką.
Nie uruchamiano kompilacji/rejestracji dodatku, ponieważ nie zmieniano jego C#.
Nowy test natywny oraz wizualny odbiór okna obserwatora: **NOT RUN**.

Wyniki cząstkowe są w `artifacts/night-research-20261026/`:

- `mount-safety-rebind-evidence.json`: wszystkie 3427 węzłów / 2829 części
  siedmiu historycznych standardów zgodne z przypiętymi inwentarzami.
- `architecture-viewer-tests.json`, `architecture-viewer-dataset.json`:
  test podmiany plików podczas sesji, limity oraz rzeczywisty eksport siatki
  41 960 160 B bez modyfikacji źródła. To odczyt, nie pomiar wydajności CAD.
- `process-report-final/index.html`: raport 85 zdarzeń historycznego przebiegu
  z 24.10, nie nowa budowa skrzyni. Log natywny uczciwie opisany jako niepowiązany.
- `architecture-family-review-result.json`: pakiet `artifacts/model-library-20261026/review-packet-02/`.
  7 kart, 26 propozycji, 0 zatwierdzeń, komplet pytań i ponowna kontrola SHA źródeł.
- `sdk-comparison.json`, `extension-verification.json`, `market-verification.json`:
  metadane SDK i kontrola dokumentacji. API istniejące w TLB nie jest dowodem
  natywnego wykonania funkcji.
- `architecture-graph-demo.json`: jawnie syntetyczny przykład zależności
  zawias → profil, niezależny od numeracji warstw podglądu.
- `capabilities-v2/`: raport sygnatur API 25/29 z końcowego czytnika powiązanego
  z dokładnymi bajtami JSON; wszystkie próby hosta NOT RUN. Wersja v1 zachowana.
- `wing-offline-benchmark-01/benchmark.json`: surowe próbki wall/CPU, rozgrzewka,
  hashe danych i kodu, środowisko oraz kontrola niezmienności wyniku.

HTML przeszedł kontrolę danych, escapowania i struktury. Wizualny podgląd przez
przeglądarkę pozostał NOT RUN: polityka przeglądarki odrzuciła adres `file://`.
Nie obchodzono tej blokady innym transportem ani przeglądarką. Pliki są dostępne
lokalnie do otwarcia przez użytkownika.

## Rekomendacja produktowa

Rdzeń RockPro powinien pozostać własny: rodziny konstrukcji, katalogowe okucia,
kotwy, właściciele wycięć, luzy, jawne odstępstwa i spójne rewizje. Nie trzeba
natomiast pisać własnego CAM ani ERP. Para-Flex/woodLAB/VCarve to kandydaci do
próby po Q07, nie wybrani dostawcy. Szczegóły i źródła są w researchu rynku.

Najbardziej użyteczne rozszerzenia po ustabilizowaniu jednej rodziny:
porównanie zmian rewizji, paszport QR skrzyni i części serwisowe, instrukcja
montażu według etapów, kontrola wymiany SKU wraz z jego wycięciem, konfigurator
wkładów/pianki, a później animacja na rzeczywistej osi zawiasu i przegląd klienta.
AR oraz automatyczny obrys ze zdjęcia pozostają eksperymentami prezentacyjnymi,
nie źródłem wymiarów produkcyjnych.

## Granice i następna kolejność

- Nie zapisano ICS, nie przebudowano modeli, nie wdrożono nowej DLL i nie
  zmieniono bazy klienta. Nie wykonano nowego testu natywnego w tej rundzie.
- Odczyt i walidacja siedmiu inwentarzy nie są pełną parametryzacją W/D/H.
- Następny krok: sesja ROC-45 → jawne role i właściciele obróbek → ograniczone
  wymiary Wing → pozostałe rodziny → jedna zatwierdzona rewizja BOM/rysunków →
  próba integracji produkcyjnej na rzeczywistej technologii firmy.
- Docelowo Python wylicza reguły, gabaryt, kotwy i obróbki; agent proponuje
  mapowania i pomaga w wyjątkach. Numery warstw prezentacji nie zastępują grafu
  zależności obliczeń. Profile potrzebują pozycji zawiasów już na etapie planu.
- CAM, magazyn i konfiguratory porównano w researchu. Nie instalowano usług,
  nie wysyłano prywatnych modeli na zewnątrz i nie dokonywano zakupów.
- Nie zamknięto zbiorczo zadań Linear. Zgoda na nocną pracę nie jest odbiorem
  produkcyjnym, potwierdzeniem nośności ani akceptacją wszystkich rodzin.

## Lokalne commity implementacji

| Commit | Zakres |
|---|---|
| `2667a5a` | Powiązanie montażu ze źródłem i kontrola importu |
| `a998fa4` | Niezmienna rewizja siatki w sesji podglądu |
| `d3ad67f` | Statusy obserwatora i eksport pomiarów |
| `adfeac4` | Karty siedmiu rodzin do przeglądu |
| `bef4117` | Graf zależności montażu i obróbek |
| `9ca291e` | Powtarzalny benchmark montażu |
| `ea61e88` | Raport możliwości ICAPI na podstawie przypiętych metadanych |

Research, ten raport i rozszerzenie harnessu zapisano osobnym lokalnym commitem
dokumentacyjnym po powyższych przyrostach. Nie wykonywano push.
