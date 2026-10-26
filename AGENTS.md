# Instrukcje dla agenta pracującego nad RockPro CAD

26.10.2026, późniejszy checkpoint: własna Scene14 w 2023 ma poprawiony montaż
i polskie parametry; natywna zmiana wymiarów oraz powrót PASS. Czytaj
[docs/T1_2023_MOUNTING_REPAIR.md](docs/T1_2023_MOUNTING_REPAIR.md).
Nie używaj historycznego prepare_unsaved.py z artifacts jako poprawionego generatora.
To wąski prototyp, nie rozszerzenie kontraktu MCP ani dowód otwierania każdego T1.
Poniższy opis Shape Load Failed dotyczy wcześniejszej próby źródła.

Najpierw przeczytaj docs/DEVELOPMENT.md. Bieżący zakres: LAYOUT.md; instalacja: HANDOVER.md i AUTOSTART.md. To natywny dodatek WinForms / .NET Framework x64, Python MCP stdio i SQLite. Docelowy host odbiorcy: IronCAD 2023 (25.0); historyczny host: 2027 (29.0). Build/autostart i podstawowy test natywny 2023 PASS; pełny generator T1 wymaga portowania. Lokalny host zaktualizowano do 2023 PU1 SP1 (25.0.12.18734). T2 przeszedł natywny odczyt i zapis/otwarcie; T1 nadal zgłasza Shape Load Failed mimo metadanych 18734. Nie uznawaj samych metadanych za dowód otwieralności. Czytaj docs/IRONCAD_2023_COMPATIBILITY.md. Nie przenoś go na ASP.NET, React ani nowy .NET w ramach zwykłej zmiany funkcji.

Priorytet użytkownika dla obecnego MVP (22.10.2026): szybki działający prototyp do ręcznego obejrzenia. Wykonuj podstawowe kontrole rozmieszczenia/symetrii całych okuć, zmiany wymiarów oraz zapisu/otwarcia; następnie przekaż model użytkownikowi. Nie dokładaj kolejnych zestawów testów, szczegółowych audytów BRep ani wielokrotnych pełnych regresji bez konkretnego błędu lub nowego wymagania. Zachowaj istniejące testy i ochronę źródeł, kopii oraz zapisów. Wygląd ocenia użytkownik; dalsze testowanie i debugowanie wynika z jego uwag.

Przy zmianie kodu lub dokładaniu funkcji użyj lokalnego skillu [.agents/skills/rockpro-scope-check/SKILL.md](.agents/skills/rockpro-scope-check/SKILL.md). Przy prostej poprawce wystarczy krótka ocena, bez osobnego zatwierdzania. Jeśli zakres rośnie, występuje błąd lub brakuje dowodu integracji, pokaż konkretny checkpoint i gotowy prompt powrotu do naprawy/weryfikacji. Sam wykonaj możliwe naprawy i kontynuuj autoryzowane, niezablokowane prace.

Kod zmieniaj w tym checkoutcie. Katalog ../Integracja jest osobnym lokalnym wdrożeniem z własną bazą i konfiguracją.

Nowe projekty: stosuj [docs/CASE_DEFAULTS.md](docs/CASE_DEFAULTS.md): zielonkawa sklejka RGB(64,128,128), płytka parametryczna pokrywa, zwykle 10–15% wysokości korpusu, minimum montażowe zawiasu; większa proporcja tylko jako jawne odstępstwo konstruktora. Nie zmieniaj historycznych plików ani raportów w celu zastosowania nowych domyślnych wartości.

