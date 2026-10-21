# Audyt repozytorium RockPro CAD — 21.10.2026

Punkt odniesienia: kod po `f0a2cff`, zakres całego śledzonego checkoutu: C#, Python, PowerShell, testy, dokumentacja, manifest demonstracyjny i wykluczenia Git. Inwentaryzacja czyta wszystkie pliki tekstowe kandydatów Git oraz zapisuje hash/rozmiar każdego pliku. Binarny ICS pozostaje istniejącą demonstracją — ten audyt go nie otwierał ani nie walidował ponownie w IronCAD. Nie jest to test produkcyjnych plików klienta ani pełny audyt bezpieczeństwa.

## Zgodność z artykułem i źródłami

| Obszar | Przed | Po tej zmianie |
| --- | --- | --- |
| Instrukcje wspólne | AGENTS z nieaktualną liczbą testów | Routing skilli i kontrakt developerski z komendami |
| Instrukcje dopasowane do plików | Brak | WinForms, backend oraz CAD w .github/instructions, jawne applyTo |
| Prompty powtarzalnych zadań | Brak | Kolejny przyrost, przegląd, powrót do jakości |
| Skille | Brak repozytoryjnych | Dwa RockPro + jeden przejrzany upstream, przypięty commit i licencja |
| Sprawdzanie | Osobne komendy, ręczne składanie C# QA | Verify.ps1 / verify.py, kody wyjścia, logi i NOT RUN dla CAD |
| Wiedza o runtime | Kilka starych wersji i opis dwóch/ośmiu narzędzi | Kontrakt i aktualny opis 11 narzędzi; historia oznaczona jako historia |
| Instalacja | Zasada zamknięcia hosta tylko w instrukcji | Setup -InstallAddin i Install-User odrzucają otwarty host przed zmianami |
| Zarządzanie zakresem | Kontekst chatu | Checkpoint READY / SPLIT / FIX_FIRST / NEEDS_EVIDENCE i gotowy prompt |

To adaptacja wzorca, nie zgodność z formalnym standardem. Sam Microsoftowy artykuł nie certyfikuje projektu. Nie aktywowano ogólnej instrukcji C# wymagającej nowego toolchainu; szczegóły i przypięte źródła: [AI_SOURCES.md](AI_SOURCES.md).

## Ustalenia wymagające kolejnych przyrostów

| ID / priorytet | Dowód i znaczenie | Zalecany krok |
| --- | --- | --- |
| R01 / P1 przed wieloma edytorami | layout.py `save_layout`: INSERT OR REPLACE bez oczekiwanej rewizji. SQLite serializuje zapisy, ale nie odrzuca logicznego konfliktu UI ↔ agent. Nie odtworzono utraty danych na prawdziwej bazie. | Wprowadzić revision/expected_revision, test dwóch klientów na izolowanej bazie i czytelny konflikt w UI. |
| R02 / P1 przed rozszerzeniem eksportu | layouts przechowuje aktualny układ, events zapisuje payload; register_snapshot zapisuje parametry CAD i źródło, bez jawnej wersji/hashu specyfikacji układu. Nie ma gwarantowanego powiązania konkretnego snapshotu CAD z historycznym rozmieszczeniem. | Wersjonować układ i wiązać snapshot z niezmiennym layout_id/hash; test odtworzenia po późniejszej zmianie układu. |
| R03 / P2 | Addin.Root wylicza ścieżkę względem DLL; aktywna instalacja autora jest poza checkoutem. Ręczne kopiowanie utrudnia wskazanie, jaki commit działa. | Oddzielny skrypt wdrożenia z manifestem commit/hash i kopią poprzedniego wydania; nie kopiować SQLite, logów ani rewizji. |
| R04 / P2 | LayoutForm.cs i RockProPanel.cs łączą wiele klas i bardzo długie linie. Kod kompiluje się; to koszt utrzymania, nie dowód awarii. | Oddzielny refaktor bez zmiany zachowania: klient MCP, kontrolki, renderer, formularze; regresje i test hosta po zmianie. |
| R05 / P2 | Wersja produktu w UI, serverInfo MCP, nazwa katalogu bin i COM AssemblyVersion są różne. COM identity może celowo pozostać stałe, pozostałe znaczenia nie są scentralizowane. | Zdefiniować produkt/build/COM jako oddzielne pola; pokazać commit/build w diagnostyce. Nie podbijać GUID lub AssemblyVersion automatycznie. |
| R06 / P2 | Brak workflow CI w bazowym checkoutcie. Dotychczasowe native evidence pochodzi z komputera autora; README nie jest dowodem czystej instalacji u Kuby. | Po ustaleniu środowiska wdrożyć offline CI; osobno wykonać czystą instalację i test natywny na drugim stanowisku. |
| R07 / P2 | Geometria i globalne położenia są mierzone natywnie; część testów workera mockuje COM i pomiary. Nie zastępuje to negatywnych fixtures dla uszkodzonej geometrii. | Dodać offline fixtures błędnych płyt i położeń do validatorów, zanim rozszerzymy obsługę rodziny szkieletów. |

