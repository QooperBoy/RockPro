# Instrukcje dla agenta pracującego nad RockPro CAD

- Prototyp telewizyjny 2027: [docs/TELEVISION_PARAMETRIC_PROTOTYPE.md](docs/TELEVISION_PARAMETRIC_PROTOTYPE.md).
  Kontur kołnierza nie zastępuje HWDrill właściwego okucia. Badaj ramę operacji
  razem z ramą części, używając różnych przyrostów wysokości i głębokości.
  Widoczność kompletnego modelu sprawdzaj również przez IsHidden części/zespołów;
  same ogólne flagi stanu nie potwierdzają widocznego podglądu.

- Siatki producentów w Studio: [docs/SUPPLIER_MODELS_STUDIO.md](docs/SUPPLIER_MODELS_STUDIO.md).
  `assets/supplier-parts` jest przenośną biblioteką podglądu, bez danych klientów.
  Zachowaj SHA, skalę i oddzielne ID niezgodnych wariantów; nie myl siatki
  producenta z zatwierdzonym montażem/wycięciem. Nie wymagaj IronCAD do konwersji.

- Przenoszenie zestawu Penn/Adam Hall do 2027: [docs/REQUESTED_CASE_2027.md](docs/REQUESTED_CASE_2027.md).
  Nominalny wymiar otworu z katalogu może różnić się od gardzieli pobranego CAD;
  sprawdź rzeczywistą interferencję. Dopasowane łuki są przybliżeniem prototypu,
  nie oryginalnym splajnem ani zatwierdzeniem CNC. Nie używaj odczytu
  `GetBSplineDataCOM` przez bufory `out double` w hoście z pracą użytkownika:
  taka próba spowodowała awarię procesu. Eksperymenty z niezweryfikowanym
  marshallingiem prowadź tylko w osobnym pustym hoście po snapshotach.

- Studio kończy się krokiem 8 „Kontrola projektu”: wspólne `studio_review`,
  poziomy błędów/ostrzeżeń i odsyłacze do edycji konkretnej grupy. Nie utożsamiaj
  kontroli znanych obrysów 2D z odbiorem BRep/wycięć w CAD. Nie blokuj kopii JSON
  problemami geometrii ani brakiem sieci. Zapis na Vercelu jest w przeglądarce;
  nie opisuj go jako współdzielonej bazy serwerowej. Szczegóły: docs/STUDIO_VERCEL.md.

- Demo Vercel i zdjęcia producentów: [docs/STUDIO_VERCEL.md](docs/STUDIO_VERCEL.md).
  Publikuj tylko paczkę z jawnej allowlisty, nigdy checkout/artifacts w całości,
  firmowego Excela, SQLite, stanów ani modeli klientów. Ceny wymagają jawnej zgody;
  28.10.2026 użytkownik zatwierdził publikację pełnych 265 rekordów i podsumowania
  cenowego na istniejącym Vercelu. Zachowuj braki cen i jednostek, nie łącz wariantów
  ani nie utożsamiaj orientacyjnej sumy okuć z pełną ceną skrzyni. Zdjęcie musi pasować
  do pełnego SKU (z wariantem); kod w produktach polecanych nie identyfikuje zdjęcia
  głównego. Zachowaj siatkę CAD niezależnie od zmiany zdjęcia oraz źródło i SHA pliku.

- Ulubione i ranking Studio: [docs/STUDIO_PART_PREFERENCES.md](docs/STUDIO_PART_PREFERENCES.md).
  Preferencje zapisuj w lokalnej bazie; użycie to różne zapisane projekty,
  nie liczba otwarć lub rewizji. Nie łącz gwiazdek podobnych wariantów SKU
  ani nie utożsamiaj rankingu z montażem lub rozchodem magazynowym.

- Firmowy Excel i etap mini ERP: [docs/EXCEL_ERP_INTEGRATION.md](docs/EXCEL_ERP_INTEGRATION.md).
  Katalog firmowy to odczyt snapshotu, nie żywy stan ani zgoda CAD. Zachowuj
  puste wartości i zera, jednostki, warianty oraz zdublowane kody. Nie księguj
  zapisanych stanów jako nowych dostaw ani ponownie całej historycznej konsumpcji.

