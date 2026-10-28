# RockPro Studio — demo Vercel i zdjęcia producentów

Stan 28.10.2026. Adres dla Tomka: https://rockpro-studio.vercel.app.
Publikacja w projekcie `modivo/rockpro-studio`, konto `qooperboy-3029`, została
wyraźnie potwierdzona przez użytkownika. Git nie jest automatycznie podłączony
do tego wdrożenia. Sam lokalny commit nie aktualizuje strony.

## Co można sprawdzić

- 3 typy konstrukcji, wieka, sekcje, zmiany wymiarów oraz interaktywny podgląd.
- 14 bazowych pozycji modeli oraz wszystkie 265 rekordów Excela (263 różne kody),
  bez łączenia duplikatów. Krok 4 ma filtr `Katalog z Excela`, sidebar ma pełny
  katalog firmowy z 232 obrazami. Brakujące obrazy nie ukrywają rekordów.
  Pozycje bez sprawdzonego powiązania modelu są widoczne katalogowo, lecz mają
  zablokowany wybór do montażu. Źródłowe zespoły klientów nie są publikowane.
- Rozmieszczenie uchwytów i zamknięć, konstrukcja, koła i gniazda.
- 94 zdjęcia ze stron producentów z kodem, atrybucją i odsyłaczem do produktu.
- Zapis/wczytanie draftu w tej samej przeglądarce, ulubione i ranking różnych
  zapisanych projektów, eksport/import JSON.

Demo nie łączy się z żywym firmowym Excelem ani IronCADem. Nie ma wspólnej bazy
projektów ani stanów magazynowych. Po dodatkowej, wyraźnej zgodzie użytkownika
opublikowano nazwy, kody, kategorie, uwagi, zdjęcia i ceny wszystkich 265 rekordów.
Osiem brakujących cen pozostaje brakiem, nie zerem. Zapis na jednym komputerze nie pojawia się
automatycznie u drugiej osoby. Aby przekazać projekt, pobierz JSON. Wyczyszczenie
danych witryny usuwa zapisy przeglądarki; JSON jest przenośną kopią koncepcji.
Podgląd nie zatwierdza wycięć ani gotowości produkcyjnej.

## Gotowe projekty w bibliotece

Biblioteka `index.html` zawiera też trzy gotowe, ogólne projekty T1:
transportowy 600 × 500 × 800 mm (76 części), duży 900 × 700 × 900 mm
(84 części) oraz bez kół 600 × 450 × 800 mm (64 części). Wymiary oznaczają
wnętrze korpusu. Pokrywy mają odpowiednio 115, 125 i 110 mm. Wszystkie mieszczą
się w zwykłej proporcji pokrywy; nie wymagają skrytego odstępstwa.

`studio_examples.py` buduje recepty z istniejących części i sprawdza je wspólnym
planerem. To warianty kompletnej konstrukcji T1, nie gotowe szafy ani T2.
Otwarcie tworzy nowy draft w przeglądarce i przechodzi do końcowego kroku 7;
nie nadpisuje szkicu z poprzedniej sesji. Wszystkie elementy i wymiary pozostają
edytowalne. Miniatury pochodzą z rzeczywistego renderera Studio:

```powershell
node scripts/render_studio_examples.cjs http://127.0.0.1:51345 artifacts/WYDANIE
node scripts/test_studio_examples.cjs https://rockpro-studio.vercel.app artifacts/examples-production
```

Pierwszy build udostępnia recepty do renderowania. Następny build do nowego
katalogu kopiuje miniatury z `artifacts/studio-example-images` i obejmuje je
manifestem. Opublikowane wydanie z wzorcami: `artifacts/vercel-studio-20261028-08`.
Test trzech kopii, zapisu/odczytu, otwierania pokryw, ochrony wcześniejszego szkicu,
miniatur i układu nocnego/mobile: `artifacts/examples-production/results.json`.

## Podsumowanie cenowe

W kroku 7 oraz na końcu kroku 8 `Podsumowanie cenowe części` korzysta z ilości wspólnego
`project_summary` oraz cen katalogu. Dopasowuje pełny kod bez utożsamiania
podobnych wariantów. Przy kilku rekordach kodu nie wybiera arbitralnie ceny.
Zachowuje cenę zero, braki cen oraz oddzielne sumy różnych walut.

