# Wizualny konfigurator RockPro — projekt architektury

27.10.2026. Status: propozycja architektury po przeglądzie repozytorium.
Dokument nie oznacza wdrożenia edytora ani podłączenia pełnych T1/T2 do MCP.

Uzupełnienie: podstawą kart są również wszystkie siedem przeanalizowanych
nowych wzorców, zgrupowanych w sześć kandydatów rodzin. M01/M07 pozostają osobnymi
wariantami ekranów. Pierwszy działający wybór wzorców i szkic wymagań opisuje
[Studio wzorców](REFERENCE_STUDIO_PROTOTYPE.md); nie ograniczamy projektu do T1/T2.

## Decyzja techniczna

Lokalna aplikacja webowa: TypeScript i Three.js w przeglądarce, Python/FastAPI
jako cienki adapter do istniejących usług RockPro, wspólna SQLite i pojedynczy
wykonawca SDK/C#. Pierwsze uruchomienie przez lokalny launcher; później opcjonalne
okno pywebview bez przepisywania interfejsu. Nie zastępujemy dodatku WinForms.

Nowy interfejs jest osobnym klientem wspólnego rdzenia. Rozwijamy go obok obecnego
podglądu tylko do odczytu, aby zachować obserwator i możliwość porównania wyników.
Three.js i dodatki przypinamy do jednej zgodnej wersji; dokumentacja aktualna
online nie dowodzi dostępności każdej metody w naszym lokalnym r180.

## Proces użytkownika

1. Wnętrze: wymagana wolna przestrzeń X/Y/Z w mm, opcjonalne bryły urządzeń,
   ich orientacja, liczba, pianki i komory. Przestrzeń wymagana jest ograniczeniem;
   dodatkowe warstwy nie mogą jej po cichu zmniejszyć. Oddzielnie pokazujemy
   minimalne wnętrze, wynikowe wnętrze, obrys sklejki i gabaryt transportowy.
2. Konstrukcja i otwieranie: wybór rodziny, podział na korpus i pokrywy,
   wysokość/głębokość każdej pokrywy, kierunek i sposób otwierania. Urządzenia
   można przesuwać i obracać, z kontrolą wyjmowania w późniejszym etapie.
3. Zamknięcia: wskazanie krawędzi zawiasów i ścian zamków, liczność i orientacja.
   Para połówek ma wspólną kotwę na płaszczyźnie zamknięcia. Nie jest to dowolny
   przedmiot umieszczony w przestrzeni.
4. Uchwyty i dodatki: przeciąganie z katalogu na ścianę, wybór jednej sztuki lub
   pary, symetrii, wycentrowania i odsunięcia od krawędzi. Domyślnie po dwa
   uchwyty na przeciwnych ścianach prostopadłych do ściany zawiasów; jawna opcja
   po jednym centralnym. Nietypowy układ wymaga zapisanego wyjątku konstruktora.
5. Podstawa: nóżki, cztery koła, wariant piętrowany lub walizkowy z dwoma kołami
   i teleskopem. Koła i górne gniazda są parą interfejsu piętrowania, nie osobnymi
   zestawami ustawianymi ręcznie. Wariant walizkowy początkowo może mieć tylko
   podgląd, dopóki nie zatwierdzimy mocowań i geometrii katalogowej.
6. Sprawdzenie: widok zamknięty/otwarty, warstwy i lista braków. Zatwierdzenie
   konkretnej rewizji koncepcji, plan dokładny, następnie zlecenie do IronCAD.

Kroki są nawigacją po edycji. Nie narzucają kolejności obróbek wykonawcy.
Zmiana wcześniejszego kroku unieważnia zależne wyniki walidacji i plan CAD.

## Rodziny i kompozycja

Katalog docelowy może zawierać 5–10 kart, ale start obejmuje dwa adaptery T1/T2.
Każda karta ma oddzielnie dostępność wizualizacji, planowania i generowania
w konkretnej wersji IronCAD. Brak adaptera nie może kończyć się zastępczym T1.

