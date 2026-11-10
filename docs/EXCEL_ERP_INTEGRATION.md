# Excel i mini ERP RockPro

## Ustalone środowisko

Użytkownik wskazał, że roboczy Excel edytuje raczej jedna osoba lokalnie.
Rekomendowany pierwszy wariant to Studio i lokalny konektor Windows.
Nie wymaga przenoszenia firmy do usługi chmurowej. Istniejący Excel pozostaje
źródłem stanów do czasu jawnego przełączenia odpowiedzialności na mini ERP.

## Rozpoznany przepływ

Przekazany plik to faktycznie OOXML XLSX, mimo końcówki `.xlsb.xlsx`.
Zawiera sześć arkuszy: Plan Produkcji, Harmonogram zleceń, Zlecenie,
Stany magazynowe, Wycena z planu prod. i Kalkulator. W dostarczonej wersji
nie ma projektu VBA ani zewnętrznych skoroszytów podpiętych jako externalLinks.
Są natomiast ścieżki projektów do folderów sieciowych; traktujemy je jako dane.

Plan Produkcji ma tabelę `Tabela3`, `A4:BZ450`. W jednym wierszu łączy
numer zlecenia, klienta, nazwę skrzyni, liczbę skrzyń, terminy, status,
folder rysunku, gabaryt, sklejkę oraz pary kod części / ilość. Materiały
obejmują także metry profili i powierzchnie płyt/pianek.

Magazyn jest transponowany: jedna część zajmuje kolumnę. Wiersze 2–11
przechowują opis, URL, zdjęcie, kod, masę, cenę, opis wycięcia, stan początkowy,
stan wynikowy i zużycie. Wiersze niżej wiążą zużycie ze zleceniami, następnie
zawierają dostawy. Przykładowy stan B10 to
`B9-SUM(B13:B1001)+SUM(B1004:B1762)`.

Odjęcie materiału jest sterowane polem BZ „Stany magazynowe” w planie,
nie samym zapisaniem projektu ani dowolną zmianą jego statusu. Formuły
zużycia mnożą ilość części przez liczbę skrzyń z kolumny E. Import historii
nie może ponownie zaksięgować zużycia uwzględnionego już w bieżącym stanie.

## Wykonany pierwszy etap

- Oryginał odczytano bez zapisu; zachowano kopię identyfikowaną SHA-256.
- Wyodrębniono 265 pozycji w 10 grupach, z 263 różnymi kodami.
- Odtworzono zdjęcia dla 231 pozycji i zachowano 15 opisów wycięć.
- Studio ma osobny widok „Katalog firmowy”: wyszukiwanie, kategorie,
  zdjęcia, stan zapisany, cena z arkusza, opis wycięcia i kandydaci modeli.
- Istniejące definicje Studio otrzymują referencję do odpowiadającego kodu
  firmowego, jeżeli kod jest zgodny. Nie zmieniono ich tożsamości, rewizji,
  geometrii ani zatwierdzenia montażu.
- Znaleziono 13 pozycji z dokładnym kandydatem kodu w dotychczasowej
  bibliotece; 12 ma kandydata z dostępną siatką. To propozycje, nie zgoda
  na równoważność wariantów ani automatyczne zamówienia.
- Nie importowano stanów jako transakcji, nie rezerwowano i nie wydawano
  materiałów. Nie dopisano zleceń ani cen do roboczego Excela.

Lokalny pakiet jest w ignorowanym `artifacts/erp-company-parts/`.
`scripts/import_company_workbook.py` czyta kopię, sprawdza układ nagłówków,
rozwiązuje osadzone obrazy typu rich value i zapisuje atomowo nowy katalog.
Nie przelicza formuł. Odczyty są oznaczone jako wartości zapisane w pliku.
Zdjęcia pochodzą z przekazanego pliku, bez pobierania witryn producentów.

## Rzeczy do rozstrzygnięcia przed synchronizacją zapisującą

1. `PN - H1052S` i `PN - R1606M` występują po dwa razy. Zachowano osobne
   rekordy źródłowe; nie sumujemy automatycznie zapasu ani nie wybieramy
   pierwszej kolumny jako poprawnej.
2. W katalogu brakuje zapisanych stanów dla 49 pozycji, cen dla 8 i mas dla
   30. Puste pole pozostaje puste, prawidłowe zero pozostaje zerem.
3. W magazynie cena, masa i stan nie mają jawnych jednostek w każdym rekordzie.
   Wycena używa EUR, a plan rozróżnia sztuki, metry i m². Trzeba potwierdzić,
   czy cena profilu dotyczy metra czy odcinka, a płyt — m² czy arkusza.
4. W wycenie komórka R55 ma rzeczywiste urwane odwołanie
   `'Stany magazynowe'!#REF!`. Są też zapisane błędy wyszukiwania i wartości
   w pozycjach wyceny. Nie poprawiano ich bez ustalenia właściwej części.
5. Wiersz zdjęć magazynu ma w XML zapasowe wartości `#VALUE!` z metadanymi
   obrazów. Nie są to 231 błędnych formuł magazynowych: zdjęcia odtworzono
   z osadzonych danych. Należy odróżniać je od błędów obliczeń wyceny.