Arkusz nie deklaruje waluty, netto/brutto i jednostek wszystkich cen. Widoczne
założenie `Szacuj cenę okuć za sztukę` pozwala oszacować tylko okucia liczone
w sztukach. Można je wyłączyć. Profile, płyty i pianki nie są mnożone przez
liczbę elementów bez ustalenia jednostek i materiału. Wycena pokazuje pozycje
pominięte i nie jest pełną ceną skrzyni. Zmiana ilości/układu odświeża zestawienie;
w trakcie przeliczania poprzednia kwota jest ukrywana.

## Zakończenie i kontrola projektu

Krok 7 kończy się aktywnym `Sprawdź projekt`, który prowadzi do kroku 8
`Kontrola projektu`. Raport z `studio_review.py` wykorzystuje wspólny planner,
nie niezależne obrysy. Wskazuje znane kolizje i rezerwy od krawędzi, brak miejsca
na rząd zamknięć, niedopasowane złącza, wybrane lecz nierozmieszczone części,
brak uchwytów/zawiasów/zatrzasków i brak lub nieobsługiwaną konstrukcję.
Pominięcia wynikają z danych, nie z liczenia kliknięć w etapy.

Każde zgłoszenie ma poziom, numer kroku i dostępne identyfikatory grup/sekcji.
Przycisk otwiera odpowiedni edytor i zaznacza grupę; kolizja pozwala także wskazać
drugą część. Po poprawce kontrola jest przeliczana. Błędne dane blokują zapis
przez istniejący walidator; poprawny składniowo projekt z problemami układu można
zachować jako draft. Raport nie ustawia zgody produkcyjnej. Kontrola kolizji to
znane obrysy 2D na wspólnej ścianie, nie BRep ani pełna przestrzeń ruchu.

Widoczny `Pobierz JSON` w nagłówku i `Pobierz projekt JSON` na końcu pobiera
bieżące dane bez zależności od sieci. Plik nie jest modelem ICS i nie generuje
automatycznie CAD. Wersja Vercel ma jawne `Zapisz w przeglądarce`, nie wspólną
serwerową bazę. Zapis aktualizuje permalink, zapis kopii zachowuje oryginał,
a błędy pamięci przeglądarki nie blokują pobrania pliku. Brak projektu pod
linkiem nie wyłącza już importu i edytora. Kopie/recovery pozostają zachowane.

Dowody: `artifacts/save-finish-production/results.json`,
`artifacts/review-production/results.json`; testy backendu
`rockpro_cad.mcp.test_studio_review` (7 przypadków) i pełny harness
`artifacts/verification/20261028T152842874887Z/`. Aktualna paczka:
`artifacts/vercel-studio-20261028-14` wraz z manifestem. Nie wykonywano CAD.

## Architektura i publikacja

`deploy/vercel/` zawiera adapter demonstracyjny. `scripts/build_vercel_studio.py`
tworzy nowy katalog wydania wewnątrz ignorowanego `artifacts/`, kopiując tylko
jawną listę modułów, statyk, licencji i pojedynczych okuć. Nigdy nie publikuj
katalogu repozytorium ani nadrzędnego `artifacts/`.

```powershell
Integracja\.venv\Scripts\python.exe scripts/build_vercel_studio.py --output artifacts/vercel-studio-NOWE-WYDANIE
```

Builder odmawia nadpisania wydania i generuje obok niego manifest plików z SHA.
Wykrywa prywatne ścieżki oraz pola danych magazynowych w publicznym JSON.
Python API wykonuje tylko `preview` i `convert` przez te same walidatory co Studio.
Nie kopiuje modułu bazy projektów ani wykonawcy CAD. Import persystencji w lokalnym
`configurator.py` jest leniwy: lokalne zapisy nadal korzystają z dotychczasowej SQLite.

`cloud-storage.js` przechowuje drafty i preferencje w localStorage, kontroluje
oczekiwaną rewizję, serializuje zapis przez Web Locks i zgłasza brak miejsca.
Przeglądanie oraz kolejne rewizje nie zwiększają liczby różnych projektów.
Nie wolno przedstawiać tego adaptera jako firmowego ERP lub wspólnej bazy.

Po kontroli manifestu uruchom w katalogu konkretnego wydania:

```powershell
vercel deploy --prod --yes --project rockpro-studio --scope modivo
```

CLI musi być wcześniej zalogowane. Po publikacji sprawdź stronę anonimowo,
nie tylko przez uwierzytelnione `vercel curl`. Lokalnie trasowanie można sprawdzić:

```powershell
Integracja\.venv\Scripts\python.exe scripts/serve_vercel_studio.py artifacts/vercel-studio-NOWE-WYDANIE
node scripts/test_vercel_studio.cjs http://127.0.0.1:51345 artifacts/vercel-e2e-local
node scripts/test_vercel_studio.cjs https://rockpro-studio.vercel.app artifacts/vercel-e2e-production
```

