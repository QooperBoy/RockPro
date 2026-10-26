# RockPro — rynek i kierunki rozwoju

Stan researchu: **26.10.2026**. Dokument jest propozycją produktu i integracji,
nie dowodem wdrożenia wymienionych rozwiązań. Sprawdzono publiczne strony
producentów i dokumentację. Nie zakładano kont, nie kupowano licencji, nie
instalowano programów i nie przesyłano modeli klienta do usług internetowych.
Brak publicznej informacji o API oznacza **niepotwierdzone**, a nie „API nie ma”.

Największa szansa RockPro to połączenie firmowych zasad konstrukcji z gotowym
modelem, obróbkami i dokumentacją tej samej rewizji. Konfiguratory, CAM i ERP już
istnieją. Własną wartością powinny być reguły Rokro, zachowane powiązania i
czytelne wyjaśnienie, skąd wzięła się każda decyzja.

## Punkt wyjścia w naszym repozytorium

Już mamy wspólny rejestr rodzin i etapów, lokalny podgląd rzeczywistych siatek,
dziennik procesu, import zapotrzebowania BOM oraz kontrolowany pakiet wydania.
Nie proponujemy ich budować drugi raz. Aktualne granice opisują
[rejestr](PART_FAMILY_REGISTRY_TASK.md),
[obserwator](RELIABILITY_AND_OBSERVER.md),
[import BOM](CUTTING_BOM_IMPORT.md),
[wydanie](REVISION_RELEASE_BUNDLE.md) oraz
[standard źródłowy nowych rodzin](WORKING_MOUNT_STANDARD.md).

Pozostają połączenia między tymi modułami, produkcyjne znaczenie części i
potwierdzone dane. Inwentarz wystąpień nie jest zakupowym BOM; pudełko obrysowe
nie jest konturem wycięcia. Siedem nowych rodzin ma robocze ramy źródłowe,
ale nie pełną parametryzację W/D/H. ROC-45 zbiera pytania do konstruktora.

## Co rzeczywiście jest dostępne

W tabelach **fakt** opisuje źródło producenta. **Wniosek dla RockPro** jest naszą
propozycją, której nie należy przypisywać producentowi. S/M/L to względna
złożoność pierwszego użytecznego przyrostu, nie obietnica terminu.

### Projektowanie, okucia i produkcja