- Pełna konstrukcja w Studio: [docs/STUDIO_CONSTRUCTION.md](docs/STUDIO_CONSTRUCTION.md).
  Zachowaj opcjonalną receptę `construction`, wspólne `project_summary`, sztywne
  modele okuć i pary koło–gniazdo. Nie pokazuj samego wyboru katalogowego jako
  rozmieszczonej części. Kompletny podgląd Studio nie zatwierdza obróbek ani CAD.

- Organizacja nowych scen: [docs/CASE_STRUCTURE.md](docs/CASE_STRUCTURE.md).
  Stosuj sześć grup ze wspólnego rejestru; po grupowaniu odtwórz powiązania
  z planu i sprawdź zmianę wymiarów. Dla T1 zawias wymaga wycięcia w sklejce
  ORAZ przerwy w profilu. Wykonuj validate_t1_machining przed CAD i kontrolę
  rzeczywistych operacji po wykonaniu. Brak informacji o wycięciu blokuje
  przyjęcie nowego SKU. Nie traktuj otworu L905/915 jako szablonu 27095.

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
- Studio, 27.10.2026: użytkownik rozszerzył liczbę uchwytów do 1–16 na ściankę w grupie, z jawnym handles_per_wall i równym rozstawem/symetrią. Domyślnie pozostaje 2 na przeciwległych bokach. Reguła 1/2 powyżej opisuje stary natywny generator T1, nie limit Studio. Rzędy zawiasów wiąż z joint_id topologii; nie pozycjonuj ich dowolnie na ścianie ani nie obiecuj wycięć/pełnego ruchu na podstawie zdjęciowego znacznika. Patrz docs/STUDIO_INTERACTION.md.
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


- Studio, preferencja konstruktora 27.10.2026: pokazuj kompletne, pojedyncze części do montażu. Nie pokazuj źródłowych zespołów, rozrzuconych grup ani niekompletnych połówek jako gotowych części. Najpierw wyodrębnij i potwierdź kompletną jednostkę. Wielobryłowy model jednego kompletnego uchwytu/koła jest dozwolony; liczba brył nie oznacza liczby części. Zachowaj archiwalne dane i drafty, nie kasuj ich przy filtrowaniu prezentacji.

- Nawigacja Studio: stały sidebar Konfigurator / Biblioteka wzorców, oddzielony od pionowych etapów projektu. Nie wracaj do odsyłacza sugerującego zewnętrzną bibliotekę. Zachowuj draft, krok, kamerę i zaznaczenie przy przejściu i powrocie. Nawigacja 3D: standardowa kostka widoków z polskimi pełnymi etykietami, nie autorski kompas punktowy. Szczegóły: docs/STUDIO_NAVIGATION_REVIEW.md.

- Aktualna preferencja podglądu Studio: bez napisów na ściankach skrzyni. Kierunki wyłącznie na kompaktowej kostce widoków (96 px, mniejsze etykiety); nie przywracaj plakietek PRZÓD/TYŁ na geometrii.

- Studio: utrzymuj zwijanie paneli, regulację/minimalizację 3D i przełącznik jasny/nocny w nagłówku na obu ekranach. Sprawdzaj ciasne układy i długie podpisy na desktopie oraz mobile; preferencje układu/motywu są oddzielone od draftów. Patrz docs/STUDIO_PANELS_AND_THEME.md.

- Studio: menu ma tryby pełne/ikony/całkowicie ukryte i regulację szerokości. Ukryty podgląd 3D nie rezerwuje miejsca ani nagłówka; środkowy edytor wykorzystuje zwolnioną szerokość i responsywne kolumny. Nie przywracaj zbędnej informacji o jednym górnym wieku w kroku wyboru typu.

- Studio — korekta UX: wszystkie rozmiary paneli reguluj jednakowymi uchwytami na granicach, bez osobnych range sliderów menu/wysokości. Nie przywracaj kart „Sekcje i otwieranie” ani „Status techniczny podglądu” pod modelem.

- Aktualna korekta: bez przycisków Menu/Ustawienia/Podgląd 3D w nagłówku. Rozmiar, zwijanie i przywracanie realizują uchwyty granic; muszą zostać osiągalne po ukryciu panelu. W nagłówku pozostają motyw i zapis.

- Przejścia stanów paneli Studio mają być płynne, krótkie i spójne po obu stronach; zwykły resize bez opóźnień. Respektuj prefers-reduced-motion i nie kolejkuj przerwanych animacji.