6. Opisy wycięć są wiedzą źródłową. Zapisy typu `47;94 x 98 mm` mogą łączyć
   odsunięcie z wymiarem i nie definiują same pełnego konturu montażowego.
   Nie nadpisują zatwierdzonych szablonów CAD.

## Docelowa architektura

Studio i dodatek IronCAD korzystają ze wspólnego backendu Python i SQLite.
Excel jest integrowany przez konektor, a nie przez obliczanie zapasów w agencie.
Agent może pomagać w opisach i niejednoznacznych dopasowaniach. Operacje
magazynowe są deterministyczne i mają operatora, historię oraz identyfikator.

Potrzebne encje:

| Encja | Odpowiedzialność |
|---|---|
| Część firmowa | Stały UUID, kod firmy, producent/SKU, wariant, jednostki i aliasy |
| Wariant geometryczny | Model 3D, źródło, rama montażowa, wycięcie i stan potwierdzenia |
| Projekt i rewizja BOM | Parametry, sceny, foldery, części na jedną skrzynię |
| Zlecenie | Klient, ilość skrzyń, terminy i zaakceptowana rewizja BOM |
| Rezerwacja | Zapotrzebowanie, które zmniejsza dostępność, ale nie stan fizyczny |
| Ruch magazynowy | Dostawa, wydanie, zwrot, korekta i ewentualny stan otwarcia |
| Wymiana z Excelem | Źródłowy hash, komórki, zmiany oczekujące i potwierdzenie zastosowania |

Nie tworzymy drugiego, niezależnego magazynu. W repozytorium istnieją już
`inventory_service.py` (partie, rezerwacje, wydania, zwroty, dostawy, dziennik)
i `inventory_intents.py` (zatwierdzane dyspozycje). Trzeba je wykorzystać,
uzupełniając katalog firmowy i jednostki. Obecny model magazynowy obsługuje
całkowite sztuki/arkusze/odpady, więc metrów i m² nie wolno przepuścić przez
niego po obcięciu ułamków. Konwersje i precyzja wymagają jawnego kontraktu.

Przebieg zlecenia: draft → przegląd i akceptacja BOM → zapotrzebowanie
pomnożone przez liczbę skrzyń → rezerwacja → wydanie do produkcji → zużycie
i ewentualny zwrot. Wydanie odejmuje stan raz. Oznaczenie późniejszego
zużycia nie odejmuje tych samych części ponownie. Zmiana geometrii tworzy
nową rewizję BOM i pokazuje różnicę; nie dopisuje drugiego całego zlecenia.

## Kolejność wdrażania do uzgodnienia

1. **Katalog i odczyt magazynu — wykonane.** Excel pozostaje źródłem stanów.
   Uzgodnić duplikaty, warianty, jednostki i brakujące wartości.
2. **BOM i zapotrzebowanie.** Powiązać zatwierdzone firmowe części z rejestrem
   Studio, długościami profili i powierzchniami materiałów. Pokazać koszt
   i braki dla wskazanej liczby skrzyń, bez ruchu fizycznego zapasu.
3. **Kontrolowany zapis zlecenia do Excela.** Przygotować zmianę konkretnych
   komórek i folderu projektu do przeglądu. Próba na nowej kopii przez natywny
   Excel, przeliczenie, zapis/odczyt i kontrola formuł, obrazów i zleceń.
   Dopiero zatwierdzony wynik zastępuje uzgodniony plik roboczy, gdy nie jest
   edytowany. Wykrycie zmiany pliku oznacza konflikt, a nie nadpisanie.
4. **Rezerwacje i produkcja w Studio.** Wybrać moment przełączenia źródła
   prawdy. Przy przełączeniu przyjąć uzgodniony stan otwarcia; nie odtwarzać
   go ponownie przez zaksięgowanie całej starej historii. Excel może wtedy
   pozostać raportem i interfejsem eksportowym.

Dla obecnego lokalnego operatora kontrolowany konektor natywnego Excela
pozwala zachować jego formuły i osadzone obiekty. Sam odczyt OOXML nie
potwierdza przeliczenia; natywna metoda [Application.Calculate](https://learn.microsoft.com/en-us/office/vba/api/excel.application.calculate)
pozwala ograniczyć zakres obliczeń. Rzeczywisty test zapisu/przeliczenia
tego skoroszytu nie był jeszcze wykonywany.

Gdyby firma później wybrała OneDrive dla firm lub SharePoint, można rozważyć
[Microsoft Graph Excel](https://learn.microsoft.com/graph/api/resources/excel?view=graph-rest-1.0).
Nie jest to wymóg dla obecnego lokalnego wariantu.

Każdy zapis musi mieć `operation_id`, oczekiwaną rewizję BOM i oczekiwany
hash pliku, listę różnic przed/po oraz potwierdzenie wykonania. Ponowienie
tej samej operacji ma odczytać poprzedni wynik, nie powtórzyć rozchodu.
Do folderów i klientów używamy stabilnych ID i bezpiecznych nazw, nie
wykonujemy poleceń zawartych w polach ani ścieżkach skoroszytu.
