# Graf zależności montażu i obróbek — przyrost offline

26.10.2026: `core_case/machining_rules.py` zawiera teraz `build_operation_graph`
i `validate_operation_graph`. Pomagają wykryć niespójne zależności przed CAD.
Nie wykonują operacji, nie zmieniają MCP, źródeł modeli ani zainstalowanej DLL.
Dotychczasowe kontrakty `machining_step` i `validate_steps` pozostają bez zmian.

## Co reprezentuje graf

Węzeł `mount` oznacza ustalenie montażu/pozycji wskazanego wystąpienia, a nie
fizyczne przykręcenie okucia w hali. Węzeł obróbki zależy od tej pozycji i wskazuje
konkretną płytę lub profil. Graf daje kolejność zależności danych; nie jest
schedulerem, instrukcją wykonania w ICAPI ani kompletną technologią montażu.

Każdy węzeł ma stabilne `id`, znany `type`, `prerequisites`, `owner_mount`,
`target_part` i metadane z `part_registry`. Dla montażu pola właściciela i celu
obróbki są `null`. Dla obróbki oba są obowiązkowe. Obsługiwane rodzaje opisu:
`cutout`, `pocket`, `drilling`, `profile_trim`. Nie przyjmujemy kodu ani dowolnych
nazw metod. Zapis rodzaju obróbki nie zatwierdza jej konturu czy głębokości.

Cel jest jawnie zadeklarowaną dostępną częścią rodziny `panels` albo `profiles`.
`profile_trim` musi wskazywać profil. Nie wolno tą drogą wskazać katalogowego
uchwytu jako bryły do przeróbki. Sam ID celu nie dowodzi istnienia części w
otwartym CAD; docelowy wykonawca będzie musiał sprawdzić mapowanie źródła.

Konstruktor budujący wejście podaje dodatkowe zależności. Builder dodaje
obowiązkową krawędź właściciel montażu → jego obróbka, jeżeli nie została już
podana. Walidator samodzielnego grafu wymaga tej krawędzi i odrzuca jej usunięcie.
Dołączane są metadane **właściciela**, nie materiału celu: wycięcie w sklejce pod
uchwyt należy do etapu uchwytów. Przycięcie profilu na zawias może należeć do
etapu zawiasów, jeśli to zawias jest właścicielem tej operacji.

## Dwie różne kolejności

- `topological_order` respektuje wszystkie jawne zależności. Remisy rozstrzyga
  leksykograficznie po stabilnym ID, więc przestawienie wejściowej listy nie
  zmienia kolejności wynikowej.
- `presentation_groups` bierze warstwy i numerację z `part_registry.contract()`.
  Nie dopisuje krawędzi wynikających z numeru warstwy.

Przykład: pozycja zawiasu jest potrzebna do wyliczenia końca profilu. Montaż
profilu zależy od zawiasu, mimo że profile są w warstwie 2, a zawiasy w 4.
To poprawny graf. Wymuszenie kolejności warstw jako zależności wprowadziłoby
pozorny cykl. Koła, gniazda i podpory nadal mają oddzielne rodziny, lecz wspólny
etap 6; ich obróbki dziedziczą ten sam etap.

## Przykład jawnie syntetyczny

```python
from rockpro_cad.core_case.machining_rules import build_operation_graph

graph = build_operation_graph(
    mounts=[
        {"id": "hinge", "family_id": "hinges", "prerequisites": []},
        {"id": "profile", "family_id": "profiles", "prerequisites": ["hinge"]},
    ],
    machining=[
        {"id": "profile-end", "type": "profile_trim", "owner_mount": "hinge",
         "target_part": "edge", "prerequisites": ["profile"]},
    ],
    target_parts=[{"id": "edge", "family_id": "profiles"}],
)
```

Wynik jest zawsze `executable_template=false`, `production_approved=false`
i `native_execution="NOT RUN"`. Nie zawiera geometrii konturu, progów kolizji,
transformacji ani wyrażenia sterującego CAD. Jest uzupełnieniem sprawdzonego
planu; nie może zostać podstawiony jako natywny szablon.

## Walidacja i granice

Walidator sprawdza dokładne pola, przypięty kontrakt rejestru, unikalne ID,
znane rodziny i typy, powtarzające się zależności, sieroty właściciela/celu/
poprzednika, zgodność etapu z właścicielem i cykle. Ograniczenia: 2048 operacji,
2048 celów, 128 poprzedników na operację, 16 384 krawędzie. Zwraca oddzieloną
kopię danych wraz z obiema kolejnościami. Jeśli wejście zawiera już wyliczoną
kolejność lub grupy, sprawdza też ich zgodność zamiast ufać staremu wynikowi.

Zachowujemy osobny etap walidacji konturów, pasowania i parametrów. Brak obróbki
w grafie nie oznacza, że dany SKU jej nie potrzebuje; taką kompletność musi
potwierdzić katalog i mapowanie ROC-45. Para koło–gniazdo w jednym etapie nie
jest jeszcze sprawdzeniem rozstawu ani nośności. Ukrycie okucia w gotowym viewerze
nie cofa geometrii jego obróbki.

Nie ma jeszcze konsumenta natywnego ani adaptera pełnej receptury T1/T2 do tego
grafu. Receptury mają własne klucze i natywne ID; potrzebne jest jawne mapowanie
ID planu na wystąpienia oraz przypięte źródła. Nie zgadujemy typu operacji ani
właściciela po nazwie ujemnej cechy. Przyszły adapter powinien zbudować graf,
sprawdzić go i zachować jego hash przy planie bez zmieniania obecnych odbiorów.

## Dowody

16 testów `test_machining_rules.py` PASS: 10 dotychczasowych i 6 nowych dla
grafu. Nowe pokrywają niezależność kolejności prezentacji i zależności, etap 6,
cykle/sieroty/duplikaty, nieznane rodziny/typy, zakaz obróbki assetu katalogowego,
naruszone powiązanie właściciela, podmieniony etap, promocję statusu i stabilność
wyniku bez modyfikowania wejść.

Prywatne dowody: `artifacts/night-research-20261026/architecture-graph-tests.json`
oraz `architecture-graph-demo.json`. Demonstracja jest syntetyczna. CAD,
interfejs viewera, instalacja dodatku i zapis/otwarcie ICS: **NOT RUN**.
