from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

OUT = Path(__file__).parent
d = Document()
s = d.sections[0]
s.page_width, s.page_height = Inches(8.5), Inches(11)
s.top_margin = s.bottom_margin = Inches(.7)
s.left_margin = s.right_margin = Inches(.75)
for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2']:
    st = d.styles[name]
    st.font.name = 'Calibri'
    st.font.color.rgb = RGBColor(0,0,0)
d.styles['Normal'].font.size = Pt(11)
d.styles['Normal'].paragraph_format.space_after = Pt(7)
d.styles['Normal'].paragraph_format.line_spacing = 1.08
d.styles['Title'].font.size = Pt(25)
d.styles['Heading 1'].font.size = Pt(17)
d.styles['Heading 2'].font.size = Pt(12)
header = s.header.paragraphs[0]
header.text = 'RockPro  |  Integracja IronCAD  |  Dokumentacja techniczna MVP'
header.runs[0].font.size = Pt(9)
footer = s.footer.paragraphs[0]
footer.text = 'Stan na 20 października 2026  •  Wersja 1.0                                      '
f = OxmlElement('w:fldSimple'); f.set(qn('w:instr'),'PAGE'); footer._p.append(f)
def p(t): d.add_paragraph(t)
def h(t): d.add_heading(t,2)
def page(t): d.add_page_break(); d.add_heading(t,1)
def table(headers, rows, widths):
    t=d.add_table(rows=1, cols=len(headers)); t.autofit=False
    pr=t._tbl.tblPr
    borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        el=OxmlElement('w:'+side); el.set(qn('w:val'),'single'); el.set(qn('w:sz'),'4'); el.set(qn('w:color'),'D9D9D9'); borders.append(el)
    pr.append(borders)
    for i,w in enumerate(widths): t.columns[i].width=Inches(w)
    for vals, row in [(headers,t.rows[0])]+[(r,t.add_row()) for r in rows]:
        for i,(cell,txt) in enumerate(zip(row.cells,vals)):
            cell.width=Inches(widths[i]); cell.text=str(txt)
            tcPr=cell._tc.get_or_add_tcPr()
            mar=OxmlElement('w:tcMar')
            for side in ['top','bottom','left','right']:
                el=OxmlElement('w:'+side); el.set(qn('w:w'),'85'); el.set(qn('w:type'),'dxa'); mar.append(el)
            tcPr.append(mar)
            for para in cell.paragraphs:
                para.paragraph_format.space_after=Pt(0)
                for r in para.runs: r.font.size=Pt(10)
        no=OxmlElement('w:cantSplit'); row._tr.get_or_add_trPr().append(no)
    for c in t.rows[0].cells:
        sh=OxmlElement('w:shd'); sh.set(qn('w:fill'),'DFEAF0'); c._tc.get_or_add_tcPr().append(sh)
        for r in c.paragraphs[0].runs: r.bold=True
    repeat=OxmlElement('w:tblHeader'); t.rows[0]._tr.get_or_add_trPr().append(repeat)
    d.add_paragraph().paragraph_format.space_after=Pt(0)

d.add_heading('Parametryczny szkielet skrzyni w IronCAD',0)
p('Dokumentacja wykonania MVP dla RockPro\nOdbiorcy: zespół projektowy RockPro i Jakub Siwiec')
h('Wynik prac')
p('Powstał natywny model ICS z dziesięcioma płytami, podzielonymi na górę i dół skrzyni. Sześć parametrów sceny steruje rozmiarami i położeniem płyt. Zmiana wspólnej długości lub głębokości przebudowuje obie części. Model przeszedł testy przez API, ponowne otwarcie oraz niezależną kontrolę geometrii przez agenta.')
p('Jest to działający szkielet konstrukcyjny dla jednego przykładu Epson. Nie jest jeszcze kompletną skrzynią produkcyjną ani uniwersalnym narzędziem rozpoznającym dowolne projekty. Nie przeniesiono okuć, kół, gniazd, otworów ani danych technologicznych WoodLAB.')
h('Cel i zmiana podejścia')
p('Celem było potwierdzenie, że istniejący projekt można wykorzystać jako źródło wymiarów i na tej podstawie automatycznie wygenerować prostą konstrukcję z trwałymi zależnościami w IronCAD. Wcześniejsza próba wiązania całej skrzyni ujawniła problemy z przebudową wycięć i profili. Dlatego ten etap ograniczono do kontrolowanego szkieletu z płyt.')
h('Plan realizacji')
for t in [
 '1. Zabezpieczyć otwartą scenę i pracować na kopii.',
 '2. Odczytać elementy grup góra/konstrukcja oraz dół/konstrukcja, ich obwiednie i wymiary.',
 '3. Przyjąć jednolity układ osi i jawne reguły budowy dziesięciu płyt.',
 '4. Utworzyć natywne części i podłączyć je do wspólnych parametrów sceny.',
 '5. Zmienić wymiary, sprawdzić rzeczywistą geometrię, zapisać i ponownie otworzyć plik.',
 '6. Przekazać wynik do niezależnej kontroli i zapisać raporty.']: p(t)
