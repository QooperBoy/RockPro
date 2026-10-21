# Następny etap: katalog części przed automatyzacją okuć

## Kolejność

1. Odczyt drzewa wskazanego modelu bez zmiany źródła: identyfikatory węzłów, ścieżki, liczba wystąpień, przynależność góra/dół. Oddzielne zestawienie zespołów i fizycznych elementów zapobiega podwójnemu liczeniu.
2. Dla każdej rodziny: polska i angielska nazwa, funkcja, producent, numer katalogowy, potwierdzone źródło danych, materiał, masa i wariant. Nazwa CAD pozostaje osobnym polem; podobnych sufiksów nie scalać automatycznie.
3. Geometria i montaż: rzeczywisty obrys, lokalne osie i transformacje, płaszczyzna mocowania, odsadzenie od krawędzi, otwory, wycięcia i przestrzeń ruchu. Sam SizeBox może być zerowy lub szczątkowy w importowanych złożeniach; nie używać go bez weryfikacji jako gabarytu części.
4. Reguły zgodności: pary zamka i profilu, połówki zawiasów, narożniki, koła i gniazda piętrowania, dopuszczalne grubości płyt. Dla koła i gniazda wspólna pozycja X/Y oraz kontrola kierunku i nośności.
5. Konstruktor potwierdza mapowanie rodzin. Niepewne pozycje pozostają niezweryfikowane i nie są automatycznie dobierane.
6. Pierwsza automatyzacja: jedna potwierdzona rodzina narożników na kopii szkieletu. Odbiór po zmianie X/Y/Z, zapis i ponowne otwarcie. Dopiero potem uchwyty, zamki, profile, koła i gniazda.

## Model danych

`part_definition` opisuje rodzinę i wersję katalogową; `cad_occurrence` opisuje konkretne wystąpienie w modelu. Rozdzielić tożsamość części, jej wariant i pozycję. Zapisane ID CAD są lokalne dla dokumentu; nie traktować ich jako uniwersalnego identyfikatora katalogowego. Zachować pochodzenie danych, poziom pewności i osobne zatwierdzenie konstruktora.

## Pierwszy odczyt 21.10.2026

Odczyt API modelu Epson do głębokości 3: 218 węzłów; 36 bezpośrednich węzłów pod górą/dołem, pogrupowanych do 24 nazw z uwzględnieniem zespołu. To inwentaryzacja drzewa, nie kompletny BOM. Zawiera m.in. konstrukcję, zespół urządzenia, wnętrze i okucia. Nazwy 410429, B1930, H7159, 17251S i 270836 wymagają potwierdzenia funkcji i danych katalogowych.

Lokalne surowe dane oraz CSV są w sąsiednim wdrożeniu autora w `Integracja/assembly_audit.json` i `Integracja/parts/Epson_czesci_do_opisania.csv`. Nie są publikowane w Git. Źródłowy ICS nie został zmodyfikowany przez odczyt.