| Rozwiązanie | Zweryfikowany fakt i źródło | Wniosek dla RockPro / ograniczenie | Kierunek |
| --- | --- | --- | --- |
| Penn Elcom Case Designer | Aktualny produkt ma bibliotekę okuć, wycenę/masę, BOM, listy cięcia i eksport DXF/STEP. [Produkt](https://www.penn-elcom.com/tools/penn-elcom-case-designer), [subskrypcja](https://www.penn-elcom.com/case-designer-subscription-annual). | Dobry punkt odniesienia: porównać kilka anonimowych typów skrzyni, liczbę ręcznych operacji i kompletność eksportów. Nie zastępować nim bez próby istniejących rodzin IronCAD. | **Porównać**, P1/M |
| Własne części w Case Designer | FAQ dopuszcza import STEP własnych nieskalowalnych okuć; niestandardowe profile/panele wymagają Penn Elcom. Wnętrza są ograniczone; producent sugeruje ich dalszą obróbkę w CAD. Stare pliki nie są importowane do nowego formatu. [FAQ PL](https://www.penn-elcom.com/pl/case-designer-faq), [FAQ EN](https://www.penn-elcom.com/sg/case-designer-faqs). | To istotna luka dla RockPro: firmowe moduły wnętrz, wieloelementowe czapki, rack i transport bagażowy. Otwarte formaty i wersjonowane reguły zmniejszą zależność od jednego formatu. Publiczne API Case Designer nie zostało potwierdzone. | **Budować reguły własne**, P0/L |
| Penn Elcom — dane elementu | Karta H7159 zawiera m.in. głębokość miski, otwory montażowe i powiązane podkładki/uszczelkę. [H7159](https://www.penn-elcom.com/heavy-duty-medium-recessed-handle-with-rivet-protection-h7159-series). | Biblioteka powinna rozdzielać SKU, zestaw zakupowy, geometrię, wycięcie i akcesoria. Karta produktu nie ustala automatycznie właściwego konturu sklejki. Nie wyprowadzać go z wymiaru zewnętrznego miski. | **Import kontrolowany**, P0/M |
| Adam Hall — biblioteka techniczna | Portal ma dane produktu i pliki CAD/rysunków; dla sprawdzonego 3429 udostępnia rysunek 2D PDF. Karta 4155 podaje materiał, grubość, otwory i gabaryty. [3429](https://portal.adamhall.com/de/downloadcenter/article/3429), [4155](https://www.adamhall.com/shop/en/corners-l-corners/4155). | Zapisywać źródło, numer rysunku, datę i hash przy części. Nie zakładać, że każdy produkt ma STEP albo że pliki wolno redystrybuować w publicznej bibliotece. | **Import kontrolowany**, P0/M |
| Adam Hall — dodatkowe rodziny | Oferta obejmuje profile, zamki, uchwyty, systemy przegród, prowadnice, wsporniki teleskopowe, koła, racki amortyzowane i system Easy Case. [Zakres katalogu](https://www.adamhall.com/shop/en/flight-case-material). | Uchwyt bagażowy i koła wpuszczane to rozszerzenia rejestru, nie wyjątki w generatorze. Później szuflady, wysuwane blaty i moduły rack; każdy wymaga osobnej reguły montażu i strefy ruchu. | **Rozszerzać rodzinami**, P1/L |
| FliteCAD | Oficjalny katalog Adam Hall opisuje projektowanie 2D/3D, wymiary wewnętrzne/zewnętrzne, sprzęt i wyceny. [Katalog producenta](https://webcontent.adamhall.com/media/online_catalogue/catalogs/Adam_Hall_Hardware_Product_News/pdf/complete.pdf). `flitecad.com` podczas odczytu przekierował do niedostępnej przez narzędzie kategorii sklepu. | Zachować jako trop konkurencyjny, ale bieżąca dostępność instalatora, wsparcia, API i zgodności nie została potwierdzona. Nie wybierać na tej podstawie jako zależności projektu. | **Sprawdzić później**, P2/S |
| Blickle — koła | Producent udostępnia modele ACIS/IGES/Parasolid/STEP po zalogowaniu. [CAD](https://www.blickle.co.uk/services/cad-downloads). Przewodnik doboru rozróżnia obciążenia i warunki eksploatacji. [Nośność](https://www.blickle.com/guide/load-capacity). | Para koło–gniazdo potrzebuje także wysokości, obwiedni skrętu/hamulca i granic podpory. Kalkulator doboru może sprawdzać brak danych o masie i zastosowaniu; zgodność geometryczna nie zatwierdza nośności całej skrzyni. | **Dodać dane i walidację**, P1/M |
| Para-Flex | Producent opisuje integrację z IronCAD: listy cięcia/zakupów, optymalizację płyt, raporty, DXF i CNC w odpowiednich pakietach. [Produkt](https://para-flex.com/). Uruchomienie wymaga modelu wcześniej zapisanego. [Instrukcja](https://para-flex.com/basics/overview/). | Pierwszy kandydat na produkcyjne rozszerzenie, gdy poznamy park maszyn. Sprawdzić obsługę konkretnych wersji 2023/2027, sterownika i eksportu, nie tylko nazwę producenta maszyny. Obecny zakaz zapisywania CAD wyklucza samodzielny test tego przepływu teraz. | **Ocenić zakup/integrację**, P1/M–L |
| woodLAB | Producent oferuje CAD/CAM dla obróbki drewna, optymalizację płyt/nesting oraz etykiety w module PLAN. [woodLAB](https://www.woodlab.eu/en/default.asp). | Alternatywa dla Para-Flex, zwłaszcza gdy firma chce pełne przygotowanie technologiczne. Próba na naszych wycięciach i profilach ma większą wartość niż ogólna prezentacja mebli. Wersje hosta/postprocesor do potwierdzenia. | **Porównać z Para-Flex**, P1/M–L |
| Vectric VCarve Pro | Pro obsługuje nesting, szablony ścieżek i typowe operacje 2D/2.5D. [Produkt](https://www.vectric.com/products/vcarve/). Dokumentacja pokazuje import zestawu CSV + DXF, warstwy operacji i etykiety. [Instrukcja](https://docs.vectric.com/docs/V12.5/VCarvePro/ENU/Help/page/single-page/). STEP nie jest obsługiwany jako wejście. [Formaty 3D](https://vectric.zendesk.com/hc/en-us/articles/31400661924125-What-3D-File-Formats-does-Vectric-Support). | Dobry cel wymiany plikowej: prawdziwe kontury DXF + materiał + ilość + warstwy obróbek. Ustalić maszynę, frezy, mocowanie i postprocesor przed generowaniem kodu. Sam DXF nie jest gotowym programem CNC. | **Adapter eksportu**, P1/M |
| HOMAG intelliDivide | Nesting przyjmuje m.in. programy woodWOP/MPR, uwzględnia materiały, włókno, resztki i etykiety. Producent rozróżnia usługę chmurową i lokalne Cut Rite. [Opis i porównanie](https://www.homag.com/en/product-detail/software/work-preparation/intellidivide-nesting). | Rozważyć tylko jeśli firma używa zgodnego procesu HOMAG. Zamiast własnego solvera można dostarczyć poprawne wejście. Nie wysyłać projektów do chmury tylko dlatego, że istnieje demo. | **Warunkowo integrować**, P2/L |
| Deepnest | Otwarta aplikacja nestingowa dla Windows/Mac/Linux; kod producenta dostępny publicznie. [Strona](https://deepnest.io/), [repo](https://github.com/Jack000/Deepnest). | Tani eksperyment porównania rozkroju na danych syntetycznych. Nie traktować samego ułożenia konturów jako sprawdzenia mocowania, kierunku dekoru, technologii piły ani kolejności frezowania. Przed osadzeniem trzeba ocenić utrzymanie, zależności i licencję konkretnej wersji. | **Eksperyment**, P2/M |

Dokumentacja Case Designer zawiera również ograniczenia użycia i
udostępniania modeli. W tej rundzie nie uzyskiwano osobnej zgody na ich
dystrybucję; nie należy traktować subskrypcji jako licencji na publiczną
bibliotekę RockPro. [Instrukcja producenta, Feedback & Legal](https://casedesigner.blob.core.windows.net/release-binaries/manual/Case%20Designer%20Manual.pdf).

### Pianki, magazyn, kontrola rewizji i prezentacja

| Rozwiązanie | Zweryfikowany fakt i źródło | Wniosek dla RockPro / ograniczenie | Kierunek |
| --- | --- | --- | --- |
| MyCaseBuilder | Edytor ma bibliotekę kształtów, obrys ze zdjęcia, wgłębienia na palce i układ warstw; FAQ opisuje import rysunków jako usługę. [Funkcje](https://mycasebuilder.com/how-the-app-works/), [FAQ](https://mycasebuilder.com/faqs/). | Świetny wzorzec UX dla modułu pianek: kontur + głębokość + chwyt + minimalna ścianka. Obrys ze zdjęcia tylko jako propozycja po kalibracji skali i potwierdzeniu wymiarów, nie źródło dokładnego pasowania. Nie potwierdzono publicznego API. | **Budować wąski moduł**, P1/L |
| Zotefoams / Plastazote | Producent rozróżnia gatunki i właściwości pianek oraz udostępnia karty właściwości. [Plastazote](https://zotefoams.com/our-brands/azote/plastazote/). | Biblioteka pianki musi przechowywać gatunek i zachowanie materiału, nie sam kolor/grubość. Docisk i podparcie wymagają danych urządzenia oraz materiału. Nie dobierać bez nich twardości „na oko”. | **Biblioteka materiałów**, P1/M |
| Pelican — gotowe korpusy | Portal producenta udostępnia dla wielu obudów STEP, Parasolid, DXF i PDF. [Pliki techniczne](https://business.pelican.com/us/en/resources/downloads). | Możliwa osobna rodzina „gotowa obudowa + wkład”. Korpus sztywny, parametryzowany tylko wkład i dozwolone mocowania. Nie deformować katalogowej obudowy do zadanego rozmiaru. | **Nowa rodzina**, P2/M |
| InvenTree | System posiada magazyn, BOM i zlecenia budowy; API REST ma kontrolę dostępu. [API](https://docs.inventree.org/en/latest/api/), [schemat](https://github.com/inventree/InvenTree/blob/master/docs/docs/api/schema.md). Kody można wiązać z częściami i zapasem. [Kody](https://docs.inventree.org/en/latest/barcodes/). | Kandydat na magazyn okuć/arkuszy i etykiety. Najpierw adapter odczytu i eksport zatwierdzonej listy; nie tworzyć drugiego stanu magazynowego w C#. Stan, rezerwacja i faktyczne zużycie muszą być rozdzielone. | **Ocenić integrację**, P1/M |
| ERPNext | Obsługuje wielopoziomowy BOM, operacje, stanowiska i zlecenia; zatwierdzony BOM podlega kontrolowanej zmianie. [BOM](https://docs.frappe.io/erpnext/bill-of-materials). Rekordy są dostępne przez REST API. [Integracje](https://docs.frappe.io/erpnext/integrating-erpnext-with-other-applications). | Kandydat, gdy celem jest również planowanie produkcji, zakupy i koszt rzeczywisty. RockPro eksportuje inżynierską rewizję i mapowanie pozycji, ERP prowadzi transakcje. Wdrożenie ERP to osobny projekt operacyjny. | **Wybrać zamiast pisać ERP**, P2/L |
| Odoo | BOM łączy komponenty, warianty i operacje. [Dokumentacja](https://www.odoo.com/documentation/saas-19.3/applications/inventory_and_mrp/manufacturing/basic_setup/bill_configuration.html). Dokumentacja Odoo 19 opisuje JSON-2 API i wymóg planu Custom dla dostępu zewnętrznego w opisanej ofercie. [API](https://www.odoo.com/documentation/19.0/th/developer/reference/external_api.html). | Alternatywa dla ERPNext, szczególnie jeśli firma już korzysta z Odoo. Przed projektowaniem integracji ustalić edycję, hosting, plan i uprawnienia. Nie zakładać dostępnego API dla każdego konta. | **Warunkowo integrować**, P2/L |
| Rentman | Producent opisuje zestawy sprzętu/cases, listy pakowania, kody QR, numery seryjne i naprawy. [Magazyn AV](https://rentman.io/solutions/inventory-management). API ma aktualizowany changelog. [API](https://support.rentman.io/hc/en-us/articles/26707946497042-Rentman-API-Changelog). | To inny magazyn niż sklejka i nity: wyposażenie klienta/wypożyczalni. Można przekazać finalny obrys, masę, listę zawartości i ID skrzyni. Sens dopiero po potwierdzeniu, że odbiorcy faktycznie używają systemu. | **Opcjonalny adapter**, P2/M |
| IronCAD SmartMotion / Mechanism Mode | Dokumentacja **2023** opisuje ruch przez więzy, kontrolę przenikania i odtwarzanie SmartMotion. Wskazuje ograniczenia więzów pomiędzy poziomami hierarchii. [Mechanism Mode 2023](https://www.ironcad.com/support/2023/IRONCAD_Help/Content/3D_Design_Environment/Positioning_Objects/Using_the_Mechanism_Mode.htm). | Nie trzeba pisać własnego solvera zawiasów. Najpierw natywny eksperyment na kopii z prawdziwą osią i zwolnionymi zamkami. Sama obecność funkcji UI nie potwierdza kompletnego kreatora animacji w SDK. Kontynuować istniejący ROC-44. | **Użyć natywnego narzędzia**, P1/M |
| Konfiguracje rozstrzelone IronCAD | Oficjalny blog opisuje osobną konfigurację rozstrzeloną; swobodne przemieszczanie jest oddzielone od domyślnej konfiguracji, z rozluźnieniem relacji. [Configurations](https://community.ironcad.com/index.php?%2Fblogs%2Fentry%2F57-configurations%2F=). | Dobre źródło instrukcji składania, ale nie mieszać go z modelem parametrycznym. Potrzebne mapowanie etapu → część → wycięcie → rysunek i kontrola powrotu. | **Rozszerzyć prezentację**, P1/M |
| Design Data Manager | IronCAD wskazuje DDM jako partnera do cyklu życia i rewizji scen, rysunków oraz dokumentów. [Partnerzy IronCAD](https://www.ironcad.com/solution-partners/). | Opcja dla wielu konstruktorów. Obecny Git/SQLite/pakiet wydania zostawić do czasu konkretnej potrzeby PDM; nie dublować jednocześnie trzech systemów rewizji. Zgodność wersji i licencje wymagają próby/oferty. | **Ocenić przy skalowaniu zespołu**, P2/L |
| model-viewer / GLB i AR | Oficjalny komponent wyświetla glTF/GLB; obsługuje AR na zgodnych urządzeniach i stałą skalę. [Dokumentacja](https://modelviewer.dev/docs/index.html), [Google](https://developers.google.com/ar/develop/webxr/model-viewer). | Opcjonalny podgląd dla klienta i kontrola gabarytu w pomieszczeniu. Aktualny lokalny viewer Three.js już istnieje — nie wymieniać go tylko dla nowej biblioteki. AR nie jest pomiarem produkcyjnym; eksport wymaga zgodności jednostek i rewizji. | **Eksperyment sprzedażowy**, P2/M |
| Speckle | Dostępne są przeglądarka 3D, issues, markups i prezentacje; aktualne plany różnią historię wersji i automatyzację. [Oferta](https://speckle.systems/pricing/), [aktualizacje](https://speckle.systems/updates/). | Inspiracja do przeglądu zmian z klientem. Nie potwierdzono gotowego konektora IronCAD. Nie opierać integracji na starym opisie „one-click diff”: zmieniają się funkcje/UX. W pierwszym kroku lokalne porównanie jawnych ID i parametrów jest prostsze. | **Obserwować, nie wdrażać teraz**, P2/L |

## Budować, integrować czy odłożyć

| Decyzja | Zakres | Powód / kryterium wejścia |
| --- | --- | --- |
| **Budować w RockPro** | Rodziny konstrukcji, sztywne okucia, kotwy, obróbki, reguły gabarytu i luzów, wyjaśnienie decyzji | To wiedza firmy i istniejące kontrakty. Każdy wariant ma mieć przypięty wzorzec, zakres parametrów i dowód powrotu geometrii. |
| **Rozszerzać istniejące moduły** | Rejestr, observer, wydanie, BOM, porównanie rewizji | Nie robić drugiego generatora ani drugiej bazy projektu. Podgląd, trace i model muszą wskazywać tę samą rewizję. |
| **Kupić / zintegrować po próbie** | Nesting produkcyjny, CAM, postprocesory, ERP/PDM | Gotowe narzędzia obsługują procesy trudniejsze niż samo ułożenie konturów. Najpierw odpowiedzi Q07 i próbny plik na rzeczywistej technologii. |
| **Pozyskać dane, nie zgadywać** | SKU, ceny, zapasy, masy, gatunki pianki, katalogowe obróbki | Dla każdego pola źródło i aktualność. Brak ceny nie jest zerem, brak informacji o wycięciu nie jest „nie wymaga”. |
| **Odłożyć** | Własny CAM, nowy ERP, pełny PDM, automatyczne zamówienia, własny solver mechanizmów | Duży koszt utrzymania, brak potrzeby i danych. Użytkownik powinien najpierw zobaczyć niezawodny przepływ jednej rodziny. |
| **Nie robić w tej formie** | „Dowolny ICS → gotowy produkt”, skalowanie gotowych okuć, dopasowanie pianki z samego zdjęcia, ocena nośności przez LLM | Wynik wygląda przekonująco, ale gubi funkcję części, technologię i dowód poprawności. |

## Trzy horyzonty

### Teraz: przyrosty możliwe bez nowych decyzji konstruktora

1. **Karta kompletności rodziny.** Wspólna lista: części rozpoznane,
   własność obróbek, materiały, ramy, ograniczenia, dowody natywne, produkcja.
   Każde pole ma źródło albo „nieustalone”; odsyła do właściwego pytania ROC-45.
   Nie przeliczać tego na procent „gotowości produkcyjnej”.
2. **Katalog kandydatów z pochodzeniem.** Zgrupować jednakowe definicje
   źródłowe, ale nie scalać samym FileGUID, nazwą ani wyglądem. Osobno liczba
   wystąpień, liczba fizycznych części i potencjalny zestaw zakupowy.
3. **Kontrakt konturu i pakietu obróbek.** Uchwyt + jego referencja do wycięcia,
   płyta docelowa, strona, głębokość, wersja i reguła luzu. Brakujący kontur
   blokuje eksport obróbki; nie zastępować go AABB.
4. **Dowody procesu i porównanie rewizji.** Kontynuować observer: czas całkowity
   bez podwójnego sumowania, czas SDK, oczekiwanie, powód interwencji agenta,
   liczba ponowień. Porównanie części przez stabilne ID zamiast obrazków.
5. **Karta wydania i lista braków.** Rozbudować istniejący pakiet o jawne role
   przyszłych plików produkcyjnych i wymagany host. Sam hash nie potwierdza
   zatwierdzenia przez konstruktora ani zgodności 2023/2027.

Powyższa lista jest propozycją przyrostów. Ich faktyczny zakres implementacji
i testów należy czytać w raporcie nocnej pracy, nie wywnioskowywać z researchu.

### Po odpowiedziach ROC-45: pierwsza droga do produkcji

1. Zamknąć jedną rodzinę od zmiany gabarytu do modelu i powrotu, bez uszkadzania
   sprzętu, pianki ani katalogowych okuć. Dopiero potem kolejne rodziny.
2. Dodać kalkulator komory, sklejki, profili i obrysu transportowego. Użytkownik
   wybiera wymiar nadrzędny; reguły jawnie pokazują konsekwencje.
3. Wyprowadzić prawdziwe formatki i powiązane obróbki, a następnie sprawdzić
   minimalny eksport DXF/CSV z operatorem maszyny. Rozróżnić cięcie,
   kieszeń, wiercenie i nacięcie profilu.
4. Porównać Para-Flex i wybraną alternatywę CAM na tym samym anonimowym
   zestawie. Kryteria: liczba ręcznych kroków, zachowanie jednostek/lustrzanych
   płyt, koszt materiału, korekta po zmianie modelu, obsługa posiadanego sterownika.
5. Dopiąć zakupowy BOM i kontrolę dostępności; potem rezerwację i rozliczenie
   zużycia. Obecny magazyn firmy pozostaje źródłem transakcji, jeśli istnieje.

### Eksperymenty: szerzej, ale z mierzalnym wynikiem

| Pomysł | Co pokazujemy | Co musi być znane / dowód |
| --- | --- | --- |
| **„Dlaczego nie mieści się?”** | Widok konfliktu zawias–uchwyt, brakujący luz, legalne alternatywy | Poprawne strefy montażowe i ruchu; propozycja nie przesuwa samoczynnie zatwierdzonego elementu. |
| **Wariant ekonomiczny** | Dwa projekty: mniej płyt/odpadu vs mniejszy obrys transportowy | Rzeczywiste formaty arkuszy, technologia, cennik z datą. Nie optymalizować samą objętością. |
| **Paszport QR skrzyni** | Rewizja, części serwisowe, instrukcja, zdjęcia odbioru, historia napraw | QR odnosi się do trwałego ID produktu/rewizji; nie zawiera danych klienta ani tokena dostępu. |
| **Instrukcja „krok po kroku”** | Etap, części, widok rozstrzelony i obróbki; potwierdzenie kontroli | Kolejność technologiczna zatwierdzona przez warsztat. Etap prezentacji nie musi być kolejnością wykonania CAD. |
| **Tryb serwisowy** | Wskazanie uszkodzonego narożnika → właściwy SKU i lista narzędzi | Zweryfikowane zestawy zakupowe i zamienniki. Bez automatycznego zamówienia. |
| **Wkład piankowy warstwami** | Urządzenie + kontury/podparcia + miejsce na palce, przewody i akcesoria | Karta materiału, punkty dozwolonego podparcia i faktyczne wymiary. |
| **Animacja rozpakowania** | Zwolnienie zamków, zdjęcie czapki, wyjęcie urządzenia | Prawdziwe osie/trajektorie, brak kolizji i powrót. Animacja prezentacyjna to osobny dowód od ruchu mechanizmu. |
| **Plan samochodu / palety** | Warianty rozstawu skrzyń, orientacja i dostęp do uchwytów | Obrysy transportowe wraz z kołami, masy, możliwość piętrowania i reguły mocowania. |
| **Podgląd AR** | Finalna bryła w miejscu użytkowania w skali 1:1 | Sprawdzony eksport i jednostki; AR tylko poglądowy. |
| **Historia egzemplarza** | Projekt → wyprodukowany numer → naprawy/pomiary/czujniki | To dopiero podstawa „digital twin”. Sam render lub eksport 3D nie jest sprzężeniem z rzeczywistym produktem. |

## Pięć demonstracji o największej wartości

1. **Jedna zmiana, wszystkie zależności.** Zmieniamy dozwolony wymiar: płyty,
   profile, uchwyty i wycięcia podążają za nim; blokada wyjaśnia konflikt zamiast
   generować uszkodzony model. Powrót odtwarza stan wyjściowy.
2. **Jedna rewizja, komplet dokumentów.** Model, lista części, formatki,
   obróbki, podgląd i pakiet wydania mają wspólną identyfikację. Po zmianie modelu
   stare dokumenty są widocznie nieaktualne.
3. **Operator rozumie plik.** Próbna formatka z uchwytem i zamkiem w DXF,
   czytelne warstwy, strona i wymiary; import do używanego CAM bez ręcznego
   odrysowania. Wynik potwierdza operator, nie sam eksport.
4. **Wiemy, co robi automat.** Ten sam projekt uruchomiony ponownie pokazuje
   czasy etapów, miejsca interwencji i różnicę rewizji; brak danych pozostaje
   brakiem. Możemy porównać ręczny czas przygotowania z czasem automatycznym.
5. **Skrzynia jest serwisowalna.** Kod identyfikuje konkretny egzemplarz i
   jego właściwą rewizję, część wskazana na widoku prowadzi do zatwierdzonego SKU.

Mierzyć czas od wymagań do odebranej dokumentacji, liczbę ręcznych korekt,
odrzucone eksporty, pomyłki rewizji, wykorzystanie płyt i kompletność BOM.
Nie obiecywać procentów oszczędności przed zebraniem własnej próby zleceń.

## Następny wybór

Najpierw rodzina + powiązane obróbki + wydanie. Następnie prawdziwy plik dla
warsztatu i wybór CAM. Magazyn, QR i instrukcje dają wartość na tym samym
fundamencie. AR, fleet/rental i zaawansowana optymalizacja mogą poczekać.
W ten sposób nowe możliwości rozszerzają jeden model produktu, zamiast tworzyć
kilka osobnych aplikacji, które inaczej rozumieją tę samą skrzynię.