h('Najważniejsze założenia')
p('Płyty są prostokątne i mają jedną grubość. Góra i dół mają wspólny obrys. Wymiary wyjściowe pochodzą z geometrii projektu, a nie z nominalnej specyfikacji sklejki. Wykryte przesunięcie jednej płyty zostało jawnie znormalizowane. Ocena tego uproszczenia przed użyciem produkcyjnym pozostaje po stronie konstruktora.')

page('Dane źródłowe i rozpoznanie płyt')
p('Źródło: AI_CAD\\T_1_1\\Epson EB-PU2216B (2).ics. Stan otwartej sceny zapisano jako Epson_source_snapshot.ics i utworzono Epson_analysis_copy.ics. Oryginalnego pliku na dysku nie nadpisano. SaveAs zmienił nazwę otwartego dokumentu na kopię.')
h('Sposób rozpoznania')
p('Odczyt wykorzystał nazwy zespołów wskazane przez użytkownika oraz stare API COM. Dla elementów w konstrukcji pobrano InstanceShape.BoundingBox. Jest to rozpoznanie oparte na strukturze tego projektu i pomiarze obwiedni; nie jest to ogólny klasyfikator brył ani pełna analiza topologii powierzchni.')
table(['Część','Płyty','Liczba','Wymiary w mm'],[
['Góra','Przód i tył','2','914 × 94,33 × 9,8'],
['Góra','Lewa i prawa','2','582,4 × 94,33 × 9,8'],
['Góra','Płyta zamykająca','1','914 × 602 × 9,8'],
['Dół','Przód i tył','2','914 × 229,44 × 9,8'],
['Dół','Lewa i prawa','2','582,4 × 229,44 × 9,8'],
['Dół','Płyta zamykająca','1','914 × 602 × 9,8']], [0.7,1.85,.6,3.85])
p('Łącznie: 10 płyt. Grubość odczytana z modelu wynosi 9,8 mm. Wartości nie zastąpiono automatycznie nominalnymi 9 mm. Wymiary powyżej opisują prostokątne płyty szkieletu, nie gotowe formatki z obróbką.')
h('Różnica względem źródła')
p('Tylna płyta dołu była przesunięta w pionie o około −3,02 mm względem pozostałych ścian. Jej wysokość była zgodna. Generator wyrównał tę płytę do pozostałych ścian. To świadoma normalizacja geometrii, a nie wierne odwzorowanie tego szczegółu źródła.')
h('Parametry zapisane w scenie')
table(['Parametr','Wartość','Znaczenie'],[
['RP_Length','914 mm','Wspólna długość zewnętrzna'],
['RP_Depth','602 mm','Wspólna głębokość zewnętrzna'],
['RP_BaseHeight','239,24 mm','Wysokość konstrukcji dołu'],
['RP_LidHeight','104,13 mm','Wysokość konstrukcji góry'],
['RP_Thickness','9,8 mm','Grubość wszystkich płyt'],
['RP_DisplayGap','30 mm','Odstęp prezentacyjny między częściami']], [2.1,1.05,3.85])
p('RP_DisplayGap służy do prezentacji rozłożenia modelu. Nie jest luzem montażowym ani wymaganiem produkcyjnym.')

