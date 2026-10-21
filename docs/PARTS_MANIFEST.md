# ROC-42 — pełne rozliczenie inwentarza

`Integracja/rockpro_cad/core_case/manifest.py` buduje manifest wyłącznie z JSON
czytnika części. Nie łączy się z IronCAD, nie zapisuje ICS ani SQLite. Wynik ma
`schema_version=1`, `manifest_kind=source_bound_inventory`,
`manifest_stage=inventory_draft` i `runtime_template_compatible=false`.
To propozycja mapowania do dalszego odbioru, a nie wykonywalny TemplateManifest
ROC-15. Nie wolno podstawiać go do planera jako zatwierdzonego szablonu.

## Definicje i tożsamość

- `definitions` przechowuje osobne propozycje definicji; nie scala geometrii na
  podstawie nazwy. `catalog_candidate` jest kandydatem, nie zatwierdzonym SKU.
- `occurrences` rozlicza każdy węzeł źródła, w tym scenę, zespoły i puste zespoły.
  `classification`: structural / physical / reference / empty / unresolved.
  `policy`: rebuild / rigid_move / manual_preserve / replace / structural /
  exclude_explicit. Polityki i role mają własny status pending_confirmation.
- `role_id` opisuje propozycję przypisania roli, `definition_id` definicję,
  `rockpro_id` wystąpienie. Każde ID to UUID zapisane w `identity_map`.
  Pierwszy przebieg nadaje nowe UUID; powtórzenie wymaga zachowania mapy.
  Nazwy, GUID i indeksy CAD nie są stabilnymi identyfikatorami RockPro.
- `source_ref` zachowuje lokalne ID CAD, ścieżkę indeksów, nazwę, materiał CAD,
  błędy i obrys lokalny. Są związane z dokładnym hashem inwentarza i tożsamością
  dokumentu. Zmiana źródła wymaga jawnego uzgodnienia mapy; nie dopasowujemy
  automatycznie po nazwach lub indeksach.
- `source_group_owner_id` wskazuje bezpośredni węzeł grupy źródłowej.
  `inventory_function=geometry_component` rozróżnia zagnieżdżoną geometrię od
  kandydata agregatu. Nie jest to zatwierdzony poziom zakupowego BOM.
  Wszystkie `purchase_quantity` pozostają null, a `physical_quantity_approved`
  false. Liczba liści lub połów zamka nie daje liczby kompletnych produktów.
- `material_cad_raw` pozostaje surową etykietą modelu;
  `purchase_material=null`. Kod nie zamienia aluminium na stal po nazwie okucia.

## Symetria i parowanie

Każda grupa sekcja/rodzina ma jawne członkostwo i grupę symetrii. Zachowujemy
również grupy pustych zespołów, importu i nierozpoznanych części. Grupy wskazują
`case.closed`; rama ściany, orientacja, tryb symetrii i montaż wymagają potwierdzenia.
Nie wyznaczamy ściany, punktu mocowania ani transformacji z nazwy lub SizeBox.
Źródłowy czytnik nie dostarcza pozycji świata: `world_transform.status` oraz
`position_evidence_status` mają wartość `not_available`.

Zamki, zawiasy, profile zamykające oraz koła/gniazda mają osobne zbiory kandydatów
parowania z wymaganymi rolami. Lista konkretnych `pairs` jest pusta. Dopiero
pomiar w potwierdzonych ramach pozwoli sparować wystąpienia. Zgodność X/Y kół
i gniazd, XYZ połówek zamka i orientacje pozostają niewykonane.

## Walidacja i odmowa

`validate_manifest(manifest, inventory=None)` zwraca `ManifestValidation`:
`valid`, `production_ready`, `diagnostics` i `summary`; `as_dict()` serializuje wynik.
Diagnostyka ma pola code/path/message/severity. `error` oznacza uszkodzony schemat
lub sprzeczne rozliczenie, `blocker` brak dowodu odbioru. Niepoprawne typy i
sprzeczne wymagane pola zagnieżdżone dają odmowę, nie wyjątek parsera.
Ten schemat draft nie odrzuca wszystkich dodatkowych pól rozszerzeń.