Początkowe propozycje kart:

- T1: korpus i płytka górna pokrywa na zawiasach.
- T2: podstawa, zdejmowana wysoka czapka, klapa przednia i niezależny rack;
  zachowujemy rzeczywistą topologię wzorca, nie dodajemy zawiasów T1.
- Szafa: korpus i frontowe drzwi z boczną osią zawiasów.
- Szafa z górną pokrywą: drzwi oraz niezależne wieko.
- Skrzynia boczna: boczna klapa i opcjonalna wysuwana platforma.
- Walizka: dwie części, dwa koła i teleskop jako wariant transportu.

Wewnętrzny model to graf zespołów, płyt, otworów dostępowych i złączy.
Złącze ma typ hinged/removable/sliding/fixed, elementy nadrzędne, płaszczyznę
zamknięcia i oś/kierunek ruchu. Reguły profili, obróbek i układu urządzeń należą
do wersjonowanego szablonu rodziny. Nie składamy dowolnych modułów bez sprawdzenia
zgodności. T2 nadal ma szerokość 548 mm w obecnym adapterze; UI to ujawnia.

## Interakcja 3D

Lewa strona: etapy i biblioteka z miniaturami. Środek: obracany podgląd 3D.
Prawa strona: polski inspektor wybranej ściany/elementu; dół: walidacja i postęp.
Do precyzyjnego ustawiania zapewniamy także prosty widok wybranej ściany na wprost.

Raycasting wybiera ścianę, a ruch odbywa się w jej lokalnych osiach u/v.
Pokazujemy punkt montażowy, obrys kołnierza, strefę wycięcia i zajętą przestrzeń
zawiasu/uchwytu. Przyciąganie do siatki, osi, krawędzi i pary oraz cofanie/ponawianie.
Podczas przeciągania działa szybki podgląd JS; po puszczeniu Python waliduje
całe ustawienie i zwraca położenie kanoniczne albo konflikt. Odpowiedzi są wiązane
z rewizją żądania; spóźniona odpowiedź nie nadpisuje nowszej edycji.

W danych zapisujemy relację, np. ściana lewa, środek wysokości korpusu,
para w 1/4 i 3/4 długości. Można też wybrać stały odstęp w mm od wskazanej krawędzi.
Zmiana rozmiaru zachowuje wybrany sens położenia. Surowe współrzędne świata nie
są jedynym zapisem intencji. Katalogowe okucia nie mają narzędzia skalowania.
Płyty/okna zmieniają wymiary poprzez uchwyty i inspektor, zgodnie z regułami rodziny.

## Dane i reguły

Nowy, jawnie wersjonowany ConceptSpec opisuje projekt koncepcyjny, również
niekompletny. Nie rozluźniamy obecnego CaseSpec v1 ani walidatorów, które odrzucają
nieznane pola. Osobny kompilator rodziny tłumaczy koncepcję na obsługiwany plan.
Manifest inwentarza nigdy nie staje się automatycznie wykonywalnym szablonem.

ConceptSpec zawiera: project_id, revision, units=mm, osie, minimalne wnętrze,
family_id/template_version, zespoły/złącza, urządzenia, materiały, wystąpienia
katalogowe, kotwy, grupy symetrii, podstawę, interfejs piętrowania i jawne wyjątki.
Stan kamery i podglądowe otwarcie są poza wymiarami zamkniętej konstrukcji.

Graf obliczeń: wymagane wnętrze → warstwy/piany i konstrukcja → płaszczyzny
ścian/zamknięć → profile i strefy montażowe → okucia → wycięcia/przerwy profili
→ gabaryty i plan. Brak miejsca blokuje wykonanie i pokazuje możliwe rozwiązania.
Program nie zmniejsza wnętrza, nie skaluje SKU i nie zmienia liczności po cichu.

Zielona sklejka #408080. Pokrywa zwykle 10–15% wysokości korpusu, ale musi mieścić
rzeczywisty montaż i luz zawiasu. Sprzeczność wymaga mniejszego okucia albo jawnego
odstępstwa konstruktora; korpus nie rośnie sam. Brak reguły 3× szerokość okucia.

