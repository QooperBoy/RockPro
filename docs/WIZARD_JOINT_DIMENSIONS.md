# Studio — wymiary korpusu i wynik dopasowania złączy

27.10.2026. Szczelina nie jest swobodnym parametrem powiększającym skrzynię.

- XYZ w obecnym kreatorze oznaczają wymagane wnętrze **samego korpusu**.
  Pokrywy mają osobną wysokość/głębokość. Nie nazywamy tych XYZ światłem całej
  zamkniętej konstrukcji; obok pokazujemy osobno jej nominalny gabaryt.
- `korpus_zewnętrzny = wnętrze_korpusu + 2 × grubość_sklejki` dla każdej osi.
  W koncepcyjnym układzie pokrywa zaczyna się na nominalnej płaszczyźnie złącza.
  Nie dodajemy ręcznej szczeliny do położenia ani rozmiaru sekcji.
- W wariancie 3-elementowym wysokość przodu wynosi wysokość zewnętrzną korpusu
  plus wysokość górnej pokrywy. Obie górne płaszczyzny nadal licują.

Szczelina montażowa i cofnięcie/docięcie sklejki mają być **wynikami** doboru
konkretnego okucia/profilu i jego wersjonowanej geometrii montażowej. Nie należy
utożsamiać szczeliny między płytami z luzem metal–metal ani z odjęciem tej samej
liczby od obu płyt. O tym decyduje szablon połączenia i osadzenie profilu.
Reguły planowania i obróbek: [ROC41_CUTOUTS_AND_JOINTS.md](ROC41_CUTOUTS_AND_JOINTS.md).

W krokach 1–3 okucia nie są jeszcze wybierane. Dlatego podsumowanie pokazuje
„do ustalenia po wyborze okucia”; API zwraca `gap_mm=null`,
`plywood_trim_mm=null`, `fit_status=awaiting_hardware`. To nie jest zero ani
zatwierdzony wynik obróbki. Płyty podglądu są nominalne
(`panel_dimensions_status=nominal_not_cutting`), nie formatkami produkcyjnymi.
Dokładnego wyliczania szczeliny z biblioteki części ten przyrost nie wdraża.

Przyszły adapter montażu ma dopasować i dociąć płyty wewnątrz ustalonego
gabarytu, zachowując wymagane wnętrze. Brak danych montażowych albo sprzeczność
wymiarów blokuje wykonanie; nie zwiększa po cichu skrzyni i nie zgaduje naddatku.

Format `rockpro.configurator/3` nie zawiera wejściowego `joint_gap_mm`.
Podanie go jest odrzucane. Drafty v1/v2 są zachowane; jawna konwersja tworzy
nową koncepcję, pomija dawną ręczną szczelinę i pozostawia dopasowanie okuć
nieustalone. Stare klucze odzyskiwania przeglądarki i rekordy nie są nadpisywane.

PASS: testy jednostkowe, SQLite i przeglądarka — odrzucenie ręcznej szczeliny,
identyczny nowy gabaryt po konwersji różnych dawnych wartości, licowanie płyt,
zachowanie XYZ korpusu, podsumowanie, zapis/odczyt i JSON v3. Prywatne dowody:
`artifacts/wizard-joint-result-20261027/`. Pełna regresja:
`artifacts/verification/20261027T144729496423Z/`.
CAD/native i produkcyjne docięcie z wybranego SKU: NOT RUN, poza zakresem.