Test przeglądarki wymaga Playwright/Chrome i lokalnego przykładowego JSON T1;
ścieżki środowiska testowego są jawne w skrypcie. Nie są zależnościami Vercela.

## Zdjęcia producentów

`scripts/fetch_manufacturer_images.py` czyta jawne adresy z katalogów. Pobiera
tylko HTTPS z domen producentów, ogranicza rozmiar, weryfikuje pełny SKU oraz
sygnaturę PNG/JPEG, zapisuje źródło, datę i SHA. Obsługuje SKU w JSON-LD oraz
HTML Penn Elcom; nie dopasowuje zdjęć przez podobieństwo kodu, kategorię ani
listę produktów polecanych. Brak zgodności pozostawia dotychczasowy obraz.
Nie omija błędów dostępu. Raport zapisuje każdy brak lub odrzucone dopasowanie.

```powershell
Integracja\.venv\Scripts\python.exe scripts/fetch_manufacturer_images.py
Integracja\.venv\Scripts\python.exe scripts/test_manufacturer_images.py -v
```

Opcjonalny overlay `artifacts/manufacturer-images/index.json` nie zmienia Excela,
definicji części, zgód montażowych ani oryginalnych renderów. Moduł
`manufacturer_images.py` sprawdza integralność i zachowuje metadane siatki przy
podmianie obrazu. Katalog firmowy ma 90 zdjęć producentów i 232 pozycje ze zdjęciem
łącznie; pozostałe obrazy pochodzą z zachowanego Excela. Pozostałe 4 zdjęcia
producentów są przypisane do bazowych pozycji Studio. Wyświetlana informacja
odróżnia zdjęcie producenta od renderu CAD.

Przykłady odrzuceń: kod AH 4054 wskazuje stronę 4053; na wskazanej stronie W0968Z
główny kod to D0941/5Z, a W0968Z występuje tylko w polecanych. Nie przenosimy
takiego zdjęcia na wariant o innym SKU. Katalogi wariantów/serie wymagają strony
jednego produktu lub ręcznego potwierdzenia.

## Dowody bieżącej wersji

- Pełny harness offline PASS: `artifacts/verification/20261028T121556408787Z/`.
- 21 testów katalogu firmowego i konfiguratora PASS po zmianie podsumowania zdjęć.
- 4 testy zdjęć PASS, w tym wariant SKU, polecany produkt, integralność i zachowanie siatki.
- E2E anonimowej produkcji PASS: `artifacts/vercel-full-catalog-production/results.json`.
  T1: 10 paneli, 8 okuć ręcznych i 58 części konstrukcji, razem 76 pozycji;
  zmiana wymiaru, 3 rewizje, eksport JSON, konflikt rewizji, izolacja przeglądarek,
  zdjęcia, 3 typy sekcji i układ mobilny.
- Pełny katalog: 6 testów backendu PASS oraz test arytmetyki cen w
  `scripts/test_cost_math.mjs` (brak/zero, warianty, jednostki, waluty, zmiana ilości).
- Harness pełnego katalogu PASS: `artifacts/verification/20261028T124319772089Z/`.
- Historyczna paczka pełnego katalogu: `artifacts/vercel-studio-20261028-06`, manifest obok katalogu.
- Oryginalny Excel zachowuje SHA256
  `7d2616b00b3433def8c4c9f0339b429c076ca1f67313b21859ee2185e23c8924`.

Nie wykonywano nowych operacji natywnych CAD w tym zadaniu.

## Aktualizacja modeli producenta — 28.10.2026

Wdrożono 74 siatki i 81 definicji dostawców, miniatury oraz filtr
„Modele 3D producenta — STEP”. Publiczny adres pozostaje bez zmian.
Wydanie: `dpl_HMF12VLckssYmgWjgHPC3MHkFxWS` (READY), paczka
`artifacts/studio-supplier-preview-final-20261028`, kod `3065e2f`.
Anonimowy E2E produkcji PASS: 74 modele, integralność i dekompresja,
rozmieszczanie, dodatkowe wystąpienie, resize, zapis/odczyt draftu.
Dowody: `artifacts/supplier-studio-production-check/result.json` i zrzuty.
Pobrany CAD nie zatwierdza montażu/wycięć. Zapis publikacji: ROC-61;
pozostała kolejka: ROC-47–ROC-60, zgodnie z `TODO_20261028.md`.