Walidacja ma etapy: poprawność danych; zgodność rodziny; przestrzeń montażowa
i symetria; kompletność technologii; dokładne pomiary CAD. Szybki obrys kolizji
w przeglądarce jest wskazówką, nie dowodem bezkolizyjności brył i ruchu mechanizmu.

## Biblioteka części

Jedna definicja części: ID/SKU i rewizja, kategoria, dopuszczone ściany/orientacje,
punkt i układ montażu, obrys widoczny, strefa zajęta, strefa ruchu, szablony wycięć,
minimalne odstępy oraz dozwolone rodziny. Status wycięcia required/none/unknown
jest odrębny od potwierdzenia wymiarów i akceptacji montażowej/produkcyjnej.
Stan magazynowy to osobny rekord SKU, nie część geometrii ani zgoda montażowa.

Definicja wskazuje lekką siatkę podglądu i osobno natywny zasób katalogowy z hashem,
wersją i zgodnością hosta. Wykorzystujemy obecny model.json/geometry.bin oraz
eksporter; GLB może być późniejszym formatem cache, nie wymogiem pierwszego MVP.
Siatka bez poprawnej kotwy może służyć do podglądu z oznaczeniem braku danych,
ale nie do automatycznego montażu. Bbox nie zastępuje konturu otworu.

Przyjęcie nowego SKU: zachowane źródło → inwentarz → wydzielenie zespołu →
siatka/miniatura → ramy montażowe i obróbki → potwierdzenie i test na kopii.
Przesunięcie wystąpienia przenosi powiązane wycięcia i przerwy właściwych profili.
Usunięcie części edytuje projekt; samo ukrycie warstwy nie usuwa jej obróbek.

## Komunikacja i wykonanie

Przeglądarka → lokalne HTTP API → wspólne usługi Python i SQLite.
MCP i WinForms korzystają z tych samych usług; HTTP nie jest drugim backendem
ani nowym właścicielem danych. Przeglądarka nie musi implementować MCP.

Proponowane operacje: read_catalog, read_family_capabilities, save_concept,
validate_concept, compile_concept, enqueue_plan, read_operation i reconcile_cad.
Zapisy wymagają expected_revision. Plan jest przypięty do rewizji projektu,
szablonu, reguł, katalogu i źródeł. Edycja po planowaniu wymaga nowego planu.

Zlecenie zatwierdzonego planu → trwały dziennik i operation_id → jeden wykonawca
CAD → SDK/C# w wybranym hoście → nowa kopia ICS → pomiary → zapis/otwarcie,
gdy tryb wydania na to pozwala → snapshot i eksport aktualnego podglądu.
COM nie działa w wątku obsługi HTTP ani dowolnych równoległych wątkach WebSocket.
Zachowujemy istniejącą blokadę, kontrolę źródeł i odzyskiwanie niepewnego wyniku.
Rozłączenie przeglądarki nie anuluje rozpoczętego joba i nie uprawnia do ponowienia.

SDK 2023 i 2027 mają osobne adaptery i jawne możliwości. Zasób zapisany w 2027
nie staje się zgodny z 2023 przez zmianę nazwy/formatu żądania. Dotychczasowy
zakaz zapisywania prototypów pozostaje w mocy; implementacja edytora nie uruchamia
automatycznie zapisów ani nie zamyka dokumentów użytkownika.

HTTP obsługuje polecenia, WebSocket dostarcza odtwarzalne zdarzenia postępu
z numerem sekwencji. Trwały stan pochodzi z SQLite/dziennika, nie pamięci socketu.
Usługa słucha na loopback, sprawdza sesję, Origin/Host i ochronę zapisów przed
obcą stroną. Udostępnia wyłącznie jawne zasoby katalogowe; bez arbitrary exec,
otwierania ścieżek z klienta ani publikowania folderów prywatnego transferu.