page('Architektura i reguły parametryczne')
h('Przepływ danych')
p('Otwarta scena IronCAD → kopia ICS → odczyt konstrukcji przez COM → legacy_panels.json → opis parametrów → generator Python → natywne części i wyrażenia IronCAD → plik ICS → pomiary i raporty testów.')
p('Warstwa Python automatyzuje tworzenie modelu i testowanie. Zależności są zapisane wewnątrz ICS jako parametry i wyrażenia IronCAD. Nie są wyłącznie wartościami w zewnętrznym Excelu. Na tym etapie nie powstał serwer MCP ani gotowy dodatek z własnym interfejsem.')
h('Środowisko integracji')
p('Prace wykonano z IronCAD 2027, Pythonem 3.14.3, pakietem python-ironcad 0.1.21 i comtypes 1.4.16. Adapter łączy się z lokalnym dokumentem przez COM i tablicę uruchomionych obiektów ROT. Korzysta z interfejsów wygenerowanych na podstawie bibliotek typów zainstalowanego IronCAD.')
p('Źródło pakietu producenta: https://github.com/IronCAD/python-ironcad. Dostępność operacji sprawdzano na rzeczywistym programie; sama obecność nazwy metody w bibliotece typów nie gwarantowała jej działania.')
h('Układ osi i jednostki')
p('Generator używa X jako długości, Y jako głębokości i Z jako wysokości. Odczyt źródłowy miał inny porządek osi. Raporty i parametry są prezentowane w milimetrach; natywne API operuje w metrach, a stary odczyt obwiedni zwracał milimetry. Pomiary testowe uwzględniają transformacje części do układu globalnego.')
h('Reguły budowy')
p('Oznaczenia: L — długość, D — głębokość, T — grubość, H — wysokość danego zespołu. Każda płyta ma jedną natywną cechę blokową Plyta.')
table(['Element','Rozmiar X × Y × Z'],[
['Ściana przednia i tylna','L × T × (H − T)'],
['Ściana lewa i prawa','T × (D − 2T) × (H − T)'],
['Płyta zamykająca','L × D × T']], [3,4])
p('W dole ściany zaczynają się na wysokości T, nad płytą denną. W górze ściany zaczynają się na lokalnym Z = 0, a płyta zamykająca znajduje się nad nimi. Cała góra ma globalne Z = RP_BaseHeight + RP_DisplayGap. Oba zespoły współdzielą długość, głębokość i grubość.')
p('Pozycje ścian wynikają z połówek wymiarów i odsunięcia o grubość. Dla przykładu środek przedniej ściany w XY to (L/2, T/2), a tylnej (L/2, D − T/2). Obsłużono fakt, że blok zmienia rozmiar w XY względem środka, a w Z względem dolnej powierzchni.')
p('Warunki poprawności: T > 0, L > 2T, D > 2T oraz H > T dla obu części. Obecne MVP nie zapewnia jeszcze ograniczania wszystkich nieprawidłowych wartości w interfejsie.')