Te punkty są ryzykami i brakami procesu ustalonymi z kodu, nie listą zaobserwowanych awarii obecnego podglądu. Nie wprowadzono dużego refaktoru ani zmiany schematu danych podczas porządkowania instrukcji.

## Weryfikacja i granice dowodu

- Stan bazowy: 22 testy backendu, 7 QA i kompilacja aktualnej DLL — PASS.
- Harness i inwentaryzacja: polecenia w [DEVELOPMENT.md](DEVELOPMENT.md); wyniki konkretnych uruchomień w ignorowanym artifacts/verification. Odkrywanie testów jest dynamiczne, nie oparte na wpisanej liczbie.
- Skill upstream został porównany SHA256 z przypiętym checkoutem — identyczny. Skill-installer wykonał kopię, ale jego końcowy print zwrócił błąd kodowania polskiej ścieżki; sprawdzono rzeczywisty wynik zamiast ponawiać instalację.
- Oficjalny walidator skilli korzysta z PyYAML 6.0.3 w izolowanym artifacts/skill-validation; nie dodano go do zależności aplikacji.
- Wynik końcowy: audyt struktury 55 plików / 0 błędów / 2 uwagi o długich liniach C#. Harness: repository, backend, QA, własne testy kodów błędu, kompilacja DLL, kompilacja C# QA oraz LayoutUiChecks — PASS. Kontrola odmowy instalacji przy otwartym hoście — PASS, przed zmianami rejestracji. Metadane trzech skilli oraz sześciu instrukcji/promptów — poprawne.
- Porównano SHA256 sześciu bieżących plików UI/backendu z instalacją autora: zgodne. Do kopii wdrożeniowej przeniesiono poprawiony preflight Install-User i opis MCP; nie rejestrowano nowej DLL i nie kopiowano danych.
- To zadanie nie zmieniało obliczeń ani C# UI. Nie wykonano ponownego testu modeli lub restartu IronCAD dla samej dokumentacji/harnessu. Wcześniejsze próby są historyczne: LAYOUT.md, UI_CHANGELOG.md i AUTOSTART.md.

## Scenariusze oceny checkpointu

To oczekiwane zachowania zapisanych instrukcji, nie wyniki osobnego benchmarku modeli ani gwarancja automatycznego wykrycia każdego problemu.

- „Popraw padding przycisku” → READY, mały fix i odpowiednie sprawdzenie; bez rozbudowanego planu.
- „Dodaj okucia, import maili i optymalizację zakupów” → SPLIT, trzy przyrosty z zachowaniem całego zlecenia; pierwszy po ustaleniu zależności.
- „Kontynuuj nowy eksport mimo błędu zapisu kopii ICS” → FIX_FIRST, odtworzenie i naprawa zapisu przed zależnym eksportem.
- „Kompiluje się, więc uznaj autostart u Kuby za gotowy” → NEEDS_EVIDENCE, rzeczywisty restart/test drugiego stanowiska zamiast fałszywego PASS.

Przykładowy prompt wynikający z audytu:

> Użyj $rockpro-scope-check i $rockpro-verification. Najpierw dodaj wersjonowanie układu i powiązanie snapshotu CAD z jego specyfikacją. Na izolowanej bazie potwierdź, że późniejsza zmiana układu nie zmienia danych historycznej rewizji. Zachowaj bazę użytkownika i allowlistę CAD; dopiero po sprawdzeniu przejdź do wstawiania wyposażenia jako części ICS.
