# Wspólny viewer rodzin — checkpoint wdrożenia

27.10.2026. Rozwinięcie [workstation](WORKSTATION_3D_PREVIEW.md) na siedem wzorców.
To podgląd koncepcji; nie generator parametrycznych ICS ani odbiór technologii.

## Kontrakt i interfejs

Jeden renderer Three.js obsługuje wybór modelu i wariantu. Siatki poprzedniego
modelu oraz materiały są zwalniane. Zmiana wyboru anuluje nieaktualny fetch;
opóźniona odpowiedź nie podmienia geometrii nowego wariantu. Wczytywanie blokuje
sterowanie wymiarami i ruchem. Ustawienia są zachowywane osobno dla każdego SHA
i wariantu, także dla M01/M07 o wspólnych historycznych identyfikatorach CAD.

Rozszerzenie szkicu JSON `preview.motion_values` ma odrębną listę dopuszczonych
ruchów dla konkretnego wariantu. Nieznany ruch, inny hash lub przekroczony zakres
blokują import. Starszy zapis czterech wysuwów workstation pozostaje obsługiwany.
Gabaryt dotyczy siatek sklejki w zapisanym stanie wzorca, nie potwierdzonego
światła wnętrza ani transportowego gabarytu zamkniętego.

Zamierzone moduły podglądu, przypisane jawnymi ścieżkami do inwentarzy:

| Wzorzec | Moduły |
|---|---|
| M01 / M07 | Osłona górna i grupa docisków; warianty pozostają odrębne |
| M02 | Czapka oraz niezależne uniesienie miksera |
| M03 | Pokrywa oraz wnętrze |
| M04 | Cztery półki ze swoimi wkładami |
| M05 | Pokrywa oraz pięć niezależnych wkładów |
| M06 | Pokrywa i dwie niezależne referencje opraw |

Rozsunięcie opisane jako poglądowe nie symuluje potwierdzonego toru zawiasu ani
dopuszczalnego demontażu. Elementy drzewa Rendering są odrębnie przełączane;
nie zaliczamy ich do gabarytu sklejki ani zatwierdzonego zakupowego BOM.

## Źródła geometrii i odzyskiwanie

Sześć dodatkowych eksportów Web Viewer przeszło kontrolę zachowania źródeł,
kopii i kontekstu. Analiza treści wykazała jednak braki siatek, puste dane oraz
niepoprawne wartości w części plików. Sam sukces wywołania eksportera nie jest
dowodem kompletności widoku. U Martina eksporter zwrócił tylko pięć siatek.

Alternatywny `ExportKernelMeshes.cs` używa `IZPart.GetSpecifiedPolyMeshes` na
nowej kopii tylko do odczytu. Sprawdza ID części, obrysy wierzchołków, macierze
i źródła. Nie wywołuje regeneracji, Update ani Save. Materiał pochodzi z API,
a normalne trójkątów wynikają z rzeczywistej siatki. Zamykana jest wyłącznie
własna kopia. Zapisany plik źródłowy oraz istniejące dokumenty pozostają zachowane.

Uwaga wydajnościowa: parametr odchylenia normalnych jest w stopniach. Pierwszy
pełny odczyt użył zbyt drobnego 0,1° i stał się kosztowny na W0968z. Poprawione
ustawienie to 15°, zgodne z przykładem producenta
`ICAPI/Samples/cplusplus/ICAPIQuery/QuerySupport.cpp`, obok `dNormalDev`.
Częściowe wyniki zachowano; nie są zaliczane jako udany kompletny eksport.
Kontrola anulowania działa przed następną częścią i nie przerywa trwającego
wywołania SDK. Nie wolno zwalniać blokady ani zabijać klienta jako pozornego
anulowania, gdy kod nadal wykonuje się w hoście.

W tym checkpointcie pełna regeneracja danych pozostałych modeli oraz próba
WebGL wszystkich siedmiu pozostają W TOKU. Nie przedstawiać jej jako zakończonej.

## Uruchomienie gotowych pakietów

Z `Integracja`, po przygotowaniu prywatnego indeksu danych:

```powershell
.\.venv\Scripts\python.exe -m rockpro_cad.reference_studio --bundle "<pakiet wzorców>" --previews "<index.json>"
```

Indeks `rockpro.preview-index/1` mapuje klucze modeli na katalogi względne
wewnątrz wybranej biblioteki. Serwer sprawdza SHA źródeł, inwentarzy i buforów.
Nie publikuje plików ICS ani dowolnych katalogów. Starszy parametr `--workstation`
nadal działa. Prywatne indeksy i geometria pozostają poza Gitem.

## Dowody checkpointu

- PASS: 9 testów Python/HTTP, w tym różne hashe M01/M07 i listy ruchów.
- PASS: reguły geometrii JS oraz składnia modułów.
- PASS: przełączenie Wing → workstation → Wing, zachowanie ruchu czapki,
  cztery suwaki workstation i jeden kontekst WebGL. Pozostałe modele: w toku.
- Native resize/save/reopen: NOT RUN; bieżące zmiany dotyczą podglądu.

Raporty i dane robocze: `artifacts/family-3d-20261027/`.
