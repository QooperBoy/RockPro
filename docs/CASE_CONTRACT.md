# ROC-15 — kontrakty danych v1

Implementacja: `Integracja/rockpro_cad/core_case/contracts.py`. Jest to czysta
walidacja danych JSON w stdlib, bez CAD, SQLite, zapisu plików i obliczania montażu.
Generator `plan_case` jest osobną warstwą opisaną w [CORE_RUNTIME.md](CORE_RUNTIME.md).
Walidatory kontraktu pozostają bez efektów ubocznych; dawny zestaw RED przechodzi jako regresja.

Każdy walidator zwraca niezależną, głęboką kopię słownika i nie modyfikuje wejścia.
Wynik pozostaje zwykłym JSON do serializacji; nie jest obiektem niemutowalnym.
Zmiana wyniku nie zmienia wejścia. Błędy to `ValidationError` z `code`, `path`,
`message` oraz `as_dict()`. Wersja jest całkowitą liczbą `1`; bool nie jest liczbą.
Migracja wersji wymaga osobnej implementacji, brak cichej konwersji.

## CaseSpec

`validate_case_spec(spec, supported_templates=...)` zachowuje format wejść A/B/C
z `tests/core_design/cases.json`. Kod produkcyjny nie odczytuje fixture ani
oczekiwań. Wymagane są `case_id`, `schema_version`, `revision`, `expected_revision`,
`template_version`, `units="mm"`, `axes="right-handed-XYZ"`, `dimension_source`,
`layout`, `display_gap`. Rewizje są dodatnimi liczbami całkowitymi i muszą się
zgadzać. Domyślna rejestracja zawiera wyłącznie `synthetic-roc43-v1`.
Przekazanie innej jawnej listy wersji przez aplikację nie zatwierdza szablonu.

Opcjonalne `order_quantity` oznacza liczbę identycznych skrzyń w zamówieniu:
liczba całkowita 1–100000, bez bool, float, null ani konwersji tekstu.
To granica danych kontraktu, nie limit zdolności produkcyjnej. Brak pola oznacza
nieznaną wielkość zamówienia i pozostaje brakiem pola; nie ma domyślnej wartości
1. `layout.count` nadal oznacza liczbę urządzeń w jednej skrzyni. Te ilości są
niezależne: walidator nie wyprowadza jednej z drugiej ani nie oblicza zamówienia.

`layout` zawiera wszystkie dotychczasowe pola konfiguratora, bez domyślnego
uzupełniania: `name`, `x/y/z`, `count`, `orientation`, `arrangement`, `gap`,
`clearance`, `separator`, `side`, `side_width/depth/height`, `side_name`,
`thickness`, `lid_height`. Zachowane granice to: wymiary urządzenia/komory
1–5000 mm, liczność 1–30, gap/clearance 0–500, separator 0–50, grubość 1–100,
wieko 2–1000 mm. Zewnętrzny obrys sklejki nie przekracza 10000 mm; korpus i wieko
muszą być wyższe od grubości. Sprawdzana jest wykonalność obrysu wejściowego,
nie geometria, kolizje ani wytrzymałość CAD. Display gap 0–1000 mm jest osobną
wartością prezentacji. Nie dodaje się go do zamkniętego gabarytu.

Opcjonalne `dimension_envelopes` rozdziela wyłącznie nazwy `device`, `internal`,
`plywood_external`, `transport_external`. Każda wartość ma `value=[x,y,z]`,
`units="mm"`, `source`. Zadeklarowane urządzenie, wnętrze i sklejka muszą
odpowiadać wejściom układu. Gabaryt transportowy musi obejmować sklejkę i wymaga
własnego źródła; nie jest automatycznie wyliczany ani zatwierdzany z samej sklejki.

`dimension_source` ma `kind`, `reference`, `confirmation` i opcjonalnie `approval`.
Źródła `synthetic` wymagają `test-only`, bez approval; pozostałe rodzaje to
`manufacturer`, `measurement`, `constructor` ze stanem `unconfirmed` albo
`confirmed`. Potwierdzony wpis wymaga jawnego approval: `scope="dimensions"`,
`reference`, `approved_by`. To sprawdzenie struktury deklaracji, nie
uwierzytelnienie podpisu ani zatwierdzenie wymiaru przez program. Nieznane pola,
w tym ukryte query/exec, są odrzucane. Ciągi nazw i źródeł pozostają danymi.
Źródła i zgody syntetyczne nie mogą zatwierdzać rzeczywistego wzorca.

Komora boczna wymaga `interior_symmetry_approval`. W syntetycznym adapterze jest
to jawny token `SYNTHETIC-*`. Dla rzeczywistego źródła jest to obiekt approval
o dokładnym zakresie `interior`; nie jest to zgoda na wyjątki okuć.

## Kotwy i komponenty

Poniższe kontrakty są formatem gotowych danych komponentów. Nie są formatem
surowego inwentarza ROC-42 ani wyliczonych obserwacji fixture ROC-43.

- `validate_anchor`: `schema_version`, `anchor_id`, `wall_id`, `datum`
  (`panel/profile/closure_plane`), `edge` (`left/right/top/bottom/center/seam`),
  `frame`, `offsets`, `orientation`.
- `frame`: `origin`, `u`, `v`, `n`, każde jako wektor XYZ. Baza musi być
  ortonormalna i prawoskrętna. `orientation` jest macierzą 3×3 z det +1.
  Tolerancja sprawdzenia bazy wynosi 1e-6; nie jest tolerancją produkcyjną.