`valid=true` oznacza poprawne strukturalnie rozliczenie. Osobne
`summary.accounting_complete=true` wymaga spójnego drzewa i liczby dzieci.
Nie oznacza poprawnej geometrii, BOM ani gotowości produkcyjnej.
Walidator wykrywa m.in. brak i duplikat węzła/ID, sprzeczne ID mapy, rodzica,
liczności i członkostwo grup, brak ramy/parowania, puste zespoły naliczone jako
fizyczne, niepoprawny obrys, zmianę surowych dowodów względem inwentarza i
powiązanie z innym źródłem.

Nierozpoznane części, import, nieznany SKU koła, niezatwierdzone mapowanie,
definicje, symetria, parowanie i brak transformacji blokują gotowość. Tak samo
częściowy odczyt oraz Modified=true. Równy hash dysku nie dowodzi zgodności
z dokumentem w pamięci. Dowód loggera pending_finalization pozostaje taki w
manifeście; nie awansujemy go do finalnego audytu bez osobnego dowodu.

Ta wersja nie implementuje odbioru geometrii montażu ani zatwierdzania produkcji.
Zawsze raportuje `MOUNTING_EVIDENCE_NOT_IMPLEMENTED` i
`production_ready=false`. Ręczna zmiana flag na true nie tworzy brakującego dowodu;
`production_approved=true` przy blokadach jest błędem FALSE_PRODUCTION_APPROVAL.
Żaden wpis katalogu referencyjnego nie zostaje automatycznie dopuszczony.

## CLI i powtarzalność

Z katalogu `Integracja`, używając Pythona z przygotowanego venv:

```text
python -m rockpro_cad.core_case.manifest --inventory <inventory.json> --output <nowy-manifest.json>
python -m rockpro_cad.core_case.manifest --inventory <inventory.json> --identity-map <poprzedni-manifest.json> --output <kolejny-manifest.json>
```

Katalog docelowy musi istnieć. Zapis jest wyłączny (`x`): istniejący plik nie
zostanie nadpisany. `--identity-map` wskazuje poprzedni manifest z mapą UUID.
CLI zapisuje dokładny SHA256 bajtów wejścia oraz hash kanonicznej treści JSON.
Ten sam JSON i zapisana mapa dają ten sam manifest. Kod wyjścia: 0 gotowość,
2 prawidłowa propozycja z blokadami, 1 błąd. Obecny etap nie ma ścieżki do 0.
Stdout zawiera raport walidacji. Jest to odczyt zachowanego inwentarza;
`current_cad_state=not_verified_offline_cached_inventory`.

Surowe dane klienta, manifesty Epson, ścieżki, UUID mapowania i raporty pozostają
w ignorowanym `artifacts/`. Do repo trafiają tylko kod, dokumentacja oraz testy
syntetyczne. Nie kopiujemy danych z sąsiedniej bazy wdrożeniowej do Git.

## Dowód bieżącego przyrostu

RED: nowy zestaw testów nie importował nieistniejącego modułu manifestu.
GREEN: syntetyczne regresje schematu, kompletności, ID, przynależności, par,
braku zatwierdzeń, surowych materiałów i wyłącznego zapisu. Polecenie:
`python -m unittest rockpro_cad.core_case.test_manifest -v` z `Integracja`.

Lokalny przebieg z pełnego inwentarza 403 węzłów rozlicza 24 grupy sekcja/rodzina,
11 pustych zespołów oraz cztery zbiory kandydatów parowania. Wszystkie węzły są
ujęte, ale 35 obrysów jest niepoprawnych i źródło ma Modified=true. To kompletny
spis w zakresie hierarchii zespołów/części przy częściowej jakości pól.
Historyczny odczyt 1143 węzłów operacji nie jest wejściem tej wersji.
Montowanie, zmiany CAD, zapis/otwarcie, generator i produkcyjny BOM: NOT RUN.