page('Wykonanie i problemy integracyjne')
h('Jak zbudowano model')
p('Najpierw utworzono pełną część blokową przez DropObject z katalogu Starter. Posłużyła do zapisania Clean_panel_template.ics. Generator tworzy nową scenę i dwa zespoły, a następnie importuje szablon dziesięć razy przez AddChildFromExternalFile bez utrzymywania zewnętrznego powiązania.')
p('Rozmiary cechy powiązano przez LengthExpression, WidthExpression i HeightExpression. Położenia części ustawiono przez PositionTransformComponentExpression. Odwołania prowadzą do parametrów sceny przez Parent i Params, zgodnie z poziomem obiektu w hierarchii.')
p('Kluczowa poprawka: wszystkie części muszą najpierw zostać zaimportowane. Następnie generator ponownie przypina wyrażenia i wywołuje ForceSetupParameterExpression dla cechy i części. Dopiero potem wykonuje RegenerateParts, Update i SaveAs. Ten wariant został ponownie zbudowany od zera i przetestowany.')
h('Co nie działało od razu')
p('Początkowo interfejs COM zwracał błędy rejestracji biblioteki i E_NOINTERFACE. Rejestracja bibliotek typów dla użytkownika oraz restart programu na zabezpieczonej kopii przywróciły dostęp. Jeden z eksperymentów z kolejnością rejestracji zakończył się błędem RPC i awarią procesu. Dokładna przyczyna tego błędu nie została dowiedziona.')
p('CreateBlock i CreateBlockPart były oznaczone jako niezaimplementowane. InsertElement z katalogu nie dawał pełnej części, a kopiowanie cechy między dokumentami kończyło się E_FAIL. Dlatego wybrano pełny szablon części i import natywny.')
p('Przy wiązaniu parametrów od razu po każdym imporcie wymiary zmieniały się tylko w ostatniej płycie każdego zespołu. Sam model bazowy wyglądał poprawnie, lecz test zmiany wymiarów wykazał błąd. Ponowne przypięcie zależności po zakończeniu importów rozwiązało obserwowany problem.')
h('Najważniejsze pliki kodu')
table(['Plik w katalogu Integracja','Rola'],[
['ironcad_adapter.py','Połączenie z dokumentem przez COM'],
['capture_legacy_panels.py','Odczyt obwiedni płyt ze źródła'],
['write_skeleton_report.py','Raport rozpoznania i dane parametrów'],
['build_clean_skeleton.py','Budowa natywnego szkieletu ICS'],
['test_clean_skeleton.py','Zmiany parametrów i pomiary'],
['reopen_skeleton_test.py','Zapis i sprawdzenie po otwarciu'],
['review_skeleton_geometry.py\nreview_skeleton_global.py','Niezależne reguły kontroli geometrii']], [3.3,3.7])
p('Rozpoznanie pozostaje dostosowane do tego pliku. Nie wszystkie wcześniejsze skrypty próbne są działającymi punktami wejścia; podstawą odczytu jest capture_legacy_panels.py.')

page('Weryfikacja i osiągnięte efekty')
p('Testy mierzyły rzeczywiste obwiednie części po przebudowie, a nie tylko wartości wpisane do parametrów. Sprawdzano wymiary, grubość, role płyt, styki, brak dodatniej objętości nakładania oraz wspólny obrys i położenie zespołów.')
table(['Próba','Zmiana w mm','Wynik'],[
['Bazowa','914 × 602; dół 239,24; góra 104,13; T 9,8','PASS'],
['Długość','L = 1014','PASS'],
['Głębokość','D = 662','PASS'],
['Wysokość dołu','H dołu = 289,24','PASS'],
['Wysokość góry','H góry = 144,13','PASS'],
['Grubość','T = 12','PASS'],
['Wariant łączony','L 1040; D 700; dół 300; góra 150; T 12','PASS'],
['Mniejsza skrzynia','L 800; D 500; dół 200; góra 80; T 9,8','PASS'],
['Powrót','Przywrócenie parametrów bazowych','PASS'],
['Ponowne otwarcie','Odczyt modelu i późniejsza zmiana L na 1014','PASS']], [1.45,4.7,.85])
h('Niezależna kontrola')
p('Agent weryfikujący odczytał gotowy model bez jego modyfikowania. Potwierdził sześć widocznych parametrów sceny, dwa zespoły po pięć płyt, jedną cechę blokową na płytę oraz przypisane wyrażenia. Kontrola obejmowała 73 sprawdzenia geometrii i 15 sprawdzeń położenia globalnego dla badanego stanu, z tolerancją geometryczną 0,002 mm.')
p('Raporty niezależne obejmują również zapisane stany wariantów i ponownego otwarcia. Po testach przywrócono parametry bazowe i zapisano plik końcowy.')
h('Granice potwierdzonego wyniku')
p('Potwierdzono przebudowę przez API i trwałość wyrażeń po ponownym otwarciu. Nie wykonano jeszcze pełnego testu akceptacyjnego ręcznej edycji parametrów w oknie IronCAD; raport jawnie zawiera ui_edit_verified = false. Wyniki dyskretnych wariantów nie dowodzą poprawności dla dowolnych wartości.')
p('Nie sprawdzono wytrzymałości, technologii połączeń, pasowania okuć, kół i gniazd ani zgodności produkcyjnej z WoodLAB. Nie wygenerowano dokumentacji CNC ani finalnego kosztorysu. Nie zmierzono jeszcze skrócenia czasu pracy konstruktora względem procesu RockPro.')
h('Znaczenie dla dalszego projektu')
p('MVP potwierdza techniczną możliwość lokalnego generowania i przebudowy kontrolowanej rodziny konstrukcji w natywnym IronCAD. Daje podstawę do dołączenia okuć jako elementów o stałym rozmiarze i położeniu wyliczanym z obrysu. Nie potwierdza jeszcze automatycznego rozumienia całej skrzyni przez AI.')