- `offsets`: osobne `u/v/n`. Każde ma `mode="fixed"` i `value` w mm,
  `mode="proportional"` i udział 0–1 albo samo `mode="centered"`.
  To opis kotwy; obliczanie pozycji od krawędzi należy do ROC-16.
- `validate_part_definition`: `schema_version`, `definition_id`, `family`,
  `units`, `geometry_policy` (`rigid/panel/profile/interior`), dodatnie
  `dimensions=[x,y,z]`, `dimension_source`, opcjonalnie `catalog_reference`.
- `validate_part_occurrence`: `schema_version`, `occurrence_id`, `definition_id`,
  `semantic_role`, `anchor`; opcjonalne `cad_reference` zawiera `document_id`
  i `node_id`. Numer CAD nie zastępuje tożsamości definicji ani wystąpienia.
- `validate_symmetry_group`: `schema_version`, `symmetry_group_id`, `mode`,
  `scope`, `member_ids`, `axes` (lokalne `u/v/n`), `datum`. Tryby: `centered`
  (1 członek), `mirrored_pair` (2), `centered_pattern` (co najmniej 3),
  `scoped_exception`. Ten ostatni wymaga `template_version`, `source_reference`
  i `exception_approval` z `scope`, `reference`, `approved_by`,
  `symmetry_group_id`, `template_version`, `source_reference` zgodnymi z grupą.
  Syntetyczny wyjątek pozostaje syntetyczny. Sprawdzanie faktycznej symetrii
  pozycji i orientacji należy do planera oraz niezależnego odbioru natywnego.

`validate_component_set` przyjmuje `schema_version`, `template_version`,
`source_reference`, `definitions`, `occurrences`, `symmetry_groups`. Sprawdza
unikalne identyfikatory, referencje do definicji i wystąpień, przypisanie każdego
montowanego wystąpienia do dokładnie jednej grupy oraz zgodność `scope` z
`anchor.wall_id`. Wyjątek musi wiązać aktualny szablon i źródło zbioru.
Nie wylicza transformacji ani nie nadaje statusu gotowości produkcyjnej.

## Granica żądania i jawne etapy manifestu

`validate_request` przyjmuje `spec`, `manifest`, `scenario` i opcjonalny
`template_recipe`. Dozwolone operacje to `plan`, `audit`, `resize`, `display`,
`set_group_count`, `reconcile`. Pola każdej operacji mają osobne allowlisty.
Rewizje scenariusza muszą być całkowite i zgodne ze specyfikacją.
Wszystkie dane, również zagnieżdżone obserwacje `current/previous`, muszą być
skończonym JSON. Funkcja zwraca zwalidowane dane wejściowe, nigdy status planned,
listę wykonalnych zmian ani potwierdzenie gotowości.

Są trzy różne etapy danych; wspólna liczba schema_version nie oznacza wspólnego
kształtu:

| Format | Funkcja | Znaczenie |
|---|---|---|
| ROC-43 synthetic summary + recipe | `validate_request` | Jawne wejście testowe. Summary musi wskazywać tę samą wersję, `synthetic=true`, `production_approved=false`; header recipe jest sprawdzany, a AST pozostaje niewykonywanym JSON. |
| ROC-42 `manifest_kind=source_bound_inventory` | `manifest.validate_manifest` | Rozliczony inwentarz i kandydaci ról. `valid=true` nie oznacza `production_ready=true`. |
| ROC-15 komponenty z kotwami i grupami | `validate_component_set` | Jawne, gotowe dane kontraktowe; nadal bez dowodu geometrii i odbioru CAD. |

Żądanie z manifestem inwentarza ROC-42 jest odrzucane jako `MANIFEST_NOT_READY`
(lub `MANIFEST_INVALID` przy błędzie struktury). Brak automatycznej konwersji
`semantic_role_candidate` na `semantic_role`, polityki inwentarza na
`geometry_policy` lub dowolnego węzła na kotwę. Taka promocja wymaga osobnego
zatwierdzonego mapowania, źródeł, reguł i testów. Gotowe komponenty nie są jeszcze
nowym produkcyjnym wariantem TemplateManifest dla planera.

Obsługa legacy ręcznych zmian ROC-43 zachowuje `manual_changes/manual_overrides`
jako propozycje danych. Tekstowe reguły kotew i tokeny zgód nie są wykonywane.
Ta warstwa nie dowodzi kompletności ani poprawności reguł recepty — to pozostaje
zadaniem osobnego planera i odbioru, bez fallbacku do oczekiwań fixture.
Planer jest zaimplementowany, a rzeczywisty katalog nadal wymaga zatwierdzenia.

## Dowody offline

Z katalogu checkoutu:

```powershell
& '..\Integracja\.venv\Scripts\python.exe' -m unittest discover -s Integracja/rockpro_cad/core_case -p test_contracts.py -v
```

Pierwsze RED: 15 błędów asercji wskazujących brak modułu kontraktów, zero errors,
skip i expectedFailure (`artifacts/roc15/red.txt`). Kolejne regresje obejmują
rewizje żądań, rozdział zgód syntetycznych oraz etapów manifestu. GREEN pierwszego
przyrostu jest w `artifacts/roc15/green.txt`, a rozdział ilości w
`artifacts/roc15/order-quantity-green.txt`. Bieżącą całość sprawdza krok
`core-contracts` zwykłego harnessu. To dowody bez CAD; brak planera, natywnego
montażu, zapisu/otwarcia ICS i odbioru produkcyjnego pozostaje jawny.