- Uchwyty do podnoszenia: domyślnie po dwa na dwóch przeciwległych ścianach prostopadłych do ściany zawiasów. Konstruktor może wybrać po jednym, wyśrodkowanym na każdej (łącznie 2). Zapisuj handles_per_wall=1 lub 2, nie myl z liczbą łączną. Natywne pozycje muszą reagować na gabaryt; gotowych okuć nie skaluj. Szczegóły w docs/CASE_DEFAULTS.md.
- Zachowaj strukturę Integracja: frontend wylicza położenie .venv względem DLL, worker względem pliku Python.
- Setup.ps1 instaluje zależności, konfiguruje ścieżki i buduje. Parametr -InstallAddin dodatkowo rejestruje HKCU. Rejestracji nie wykonuj podczas pracy IronCAD z niezapisanymi dokumentami.
- Nie kopiuj ścieżek autora z historycznych raportów. Uruchom configure.py w nowym położeniu paczki.
- Przed istotną zmianą sprawdź bazowy stan odpowiednich testów; po niej uruchom adekwatne sprawdzenia według [.agents/skills/rockpro-verification/SKILL.md](.agents/skills/rockpro-verification/SKILL.md). Polecenie: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1. Opcje -WithAddinBuild -WithUiChecks dodają kompilację i regresje formularzy. Wybór Pythona opisuje docs/DEVELOPMENT.md; nie utrzymuj stałej liczby testów jako bramki.
- Nie uznawaj testów bez CAD za test natywnej integracji. Sprawdź osobno odczyt, zmianę na kopii, walidację, zapis/otwarcie ICS, SQLite i snapshot.
- Zmiany CAD wyłącznie na nowej kopii. Zachowaj allowlistę sześciu parametrów, granice, kontrolę liczb, blokadę współbieżności, kontrolę źródła i walidatory geometrii.
- Nie rozszerzaj obsługi na dowolny ICS przez pomijanie kontroli manifestu/identyfikatorów. Aktualny model to 10 płyt, dwa zespoły.
- Nie nadpisuj snapshot.ics; kopia robocza i archiwum są oddzielne. Integralność to SHA256, nie gwarancja WORM.
- UI musi pokazywać brak backendu, a ręczny status nie może udawać automatycznej walidacji ani gotowości produkcyjnej.
- Nie przechowuj osobnej bazy projektów w C#. Frontend i klient AI mają korzystać z tych samych operacji MCP/SQLite.
- Nie dodawaj arbitralnego exec/eval lub shell do narzędzi MCP.
- MVP okuć operuje całym gotowym elementem: ID źródła, środek obrysu, orientacja, gabaryt, ściana i symetria grupy. Nie projektuj ani nie parametryzuj otworów, wierceń, nitów i szkiców wewnątrz okucia. Istniejąca historia modelu katalogowego pozostaje nieprzezroczysta dla planera; nie usuwaj jej przez zmianę geometrii źródła. Szczegółowy audyt BRep jest osobną, jawną diagnostyką, nie domyślną pętlą montażu.
- Wymagania ROC-41 z 26.10.2026: [docs/ROC41_CUTOUTS_AND_JOINTS.md](docs/ROC41_CUTOUTS_AND_JOINTS.md). Wycięcia dotyczą płyt i jawnie wskazanych profili, nie przebudowy wnętrza katalogowego okucia. Powiąż je z kotwą wystąpienia i wersją szablonu montażowego; bbox nie jest konturem. Pasowanie przekrojów i gabaryt oblicz przed CAD. Nie utożsamiaj szczeliny sklejki z luzem profili ani RP_DisplayGap; nie powiększaj skrycie skrzyni. Natywny prototyp 48 obróbek: [docs/T1_MACHINING_PROTOTYPE.md](docs/T1_MACHINING_PROTOTYPE.md). Powiązania działają przez parametry sceny; dowolny ruch TriBallem i zewnętrzny podgląd obróbek nie są jeszcze obsługiwane.
- Doprecyzowanie ROC-41: uwzględniaj skraj i przestrzeń ruchu zawiasu przy doborze uchwytu; nie usuwaj kolizji przypadkowymi dodatkowymi wycięciami. Biblioteka ma odróżniać wymagane wycięcie od braku danych. W rozszerzalnym podglądzie etap okucia obejmuje jego obróbki, lecz ukrycie okucia w gotowym modelu nie usuwa otworu. Szczegóły i przyszły transport bagażowy N01/N02 pozostają planem w dokumencie ROC-41.
- Po operacji zamykaj wyłącznie dokumenty CAD utworzone/otwarte przez tę operację; także w obsłudze błędu. Nie zostawiaj ukrytych kopii i prototypów w pamięci hosta. Przed zamknięciem zmodyfikowanego własnego prototypu zachowaj zmiany w nowej kopii; nie zamykaj oryginałów ani nieznanych dokumentów użytkownika. Nie aktywuj okien do sprzątania.
- Nie commituj .venv, danych klientów, baz SQLite, logów, rewizji i lokalnych konfiguracji. SDK i DLL dostawcy pochodzą z lokalnej instalacji IronCAD.
- UI: jasne tło, logo RockPro, pomarańczowe akcenty, polskie etykiety, tooltips, operacje asynchroniczne, wyraźny stan pracy i błędów. Tabele w osobnych oknach. Sprawdzaj DPI i przycinanie tekstów w prawdziwym IronCADzie.
- W raporcie rozróżnij kod zaimplementowany, test jednostkowy, test natywny oraz makietę bez backendu.
- Nowa kompilacja nie oznacza nowej DLL w działającym hoście. Rejestruj i przeładowuj po bezpiecznym zamknięciu IronCAD; zachowuj dane użytkownika. Wyniki sprawdzeń oznaczaj PASS / FAIL / NOT RUN.