AI jest opcjonalnym klientem: może zaproponować rodzinę/układ i wyjaśnić konflikt
przez te same operacje. Zatwierdzona koncepcja przechodzi do skryptów bez AI.
Prompt i obraz nie są pośrednim formatem projektu. Ręczne zmiany w IronCAD
wymagają odczytu i uzgodnienia różnic; nie obiecujemy natychmiastowej synchronizacji
każdego ruchu TriBalla. Początkowo synchronizujemy zatwierdzone rewizje.

## Co wykorzystujemy i co trzeba dopisać

| Istnieje | Sposób wykorzystania / granica |
|---|---|
| [Viewer i obserwator](RELIABILITY_AND_OBSERVER.md) | Three.js, rzeczywiste siatki, etapy, kolory, pomiary czasu; brak edycji drag and drop |
| part_registry.py i [rejestr rodzin](PART_FAMILY_REGISTRY_TASK.md) | Te same rodziny/kolory; koła i gniazda razem w etapie 6 |
| [Kontrakty](CASE_CONTRACT.md) i [rdzeń](CORE_RUNTIME.md) | Walidatory, kotwy, rewizje, plan/dziennik; obecny ogólny wykonawca jest syntetyczny |
| layout.py, device_catalog, project_store | Układ urządzeń, dane projektu i jedna SQLite; wejście minimalnego wnętrza wymaga osobnego trybu |
| [T1](CASE_STRUCTURE.md) / [T2](T2_REFERENCE_ANALYSIS.md) | Natywne prototypy i reguły rodzin; pełna integracja z serwisem wymaga adapterów |
| [Katalog](CATALOG_ASSETS.md) | Definicje i źródła kandydatów, bez uznawania wszystkich zasobów za zatwierdzone |

Do dopisania: ConceptSpec i kompilatory rodzin, katalog możliwości, edytor 3D,
adapter HTTP, zapis szkiców, adaptery pełnych T1/T2 do wspólnej usługi, walidacja
montażu i eksportów oraz mapowanie koncepcja ↔ plan ↔ elementy CAD ↔ siatki.

## Kolejność realizacji i odbiór

1. Kontrakt koncepcji i rejestr możliwości rodzin. Odbiór: wnętrze zachowane przy
   zmianie grubości, nieobsługiwany wariant jawnie zablokowany, serializacja rewizji.
2. Edytor T1 bez CAD: wymiary wnętrza, wysokość pokrywy, otwieranie, katalog,
   ściany, pary i cofanie. Odbiór: zapisz/otwórz szkic i odzyskaj identyczny układ.
3. Pełny adapter T1: plan, obróbki, pomiary, eksport. Odbiór: jeden projekt od
   konfiguratora do kopii w wybranym IronCAD; test zmiany i powrotu, a trwałość
   pliku dopiero w odrębnie dozwolonym trybie zapisu. Odbiór wyglądu przez użytkownika.
4. T2: osobna czapka, klapa, rack i ograniczenie szerokości; brak zależności ruchu
   racka od prezentacyjnego unoszenia czapki. Testy rzeczywistych brył i obróbek.
5. Kolejne rodziny: szafa, warianty boczne i transport walizkowy, każda z własnym
   źródłem, regułami i próbą natywną. Widoczne karty podglądowe nie udają generatorów.
6. Rozszerzenia: porównanie rewizji, uzgodnienie pracy ręcznej, wycena/magazyn,
   produkcyjne formatki i opcjonalny asystent. Czas skryptów, oczekiwanie CAD,
   błędy i decyzje AI logujemy osobno od samego początku.

## Dokumentacja technologii

- [Three.js Raycaster](https://threejs.org/docs/pages/Raycaster.html)
- [Three.js TransformControls](https://threejs.org/docs/pages/TransformControls)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [pywebview — komunikacja JavaScript/Python](https://pywebview.flowrl.com/guide/interdomain)

Weryfikacja tej zmiany: przegląd wskazanych modułów i lokalnych odnośników;
dokumentacja architektury, bez zmian runtime, instalacji i operacji CAD.
