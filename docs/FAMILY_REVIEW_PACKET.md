# Powtarzalne karty mapowania rodzin

`scripts/prepare_family_review.py` tworzy prywatny `packet.json` i lokalny
`index.html` do rozmowy z konstruktorem. Czyta istniejące dane; nie uruchamia
IronCAD, nie zapisuje modeli i nie nadaje zatwierdzeń. To powtarzalny generator
kart, uzupełniający historyczny prywatny `build_family_notes.py`.

Wejścia są jawne: manifest paczki, szkice rodzin, katalog inwentarzy, dokument
pytań i konfiguracja przypisująca numery pytań do modeli. Przykład konfiguracji:

```json
{"schema_version":1,"common_questions":["Q01","Q02"],
 "models":[{"key":"M01","questions":["Q17","Q18"]}]}
```

Konfiguracja, manifest i szkice muszą zawierać ten sam zestaw modeli. Kolejność
kart wynika z konfiguracji. Pytania mają postać `[ ] Q01. Treść`; powtórzone
numery i nieistniejące odwołania są odrzucane. Generator nie importuje odpowiedzi
ani zatwierdzeń z checkboxa.

```text
python scripts/prepare_family_review.py --manifest artifacts/PACZKA/pristine/manifest.json --drafts artifacts/PACZKA/library/family_drafts.json --inventory-dir artifacts/PACZKA/native-02 --questions artifacts/PACZKA/review/ROC-45.md --config artifacts/PACZKA/review-config.json --output artifacts/PACZKA/review-packet-01
```

Sprawdzany jest rzeczywisty SHA źródła, zgodność z manifestem i szkicem,
SHA bajtów inwentarza przypięty w szkicu oraz kompletność ram/hierarchii przez
istniejący `working_mounts.build_working_standard`. Na końcu ponownie sprawdzane
są hashe wejść. Wynik powstaje wyłącznie w nowym folderze. Dane klientów, ścieżki,
nazwy, karty i konfiguracja konkretnej paczki należą do ignorowanego `artifacts/`.

ID kandydata musi wskazywać rzeczywisty węzeł. Karta pokazuje jego ścieżkę,
nazwę i licznik poddrzewa. Rola ma zawsze status **propozycja do potwierdzenia**.
Brak kandydatów daje jawny brak mapowania. Liczniki poddrzew mogą się nakładać,
więc ich nie sumujemy. Fizyczne części CAD obejmują też modele urządzeń i
pozostałe bryły — to nie zakupowy BOM.

PASS dotyczy integralności i kompletnego odczytu obrysów brył. Błędy historii
cech są liczone osobno; nie ukrywamy ich pod wynikiem pomiarów. Montaż pozostaje
standardem roboczym. W/D/H ma status NOT RUN w zakresie tego pakietu; karty nie
oceniają wcześniejszych prób ruchu prezentacyjnego. SKU, funkcje, wycięcia,
pasowanie, nośność i produkcja pozostają nieznane. Nie wyliczamy procentu
gotowości produkcyjnej.

HTML ma zakodowane dane tekstowe, nie ma skryptów ani zewnętrznych zależności.
Otwiera się lokalnie. Ponowne przygotowanie po zmianie decyzji wymaga nowego
folderu i nowej, jawnie przypiętej rewizji szkicu.

Testy `scripts/test_family_review.py` obejmują zmienione źródło/inwentarz,
nieznane ID, pustą mapę, zakaz nadpisania, rzeczywiste ścieżki/liczniki,
escapowanie HTML, nieznane pytania i odmowę automatycznego zatwierdzenia.

26.10.2026: 7 testów PASS. Wygenerowano pakiet siedmiu rzeczywistych modeli
z przypisaniem pytań Q01–Q26. Integralność wejść i odczyt 2829 obrysów części
PASS; role kandydatów pozostają niepotwierdzone. Dowody prywatne znajdują się
w `artifacts/night-research-20261026/architecture-family-review-*.json`.