page('Odtworzenie wyniku i dalsze prace')
h('Gdzie znajdują się pliki')
p('Katalog integracji:\nC:\\Ai\\Podnośniki\\Materialy_dla_firm\\RockPro\\Integracja')
p('Katalog wyniku względem integracji:\nskeleton\\20261020T110925Z')
table(['Plik w katalogu wyniku','Zawartość'],[
['RockPro_Epson_szkielet_MVP.ics','Końcowy model do otwarcia w IronCAD'],
['Rozpoznanie_plyt.html','Czytelny wykaz płyt i wymiarów'],
['legacy_panels.json','Pomiary źródłowe'],
['skeleton_parameters.json\nskeleton_manifest.json','Założenia, parametry i utworzone obiekty'],
['skeleton_tests.json','Wyniki zmian parametrów'],
['independent_geometry_review.json\nindependent_global_review.json','Niezależna kontrola zapisanych pomiarów'],
['independent_live_review.json','Odczyt i audyt gotowego modelu'],
['START_HERE.txt','Skrócona instrukcja pracy z wynikiem']], [3.65,3.35])
h('Warunki ponownego uruchomienia')
p('Gotowy ICS można otworzyć bez uruchamiania generatora. Ponowne generowanie wymaga lokalnego IronCAD, dostępu COM w sesji użytkownika i środowiska Python integracji. Obecny skrypt jest prototypem zależnym od lokalnych ścieżek oraz skeleton_state.json, a nie przenośnym instalatorem.')
p('build_clean_skeleton.py oczekuje otwartego Skeleton_probe_drop.ics i części wzorcowej. Odczytuje skeleton_parameters.json oraz używa Clean_panel_template.ics. Odmawia nadpisania istniejącego pliku wynikowego. Przed kolejnym uruchomieniem należy wskazać nowy katalog wyniku i dostosować stan wejściowy; nie usuwać działającego MVP tylko po to, aby ponowić test.')
h('Kolejność następnego etapu')
p('1. Dokończyć test ręcznej zmiany sześciu parametrów w IronCAD i uzgodnić z konstruktorem grubość 9,8 mm oraz wyrównanie tylnej płyty. Kryterium: taka sama geometria jak po zmianie przez API.')
p('2. Uporządkować generator: jawne argumenty wejściowe, brak zależności od sceny próbnej, kontrola zakresów, kopia bezpieczeństwa, dziennik błędów i bezpieczny powrót po nieudanej przebudowie.')
p('3. Dodać jedną rodzinę okuć i parę koło–gniazdo. Rozmiar katalogowy pozostaje stały, a położenie wynika z obrysu i wspólnych punktów odniesienia. Dopiero potem dodać powiązane otwory i obróbkę.')
p('4. Wystawić sprawdzone operacje jako narzędzia MCP: odczyt sceny, rozpoznanie konstrukcji, podgląd zmian, zastosowanie parametrów i walidacja. AI proponuje wariant; deterministyczny kod wykonuje geometrię, a konstruktor zatwierdza zmianę.')
p('5. Sprawdzić drugi rzeczywisty projekt, zachowanie danych WoodLAB i eksport dokumentacji. Dopiero te wyniki pozwolą ocenić zakres automatyzacji produkcyjnej oraz oszczędność czasu.')
d.core_properties.title='Parametryczny szkielet skrzyni w IronCAD'
d.core_properties.subject='Dokumentacja techniczna MVP RockPro'
d.core_properties.author='RockPro — dokumentacja prac integracyjnych'
d.save(OUT/'RockPro_IronCAD_Dokumentacja_techniczna_MVP.docx')
print(OUT/'RockPro_IronCAD_Dokumentacja_techniczna_MVP.docx')
