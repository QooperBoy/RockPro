> Aktualizacja 31.10.2026: część propozycji jest wdrożona — rejestr przebiegów
> w SQLite, panel Studio, pochodzenie operacji, interwencje i warstwa 3D.
> Zakres i ograniczenia: [RELIABILITY_AND_OBSERVER.md](RELIABILITY_AND_OBSERVER.md).
> Poniższy opis zachowuje historyczną propozycję; nie oznacza wdrożenia wszystkich punktów.

# Propozycja: panel przebiegu i kontroli produktu RockPro

Status: pomysł do oceny, nie zaimplementowany interfejs. Prośba użytkownika
24.10.2026: widoczność pracy skryptów, agentów i logicznych etapów procesu.

## MVP poza IronCAD

Lokalny rejestr zdarzeń i odczytowy panel z osią czasu oraz prostą bryłą skrzyni.
Replay dodaje płyty, profile i symbole okuć według zakończonych etapów.
Nie musi renderować BRep ani zastępować CAD. Każdy etap i element mają jawne
pochodzenie: reguła/skrypt, propozycja agenta, decyzja lub poprawka konstruktora.
Kolory mają etykiety, aby znaczenie nie zależało wyłącznie od barwy.

Etapy: wymagania → układ → płyty → profile → okucia → kontrola → zapis/wydanie.
Dla każdego: wejściowa/wyjściowa rewizja, reguła i wersja kodu, status,
czas, liczba prób, wynik sprawdzeń, przyczyna interwencji, odnośnik do artefaktu.
Oddzielić aktora uruchamiającego skrypt od autora decyzji projektowej.
Skrypt napisany doraźnie przez agenta nie dowodzi samodzielnej automatyzacji.
Brak danych o modelu, tokenach lub koszcie pozostaje brakiem danych.

Mierzyć oddzielnie czasy planera, wywołań SDK/COM, regeneracji, grafiki,
zapisu/otwarcia i oczekiwania na użytkownika. Liczyć interwencje i powody
(np. brak reguły, konflikt geometrii, błąd programu, zmiana wymagania).
Udział etapów bez interwencji pokazywać wraz z jawnym mianownikiem; nie mieszać
go z udziałem czasu czy procentem kodu napisanego przez AI.

## Wykorzystać to, co już istnieje

parts/operation_log.py ma ograniczony JSONL z aktorem, modelem i hashami.
mcp/core_service.py ma wspólną bazę oraz dziennik operacji i wersji.
Raporty generatorów i harnessu zawierają pomiary i wyniki, lecz nie tworzą
jeszcze jednego pełnego śladu wszystkich etapów. Potrzebny wspólny schemat
zdarzeń i adaptery, nie druga baza projektów ani otwarte logowanie całego CAD.
Zachować limity i allowlisty metadanych; dane geometrii do podglądu mają osobny
jawny, lokalny kontrakt z uproszczonymi elementami i stabilnymi ID.
Nie dopisywać zmyślonej historii interwencji do dawnych raportów.

Pierwszy panel tylko odczytuje zapisany przebieg. Później kontrolowane bramki:
zatrzymaj po etapie, zatwierdź propozycję, ponów operację, wróć do rewizji.
Muszą korzystać z istniejącego CAS i dziennika; replay nie wykonuje ponownie CAD.

## Ownership produktu i procesu

- Wersjonowane wymagania i kryteria odbioru dla rzeczywistych skrzyń.
- Wzorce akceptacyjne EB-L630U i warianty: mały/duży gabaryt, jeden/dwa uchwyty,
  pokrywa i odstępstwo konstruktora, zapis/otwarcie oraz ręczna korekta.
- Dziennik decyzji: co, dlaczego, kto zatwierdził i jakie są granice automatyki.
- Każde wydanie ma opis zmian, znane ograniczenia, dowody i odwracalną rewizję.
- Projekt i podstawowy przebieg mają być odtwarzalne z konfiguracji i skryptów,
  a własne pliki dostępne także bez aktywnej rozmowy z agentem.
- Oddzielić odbiór kodu/testów od odbioru konstrukcji i dopuszczenia do produkcji.

Astra High może najpierw wykonać niezależny audyt architektury i zaproponować
punkty pomiarowe. Optymalizacja powinna wynikać z profilu konkretnego przebiegu,
ze spodziewanym zyskiem i pomiarem przed/po. Audytu ani panelu nie uruchomiono.
