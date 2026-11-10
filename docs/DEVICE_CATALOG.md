# ROC-23 — katalog urządzeń ze źródłami

Katalog urządzeń działa w tej samej SQLite co projekty. To dane wyposażenia,
nie katalog okuć i nie zgoda produkcyjna. Identyfikator wynika z jawnej trójki
producent / model / wariant. Podobne nazwy i warianty nie są scalane.

## Narzędzia UI/MCP

- preview_device_record(record): czysta walidacja i rozliczenie obserwacji.
- save_device_record(record, expected_revision): zapis niezmiennej wersji z CAS.
- get_device_record(catalog_id, revision=None): bieżąca lub historyczna wersja.
- draft_device_inquiry(record): projekt pytania o braki/sprzeczności. Nie wysyła.

Schemat v1: manufacturer, model, variant, axes, sources i observations.
Każdy pomiar ma field X/Y/Z/mass, value, unit, source_id i confirmation.
Jawne osie: X=width, Y=depth, Z=height. mm/cm/m oraz g/kg są normalizowane;
innych jednostek nie zgadujemy. Źródło ma rodzaj, odnośnik, lokalizator strony/
sekcji i SHA256 zachowanej treści. Status potwierdzenia jest zachowaną deklaracją
pochodzenia, nie uwierzytelnionym podpisem konstruktora.

Brak wartości pozostaje null/missing. Różne odczyty pozostają w obserwacjach,
a rozstrzygnięta wartość jest null/conflict. Nie wybieramy automatycznie
wygodniejszego wymiaru. Pole z niepotwierdzoną obserwacją nie uzyskuje statusu
source_checked. dimensions_ready dotyczy trzech wymiarów; nie oznacza odbioru
transportowego, wytrzymałości ani dopuszczenia akcesoriów.

## Odczyt źródeł

scripts/Extract-DeviceSource.py czyta EML (jawny tekst), PDF (pypdf) i UTF-8 TXT.
Zachowuje tekst z numerem strony/sekcji i SHA źródła, nie modyfikuje wejścia.
Dane z załączników nie są wykonywane. HTML bez tekstowego korpusu oraz skany
bez tekstu wymagają oddzielnego odczytu; nie są uzupełniane domysłami.

Przykład uruchomienia przy użyciu udokumentowanego Pythona z pypdf:

    python scripts/Extract-DeviceSource.py --source <plik.pdf> --output <nowy-raport.json>

Ekstrakcja nie zatwierdza automatycznie żadnej wartości. Po niej należy wskazać
właściwy wariant produktu, osie i lokalizator. Markery internal/external są
zachowywane, żeby obrysy skrzyni nie stały się wymiarami samego urządzenia.

## Próba lokalna

Odczytano sześciostronicowy T_1/Epson EB-L630U_Dokumentacja.pdf i tekst Temat II.eml.
Oba źródła bez zmian; wyniki wyłącznie w prywatnym artifacts/overnight-20261024.
PDF opisuje m.in. gabaryty skrzyni, a nie dostarcza potwierdzenia wymiarów
urządzenia. Nie przepisano tych obrysów do katalogu projektorów.

Oficjalna strona Epson dla EB-L630U, SKU V11HA26040:
https://www.epson.eu/en_EU/products/projector/professional/eb-l630u-projector/p/31706
Sekcja General podaje Width × Depth × Height: 440 × 339 × 136 mm oraz masę 8.4 kg.
Sprawdzono 24.10.2026. Zachowano krótki fragment źródła z hashem. Rekord v1
zapisano w lokalnej wspólnej SQLite, bez zmiany projektów i ich rewizji.
Dowód: artifacts/overnight-20261024/epson-device-saved.json.

Testy: jednostki/źródła/osie, rozdzielenie wariantów, braki/sprzeczności,
niezmienne wersje i CAS, odmowa niewłaściwych jednostek i duplikatów — PASS.
Projekt zapytania zawsze ma sent=false i wymaga wysłania przez uprawnioną osobę.

Pełny harness po wdrożeniu: PASS, artifacts/verification/20261024T214134912003Z/results.json.
