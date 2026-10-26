# Pomiar planera montażu bez CAD

`scripts/benchmark_working_mounts.py` mierzy trzy istniejące funkcje na jawnie
wskazanym inwentarzu i standardzie źródłowym. Nie otwiera IronCAD, nie korzysta
z COM, nie zapisuje ICS, nie zmienia modeli i nie przyspiesza kodu automatycznie.
To punkt odniesienia do późniejszych zmian, nie dowód czasu wykonania skrzyni.

## Uruchomienie

Z katalogu źródła, przygotowanym Pythonem projektu:

```text
python scripts/benchmark_working_mounts.py INWENTARZ.json STANDARD.json NOWY_KATALOG --component root/3249/1456 --delta 0 0 300 --repeats 5 --warmup 1
```

Ścieżka komponentu i wektor przesunięcia są obowiązkowe. Domyślnie wykonywane
są 3 pomiary i 1 rozgrzewka. Liczba pomiarów musi być całkowita z zakresu 1–20,
a rozgrzewek 0–5. Każdy plik wejściowy ma limit 64 MB. Istniejący katalog wyników
powoduje odmowę — raport zapisuje się w nowym `benchmark.json`.

Najpierw następuje nietaktowana walidacja SHA, pełnego standardu i komponentu.
Błędny inwentarz, wersja lub plan nie uruchamiają pomiaru ani nie tworzą katalogu
wynikowego. Ta kontrola już wykonuje funkcje; rozgrzewka nie jest więc pomiarem
zimnego startu interpretera czy pierwszego wczytania modułu.

## Co dokładnie mierzymy

| Funkcja | Zakres wywołania |
| --- | --- |
| `build_working_standard` | Parsowanie przypiętych bajtów i budowa roboczej referencji, walidacja hierarchii i ram |
| `validate_working_standard` | Ponowna budowa ze źródłowych bajtów i porównanie danych standardu |
| `plan_component_translation` | Wymagane powyższe powiązanie, walidacja i obliczenie ruchu wskazanego poddrzewa |

Dla każdej funkcji raport zawiera próbki oraz minimum, medianę i maksimum:
czas ścienny przez `perf_counter`, czas CPU procesu przez `process_time`.
Rozgrzewka i właściwe pomiary są oddzielne. **Nie sumujemy tych trzech funkcji**
jako czasu całego procesu: plan zawiera własną walidację. Czasy nie obejmują
odczytu plików, sprawdzania wyników po wywołaniu, generowania raportu ani CAD.
Na krótkich odcinkach pomiar CPU może mieć zauważalną ziarnistość systemową.

Przed i po pracy sprawdzane są bajty obu wejść oraz SHA plików kodu benchmarku
i planera. Każda iteracja musi dać identyczne dane planu/standardu, a obiekt
wejściowy standardu pozostać niezmieniony. Raport zapisuje wersję Pythona,
implementację, platformę, hashe wejść/kodu, liczby węzłów i części. Nie zbiera
nazwy użytkownika, hosta, zmiennych środowiska ani kluczy/API. SHA źródłowego
ICS jest wyraźnie oznaczony jako deklaracja z inwentarza — sam ICS nie jest czytany.

Zgodność próbek dowodzi deterministyczności tego konkretnego wejścia. Nie dowodzi
poprawności montażu, nośności, braku kolizji ani gotowości produkcyjnej. Zmiana
kodu lub danych wymaga nowego katalogu wyników. Porównania należy prowadzić na
tych samych wejściach i z odnotowaniem obciążenia komputera; pojedyncza szybsza
próbka nie stanowi dowodu optymalizacji.

## Pierwszy punkt odniesienia — 26.10.2026

Prywatny przebieg M02: 233 węzły, 162 części, wskazana czapka
`root/3249/1456`, przesunięcie `[0, 0, 300]` mm. 172 przemieszczane węzły
obejmują zespoły i części — nie jest to liczba fizycznych okuć.
1 rozgrzewka + 5 pomiarów, niezmienność wejścia i powtarzalność wyników PASS.

| Funkcja | Mediana czasu ściennego | Minimum–maksimum |
| --- | ---: | ---: |
| Budowa standardu | 20,47 ms | 19,87–20,85 ms |
| Walidacja ze źródłem | 27,07 ms | 26,40–29,53 ms |
| Plan translacji wraz z walidacją | 40,57 ms | 40,45–42,07 ms |

Wynik: `artifacts/night-research-20261026/wing-offline-benchmark-01/benchmark.json`.
To historyczna próbka przypięta do kodu i danych w raporcie, nie próg wydajności
ani obietnica podobnego czasu w IronCAD. Pomiary natywne: **NOT RUN**.

Testy `scripts/test_mount_benchmark.py`: odmowa przed pomiarem przy innym SHA
lub wersji, granice liczby powtórzeń, oddzielne próbki rozgrzewki, poprawne liczbowe
czasy bez asercji konkretnej szybkości, ochrona wejścia i odmowa nadpisania raportu.
