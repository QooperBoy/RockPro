import re,json
p='Integracja/rockpro_cad/addin/RockProPanel.cs'
s=open(p,encoding='utf-8-sig').read()
data=r'''MCP przekroczyło 180 s. Sprawdź IronCAD i historię operacji przed ponowną próbą.|MCP did not respond within 180 seconds. Check IronCAD and operation history before retrying.
MCP zamknęło połączenie bez odpowiedzi.|MCP closed the connection without a response.
Nazwa projektu|Project name
Klient|Client
Urządzenie|Device
Liczba skrzyń|Number of cases
Notatki|Notes
Plik ICS|ICS file
Status etapu|Stage status
Notatka etapu|Stage note
Wersja|Version
Pole|Field
Przy otwarciu|When opened
Twoje zmiany|Your changes
Aktualnie w bazie|Currently saved
RockPro CAD — Konflikt zapisu |RockPro CAD — Save conflict |
Nie zapisano: ktoś zmienił te dane od ich otwarcia (v|Not saved: these data changed since you opened them (v
).\nPorównaj wartości. Zamknięcie zachowa formularz i jego starą wersję. Wczytanie aktualnych danych odrzuci Twoje wpisy — możesz wcześniej skopiować komórki tabeli (Ctrl+C).|).\nCompare the values. Closing this window keeps your unsaved entries and original version. Reloading discards your entries. You can copy table cells first (Ctrl+C).
Zachowaj moje wpisy|Keep my unsaved entries
Wczytaj aktualne dane…|Reload saved data…
Odrzucić moje niezapisane wpisy i wczytać dane z kolumny Aktualnie w bazie?|Discard my unsaved entries and load the values in Currently saved?
Wczytanie aktualnej wersji|Reload current version
RockPro CAD — Historia zmian karty i etapów|RockPro CAD — Project and stage history
Data lokalna|Local time
Obszar|Area
Autor / kanał|Author / channel
Powód|Reason
RockPro CAD — Zmiana: przed i po|RockPro CAD — Before and after
Przed|Before
Po|After
Dwuklik w wiersz: wartości przed i po. Autor/kanał są deklaracją klienta, nie uwierzytelnioną tożsamością.\n|Double-click a row to compare before and after. Author/channel are reported by the calling app; they do not verify a person's identity.\n
Pokazano najnowsze 200 wpisów. Starsze wpisy dostępne przez get_history / before_id.|Showing the latest 200 entries. Older entries are available through the get_history API (before_id).
 wpisów. Starsze zdarzenia mogą nie zawierać pełnego porównania.| entries. Older events may not include a complete comparison.
Długość zewnętrzna konstrukcji • oś X|Outside plywood length • X axis
Głębokość zewnętrzna konstrukcji • oś Y|Outside plywood depth • Y axis
Wysokość dołu z dnem • oś Z|Base height including bottom • Z axis
Wysokość pokrywy z wiekiem • oś Z|Lid height including top • Z axis
Stała grubość wszystkich płyt|Constant thickness of every plywood panel
Odsunięcie prezentacyjne pokrywy • oś Z|Display-only lid separation • Z axis
Zapytanie|Inquiry
Urządzenia|Devices
Układ wyposażenia|Equipment layout
Konstrukcja|Structure
Okucia i profile|Hardware and profiles
Koła i piętrowanie|Wheels and stacking
Dokumentacja|Documentation
Materiały i koszty|Materials and costs
Produkcja|Production
Roboczy|Draft
Czeka na dane|Waiting for data
Do sprawdzenia|Needs review
Zatwierdzony ręcznie|Manually approved
Nieaktualny|Outdated
RockPro CAD | Stanowisko konstruktora|RockPro CAD | Designer workspace
Połącz / Odśwież|Connect / Refresh
Lokalna baza i MCP • niepołączono|Local database and MCP • not connected
+ Nowy projekt|+ New project
MVP 0.4\n\nCAD: szkielet 10 płyt\nSQLite: lokalna baza\nAI: operacje przez MCP\n\nBez generowania okuć i rysunków w tej wersji.|MVP\n\nCAD: 10-panel structure\nLocal project database\nAI access through MCP\n\nHardware and drawings are not generated yet.
Gotowe. Wybierz projekt lub utwórz nową kartę.|Ready. Select a project or create a new project card.
Trwa operacja. Poczekaj na wynik przed zamknięciem panelu.|An operation is running. Wait for the result before closing.
Masz niezapisane zmiany statusów. Odrzucić je i kontynuować?|You have unsaved stage changes. Discard them and continue?
Niezapisane etapy|Unsaved stages
Masz niezastosowane parametry. Odrzucić je i kontynuować?|You have unapplied parameters. Discard them and continue?
Niezastosowane parametry|Unapplied parameters
Masz niezapisane zmiany karty. Odrzucić je i kontynuować?|You have unsaved project changes. Discard them and continue?
Niezapisane zmiany|Unsaved changes
Dokonano: |Completed: 
Ostatnia operacja niepotwierdzona — sprawdź połączenie|Last operation not confirmed — check connection
Błąd: |Error: 
RockPro CAD — operacja nie została potwierdzona|RockPro CAD — operation not confirmed
Odczyt lokalnej bazy przez MCP|Loading the local database through MCP
MCP połączone • SQLite lokalna|MCP connected • local SQLite database
Baza: |Database: 
. Nie jest to import dawnej biblioteki RockPro.|. The historical RockPro library has not been imported.
Projekty w bazie: |Projects in database: 
Otwieranie karty projektu|Opening project card
Karta projektu|Project card
Nowy projekt • dane nie są zapisywane, dopóki nie klikniesz Zapisz kartę.|New project • enter the details, assign a saved ICS file and click Save project card.
 • karta v| • card v
 • lokalna baza SQLite| • local SQLite database
Nazwa projektu *|Project name *
Urządzenie / produkt|Device / product
Powiązany plik ICS • operacje CAD korzystają wyłącznie z tego pliku|Assigned ICS file • all CAD operations use this file
Zmiana aktywnej zakładki w IronCADzie nie zmienia powiązania projektu. Użyj jawnie przycisku przypisania i zapisz kartę.|Switching the active IronCAD tab does not change the assigned file. Use Assign active ICS file and save the card.
Przypisz aktywny plik ICS|Assign active ICS file
Podgląd UI nie ma sesji IronCAD.|This preview is not connected to IronCAD.
Brak aktywnego dokumentu.|No active document.
Zapisz scenę jako plik ICS przed przypisaniem.|Save the scene as an ICS file before assigning it.
Powiązanie pliku|Assign file
Notatki / wymagania|Notes / requirements
Zapisz kartę projektu|Save project card
Podaj nazwę i przypisz zapisany plik ICS.|Enter a project name and assign a saved ICS file.
Zapisywanie karty projektu|Saving project card
Konflikt: nic nie zapisano. Porównaj dane przed kolejnym zapisem.|Conflict: nothing was saved. Compare the data before saving again.
POŁĄCZONE: karta i plik projektu. BRAK BACKENDU: import maila, załączniki, automatyczne rozpoznawanie wymagań. Zapisz kartę przed zmianą widoku — niezapisane pola są tracone.|Available: project details and assigned file. Planned: email import, attachments and automatic requirements extraction. Save your changes before leaving this view.
Przygotowanie jednej skrzyni: liczba urządzeń, orientacja, przegrody i komora na akcesoria.|Plan the contents of ONE case: device count, orientation, dividers and an accessory compartment.
Otwórz konfigurator 3D|Open 3D layout editor
Najpierw zapisz kartę projektu z przypisanym szkieletem ICS.|First save the project card with an assigned ICS structure.
POŁĄCZONE: podgląd 3D, obliczenia przez MCP, zapis układu w SQLite i przekazanie gabarytów do kopii szkieletu ICS. Urządzenia, przegrody i akcesoria są obrysami w podglądzie; nie są jeszcze wstawiane do ICS. Wersja obsługuje jeden typ urządzenia i jedną komorę.|Available: 3D preview, layout calculation and saving, and resizing a copy of the ICS structure. Devices, dividers and accessories are preview shapes only; they are not inserted into ICS yet. Supports one device type and one accessory compartment.
Etapy projektu|Project stages
Statusy są deklaracją konstruktora. Każdy etap ma osobną wersję; ręczne zatwierdzenie nie oznacza kontroli CAD ani gotowości produkcyjnej.|Select a status and save it for each stage. Every stage has its own version. Manual approval does not validate CAD or release the design for production.
Najpierw zapisz lub wybierz projekt.|Save or select a project first.
Zapisz status|Save status
Zapisywanie statusu|Saving stage status
POŁĄCZONE: wersjonowane statusy i historia zmian. Wybrane zmiany danych oznaczają zależne etapy jako nieaktualne. BRAK BACKENDU: automatyczne bramki jakości i formalna akceptacja produkcyjna.|Available: stage versions and change history. Certain data changes mark dependent stages as outdated. Planned: automatic quality checks and formal production release.
Historia karty i etapów|Project and stage history
Pobieranie historii zmian|Loading change history
Parametry konstrukcji|Structure parameters
Zmiana wymiarów tworzy kopię ICS. Oryginał pozostaje niezmieniony; wynik przechodzi kontrolę geometrii i ponowne otwarcie.|Read values from CAD, edit dimensions in mm, then apply them to a copy. The copy is checked and reopened. The source file remains unchanged.
Źródło konstrukcji|Structure source file
Parametry nie zostały jeszcze odczytane z CAD.|Read parameters from CAD to enable editing.
Aktywna zakładka CAD jest inna niż przypisane źródło. Operacje użyją pliku projektu wskazanego powyżej.|The active CAD tab differs from the assigned source. Operations will use the project file shown above.
. Jednostka: mm. Grubość nie skaluje się razem z gabarytem.|. Unit: mm. Panel thickness does not scale with overall dimensions.
Odczytaj z CAD|Read from CAD
Wybierz projekt z przypisanym plikiem ICS.|Select a project with an assigned ICS file.
Odczyt parametrów przez MCP|Reading parameters through MCP
Parametr poza zakresem edycji: |Parameter outside the editable range: 
Odczytano 6 parametrów • wartości w milimetrach|6 parameters loaded • values in millimetres
Zastosuj na kopii|Apply to a copy
Wybierz zapisany projekt i odczytaj parametry.|Select a saved project and read its parameters first.
Tworzenie i kontrola kopii CAD|Creating and checking a CAD copy
Zmiana parametrów z panelu|Parameter changes from the panel
Utworzono i sprawdzono kopię:\n|Copy created and checked:\n
\n\nProjekt wskazuje teraz nową kopię roboczą. Odczytaj jej parametry przed kolejną zmianą.|\n\nThe project now points to the new working copy. Read its parameters before making another change.
Kopia zapisana|Copy saved
POŁĄCZONE: 6 parametrów szkieletu 10 płyt. BRAK BACKENDU: zmiany okuć, profili, pianek i dowolnych modeli WoodLAB.|Available: 6 parameters of the 10-panel structure. Planned: hardware, profiles, foam and support for other WoodLAB models.
Skopiowano do schowka.|Copied to clipboard.
Schowek|Clipboard
Kopiuj pełną ścieżkę|Copy full path
Kopiuj nazwę pliku|Copy file name
Kopiuj katalog|Copy folder path
Nie przypisano pliku|No file assigned
Kopiuj|Copy
Kopiuj pełną ścieżkę. Prawy przycisk: więcej opcji.|Copy the full path. Right-click for more copy options.
Historia snapshotów|CAD archive copies
Rewizje przypisane do projektu. Każdy snapshot zawiera plik ICS, parametry i raport kontroli.|Save an archive copy (snapshot) of the assigned CAD file. Enter a name and change description. Open the list to inspect previous copies and reports.
POŁĄCZONE: zapis i lista snapshotów. BRAK BACKENDU: automatyczny zapis po każdym etapie, porównanie geometrii oraz scalanie zmian ręcznych.|Available: saving and listing archive copies. Planned: automatic copies after each stage, geometry comparison and merging manual changes.
Nazwa snapshotu|Archive copy name
Opis zmian|Change description
Zapisz snapshot CAD|Save CAD archive copy
Wybierz projekt.|Select a project first.
Zapis snapshotu i kontrola CAD|Saving archive copy and checking CAD
Snapshot zapisany. Otwórz historię, aby zobaczyć szczegóły.|Archive copy saved. Open the history list to see its details.
Otwórz historię w oknie|Open archive list
Pobieranie historii snapshotów|Loading CAD archive history
Snapshot • przypisane źródło|Archive copy • assigned source
RockPro CAD — Historia |RockPro CAD — History |
Data|Date
Nazwa|Name
Walidacja CAD|CAD check
Integralność archiwum|Archive integrity
Wersja układu|Layout version
Parametry [mm]|Parameters [mm]
Niepowiązany|Not linked
Dwuklik: szczegóły • prawy przycisk: kopiuj ścieżkę\n|Double-click: details • right-click: copy path\n
RockPro CAD — Snapshot: |RockPro CAD — Archive copy: 
UKŁAD (wersja / SHA256 / specyfikacja):|LAYOUT (version / SHA256 / specification):
Niepowiązany — brak potwierdzonej wersji układu.|Not linked — no confirmed layout version.
PARAMETRY [mm]|PARAMETERS [mm]
    równanie: |    expression: 
Kopiuj ścieżkę ICS|Copy ICS path
Kopiuj szczegóły|Copy details
 snapshotów • Dwuklik w wiersz: pełne szczegóły i ścieżki\nID projektu: | archive copies • Double-click a row for details and paths\nProject ID: 
BRAK BACKENDU|PLANNED
Makieta zakresu. Poniższe pola nie zapisują danych i nie uruchamiają operacji.|Planned feature. The disabled fields below illustrate its scope; they do not save data or run operations.
Funkcje dostępne w głównych widokach. Zakres opisany w rejestrze integracji.|Use the main views for the available functions. This window explains the module's scope.
Dobór|Template
Koła|Wheels
Rysunki|Drawings
Magazyn|Inventory
Automatyczne|Automatic
Zaplanowane — backend niewdrożony|Planned — not available yet
Jawny rejestr możliwości MVP. Status „połączone” opisuje zakres funkcji, a nie bieżącą dostępność sesji CAD.|Check which features are available or planned. Click a module for details. Available describes implemented functionality, not the current CAD connection.
Karta projektu + SQLite|Project card + database
POŁĄCZONE|AVAILABLE
Zapis i odczyt metadanych; nowa lokalna baza, bez importu archiwum.|Save and load project details in a local database; historical library import is not available.
Parametry CAD przez MCP|CAD parameters through MCP
Odczyt 6 parametrów i walidowana zmiana na kopii szkieletu.|Read 6 parameters and apply checked changes to a copy of the structure.
Snapshoty ICS|ICS archive copies
Jawny zapis, historia, parametry i raport kontroli.|Save archive copies, view history, parameters and check reports.
CZĘŚCIOWO|PARTLY AVAILABLE
Ręczne statusy w bazie; brak automatycznych bramek.|Saved manual statuses; automatic quality checks are not available.
E-mail i załączniki|E-mail and attachments
Import zapytania, powiązanie korespondencji.|Import inquiries and link correspondence.
Urządzenia / research / Text-to-CAD|Devices / research / Text-to-CAD
Działają ręczne obrysy urządzeń; research i Text-to-CAD niewdrożone.|Manual device shapes are available. Research and Text-to-CAD are planned.
Dobór szablonu i układu|Template and layout selection
Działa układ 3D, przegrody, komora i gabaryty kopii ICS; bez wyszukiwania szablonów.|3D layout, dividers, compartment and ICS copy dimensions are available; template search is planned.
Okucia, profile, pianki|Hardware, profiles and foam
Katalog części i deterministyczne reguły mocowania.|Parts catalogue and defined placement rules.
Koła i gniazda|Wheels and stacking cups
Wspólny wzorzec, obciążenie i kontrola piętrowania.|Matching wheel/cup positions, load and stacking checks.
Rysunki i dokumentacja|Drawings and documentation
Paczkowanie dokumentacji konkretnej rewizji.|Prepare documentation for a specific design version.
Excel i BOM|Excel and materials list
Import, eksport, mapowanie kolumn i zestawienia.|Import, export, column mapping and materials lists.
Magazyn, zakupy i rozkrój|Inventory, purchasing and cutting
Rezerwacje, ceny, wspólny rozkrój zamówień.|Reservations, prices and combined cutting plans for orders.
Produkcja i informacja zwrotna|Production and feedback
Wydanie, zdjęcia, zgłoszenia i sprawdzone rozwiązania.|Production release, photos, reports and proven solutions.
Automatyczne harnessy i porównania|Automatic checks and comparisons
Migawki etapów, zależności, wykrywanie ręcznych zmian.|Stage snapshots, dependencies and detection of manual changes.
14 obszarów: 3 połączone · 3 częściowe · 8 bez backendu|14 areas: 3 available · 3 partly available · 8 planned
 Kliknij, aby zobaczyć zakres modułu.| Click to view module details.'''
# A literal can contain | in window titles; split on the last separator.
m={}
for line in data.splitlines():
 if '|' not in line:continue
 a,b=line.rsplit('|',1) if line.endswith('|') else line.split('|',1)
 # special title separator handled below
 m[a]=b
m['RockPro CAD | Stanowisko konstruktora']='RockPro CAD | Designer workspace'
m['RockPro CAD — Konflikt zapisu | ']='RockPro CAD — Save conflict | '
m['RockPro CAD — Historia | ']='RockPro CAD — History | '
# Explicit UI literals only; identifiers, data values and navigation keys are unchanged.
def q(x):return json.dumps(x,ensure_ascii=False)
def repl(match):
 literal=match.group(0); raw=literal[1:-1]
 if raw in m:return 'UiText.T('+literal+','+q(m[raw]).replace('\\\\','\\')+')'
 return literal
s=re.sub(r'"(?:\\.|[^"\\])*"',repl,s)
# Arrays need language-sensitive access instead of capturing language at construction.
for name in ['meanings','stageLabels','statusLabels']:
 s=re.sub(r'readonly string\[\] '+name+r'=\{(.*?)\};',r'string[] '+name+r' {get{return new[]{\1};}}',s)
open(p,'w',encoding='utf-8-sig').write(s)
