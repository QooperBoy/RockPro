# Rzetelne etapy, podgląd i pomiary procesu

Przyrost z 26.10.2026 rozszerza istniejący obserwator. Nie steruje IronCAD,
nie zapisuje ICS, nie migruje SQLite i nie tworzy drugiej bazy projektu.

## Naprawione rozbieżności

- Zbiorcze `case.create=passed` nie odsłania już wszystkich planowanych części,
  jeśli istnieje szczegółowy strumień `native.create` z brakami lub błędami.
  Późniejszy nieznany wynik tego samego ID nie zachowuje starego sukcesu.
- Błąd jednego elementu pozostaje błędem etapu po sukcesie kolejnego elementu.
  Statusy częściowe/nieznane są pokazywane jako niepełne. Niedomknięte rozpoczęcie
  operacji nie staje się sukcesem wskutek zakończenia innego `operation_id`.
- Sąsiedni `native_progress.jsonl` nie jest dowodem dla modelu tylko z powodu
  położenia w tym samym katalogu. Powiązany wpis musi wskazywać ID operacji
  z podglądu i SHA bajtów tego podglądu. Natywne wpisy bez powiązania pozostają
  widoczne w dzienniku z ostrzeżeniem, ale nie potwierdzają utworzenia części.
- Zbiorcze fazy muszą należeć do jednego przebiegu loggera powiązanego z SHA
  podglądu. Dopisany obcy sukces nie zasłania błędu właściwego przebiegu.
- Niepoprawny/brakujący czas, niepełny wpis oraz brak czasu trwania nie są
  zamieniane na poprawne zero. Odczyt ogranicza rzeczywiste bajty, nie tylko
  rozmiar sprawdzony przed otwarciem pliku.

**Granica integracji:** obecny `NativeSceneBridge.Progress` nie emituje jeszcze
ID operacji i SHA podglądu. Jego dotychczasowe szczegółowe logi są zatem jawnie
niepowiązane. Nie dopisano im fikcyjnego pochodzenia i nie zmieniono mostu CAD
w tej rundzie. Pełna integracja producenta śladu pozostaje osobnym przyrostem
z próbą natywną. `visible_elements` jest helperem dowodowym; obecny obserwator
nie rysuje odrzuconych obrysów, a rzeczywisty model 3D pozostaje osobnym eksportem.

## Pomiary dostępne teraz

`process_observer.summarize_events` podaje dla każdego istniejącego etapu:
liczbę zakończonych i zmierzonych operacji, błędy, sumę zarejestrowanych odcinków,
medianę i maksimum. Osobno pokazuje dziesięć najdłuższych wywołań, zakres
znaczników czasu oraz liczbę zakończonych wywołań według wykonawcy.

Suma odcinków w etapie nie jest czasem całego procesu ani CPU. Faza SDK zawiera
podetapy; tych sum nie dodajemy do siebie. Okno między pierwszym a ostatnim
znacznikiem czasu nie obejmuje brakujących zdarzeń ani czasu sprzed logowania.
Znacznik bez strefy czasowej nie jest traktowany jako UTC. Liczba wywołań
`actor=agent` nie oznacza liczby interwencji konstruktorskich.

Udział automatyzacji, interwencje, tokeny i koszty pozostają `null`, dopóki nie
ma pełnego pomiaru pochodzenia decyzji. Nie wyliczamy ich ze słowa `script`.

## Przenośny raport bez uruchamiania obserwatora

```text
python scripts/report_process.py <ślad.jsonl> <nowy-katalog-raportu>
```

Powstają `summary.json` i polski `index.html`, działający bez internetu.
Raport zawiera SHA odczytanych źródeł. Zmiana wejść w trakcie odczytu blokuje
eksport; istniejący katalog nie jest nadpisywany. Dynamiczne teksty w HTML są
escapowane. To lokalny raport programistyczny, nie odbiór konstrukcji.

Podsumowanie w oknie Tk pokazuje zakres zarejestrowanych zdarzeń i wykonawców.
Zmiana źródła Pythona nie przeładowuje już działającego procesu obserwatora.

## Weryfikacja

Testy obejmują błąd przykryty sukcesem, brakujące części, obcy przebieg,
niepowiązany natywny ślad, różne ID operacji, puste znaczniki czasu, overflow,
zagnieżdżone czasy, brakujące dane autorstwa, XSS w HTML, ochronę istniejącego
raportu oraz zmianę źródła podczas eksportu. Testy raportu i paczek źródłowych
są od teraz częścią zwykłego `scripts/Verify.ps1`.

Testy jednostkowe i odczyt historycznego śladu są oddzielnymi dowodami od nowego
wykonania CAD. Ten przyrost nie zawiera nowego uruchomienia CAD ani odbioru
działającego okna obserwatora w IronCAD. Końcowe wyniki i ścieżki dowodów:
[raport nocnej pracy](NIGHT_WORK_20261026.md).
