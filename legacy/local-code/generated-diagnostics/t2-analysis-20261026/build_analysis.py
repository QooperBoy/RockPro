"""Local evidence reduction only. Does not attach to CAD or modify input files."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import itertools
import json
import math

BASE = Path(__file__).resolve().parent


def read(name):
    return json.loads((BASE / name).read_text(encoding="utf-8-sig"))


def write(name, data):
    (BASE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


inventory = read("native/inventory.json")
receipt = read("native/result.json")
manifest = read("source_manifest.json")
rows = inventory["rows"]
by_id = {r["id"]: r for r in rows}
assert len(by_id) == len(rows), "Non-unique source IDs"
assert len({r["path"] for r in rows}) == len(rows), "Non-unique paths"
assert receipt["passed"] and receipt["remaining_owned"] == 0
assert receipt["before"] == receipt["after"], "User context changed"
assert read("native/addon_cleanup.json")["remaining_count"] == 0
assert sha(Path(manifest["archive"])) == manifest["archive_sha256"]
assert sha(Path(manifest["email"])) == manifest["email_sha256"]
for f in manifest["files"]:
    assert sha(BASE / "source" / f["name"]) == f["sha256"]
assert sha(Path(inventory["copy_path"])) == inventory["source_sha256"]
assert sha(Path(inventory["source"])) == inventory["source_sha256"]

panels = [6436, 6440, 6444, 6448, 6452, 4649, 4653, 4661, 4665, 6412, 6416, 6420, 6428]
groups = {4499: "base", 4601: "front_cap", 7036: "hood"}
root_labels = {"base": "Spód", "front_cap": "Klapa", "hood": "Czapka"}
annotations = {
    4499: ("base", "structural_base", "base_shell"),
    4601: ("front_cap", "removable_front_cap", "front_cap"),
    7036: ("hood", "removable_hood", "hood"),
    6718: ("base", "interior", "interior"),
    4680: ("base", "device_reference", "device_reference"),
    8243: ("base", "mixer_spacers", "interior"),
    6366: ("hood", "removable_rack", "rack"),
    7059: ("hood", "rack_support_right", "rack_support"),
    7814: ("hood", "rack_support_left", "rack_support"),
    7901: ("base", "trolley_handle", "transport"),
}
for root_id in groups:
    for r in rows:
        if r["path"].startswith(f"root/{root_id}/") and r["path"].count("/") == 2:
            name = r["name"]
            if name in ("0300", "0100"):
                annotations[r["id"]] = (groups[root_id], "profile_group", "profiles")
            elif name in ("H7159", "B1121/20", "B1121", "C1351", "41081") or name.startswith(("L905-915", "37600S")):
                role = ("carry_handle" if name == "H7159" else "latch_half" if name.startswith("L905")
                        else "corner_wheel" if name.startswith("37600S") else "corner_or_brace")
                annotations[r["id"]] = (groups[root_id], role, "transport" if role == "corner_wheel" else "handles" if role == "carry_handle" else "latches" if role == "latch_half" else "corners")
for pid in panels:
    owner = groups[int(by_id[pid]["path"].split("/")[1])]
    annotations[pid] = (owner, "outer_panel", owner + "_shell")
for r in rows:
    if r["name"].startswith("Piana"):
        annotations[r["id"]] = (groups[int(r["path"].split("/")[1])], "foam", "interior")


def resolved(r):
    ids = [int(x) for x in r["path"].split("/")[1:]]
    for id_ in reversed(ids):
        if id_ in annotations:
            return id_, annotations[id_]
    return None, (None, "scene_root", None)


mapped = []
for r in rows:
    anchor, (owner, role, stage) = resolved(r)
    b = r.get("bounds_local_m")
    size = None
    if r["type"] == "Z_ELEMENT_PART":
        assert b and len(b) == 6 and all(math.isfinite(x) for x in b)
        assert all(b[i+3] >= b[i] for i in range(3))
        size = [round((b[i+3] - b[i])*1000, 6) for i in range(3)]
    mapped.append({"source_id": r["id"], "source_path": r["path"], "source_name": r["name"],
                   "source_type": r["type"], "owner": owner, "role": role,
                   "proposed_stage": stage, "role_source_id": anchor,
                   "role_status": "observed_part" if r["id"] in panels else "reviewed_assembly_role_inherited",
                   "local_aabb_size_mm": size,
                   "is_procurement_item": False,
                   "note": "Descendants of catalog hardware remain opaque; row count is not BOM."})

upper = [r for r in rows if r["name"] == "L905-915_1" and r["path"].count("/") == 2]
lower = [r for r in rows if r["name"] == "L905-915" and r["path"].count("/") == 2]
pairs = []
used = set()
for a in upper:
    distances = [(math.dist(a["world_mm"][3][:3], b["world_mm"][3][:3]), b) for b in lower]
    distances.sort(key=lambda x: x[0])
    d, b = distances[0]
    assert d < .01 and b["id"] not in used
    assert sum(x < .01 for x, _ in distances) == 1, "Ambiguous latch pairing"
    used.add(b["id"])
    pairs.append({"upper_source_id": a["id"], "lower_source_id": b["id"],
                  "upper_owner": groups[int(a["path"].split("/")[1])], "lower_owner": "hood",
                  "world_origin_distance_mm": d,
                  "status": "unique_coincident_source_origins_not_mechanical_approval"})
assert len(pairs) == 6

hardware_roots = [r for r in mapped if r["source_id"] == r["role_source_id"] and r["role"] in
                  ("carry_handle", "latch_half", "corner_wheel", "trolley_handle", "corner_or_brace")]
profile_parts = [r for r in rows if r["type"] == "Z_ELEMENT_PART" and r["name"] in ("EG-0300", "EG-0100")]
component_cuts = []
for r in rows:
    _, (_, role, stage) = resolved(r)
    # Catalog internal cuts are NOT manufacturing operations of the case.
    if role in ("carry_handle", "latch_half", "corner_wheel", "trolley_handle", "corner_or_brace", "device_reference"):
        continue
    for f in r.get("features", []):
        if f["operation"] != "Z_SUBTRACT":
            continue
        missing = [c["type"] for c in f.get("curves", []) if not any(k in c for k in ("start", "center"))]
        component_cuts.append({"target_source_id": r["id"], "target_path": r["path"],
                               "feature_id": f["id"], "feature_name": f["name"],
                               "candidate_stage": stage, "feature": f,
                               "unresolved_curve_types": missing,
                               "status": "observed_reference_not_executable_template"})

handle_links = [
    {"hardware_source_id": 8155, "panel_source_id": 4665, "feature_id": 8232, "additional_targets": [], "status": "reference_candidate"},
    {"hardware_source_id": 8078, "panel_source_id": 6416, "feature_id": 8238, "additional_targets": [{"part_id": 7824, "feature_id": 8240, "depth_mm": 4}], "status": "reference_candidate"},
    {"hardware_source_id": 8001, "panel_source_id": 6420, "feature_id": 8234, "additional_targets": [{"part_id": 7815, "feature_id": 8236, "depth_mm": 4}], "status": "reference_candidate"},
]
for link in handle_links:
    assert any(f["id"] == link["feature_id"] for f in by_id[link["panel_source_id"]]["features"])
    for extra in link["additional_targets"]:
        assert any(f["id"] == extra["feature_id"] for f in by_id[extra["part_id"]]["features"])

conflicts = [
    ("C01", "Urządzenie", "Mail: wymiary klienta i producenta różne; oczekiwany pomiar sprzętu.", "Blokuje zatwierdzenie wnętrza i dopasowanie urządzenia."),
    ("C02", "Oznaczenia okuć", "PDF: SHD 001, 905-914, EG-100, C1351Z. CAD: H7159, L905-915, EG-0100, C1351.", "Zachować aliasy jako kandydatów. Potwierdzić SKU i rewizje przed zakupowym BOM."),
    ("C03", "Klapa / płyta PL", "PDF formatka 548×404; lokalny obrys CAD 548×424 mm (id 4665).", "Różnica 20 mm; ustalić rewizję i podział/osadzenie profili."),
    ("C04", "Czapka / płyty BP, BL", "PDF 398×555; CAD 418×555,5 mm (id 6416/6420).", "Różnica 20 i 0,5 mm; nie przenosić wymiaru bez uzgodnienia."),
    ("C05", "Boczne listwy klapy", "PDF 398×52; CAD 417,5×51,5 mm (id 4649/4661).", "Sprawdzić końce profili oraz rewizję listy formatek."),
    ("C06", "Rack", "PDF boki 288×272; CAD lokalny obrys 313×288 mm. Długie panele PDF 498×253; CAD 497,5×253.", "Porównać kontur po fazowaniu, orientację, tolerancje i wersję rysunku."),
    ("C07", "Podpory racka", "PDF Phenol 18; CAD jedna strona ma 15 mm, druga 18 mm. Elementy krótkie: PDF 199 mm, obrys CAD ok. 241,283 mm.", "Wyjaśnić asymetrię i długość/kąt cięcia; nie ujednolicać automatycznie."),
    ("C08", "Kontury zamków", "Dwa zaokrąglenia szkicu typu Z_CURVE2D_FILLET nie mają danych w bieżącym eksporcie krzywych.", "Szkic nie jest kompletnym neutralnym szablonem; odczytać fillet SDK lub kopiować pełny szkic na zweryfikowanej kopii."),
    ("C09", "Transport i produkcja", "PDF wprost wymaga sprawdzenia wycięć pod koła i uchwyt wysuwany przy frezowaniu.", "Potrzebne potwierdzenie tolerancji, mocowania, udźwigu oraz realnego toru wysuwu."),
]

parameters = [
    ("case_width", "559", "PDF s.2", "Gabaryt odniesienia z rysunku; nie obwiednia wszystkich okuć."),
    ("case_depth", "660", "PDF s.2", "Gabaryt odniesienia z rysunku."),
    ("case_height", "511", "PDF s.2", "Gabaryt odniesienia z rysunku."),
    ("base_reference_height", "106", "PDF s.2", "Zaznaczony wymiar spodu; nie grubość płyty."),
    ("front_cap_reference_depth", "78", "PDF s.2", "Osobny parametr klapy; nie procent wysokości czapki."),
    ("front_cap_reference_height", "415", "PDF s.2", "Nie zastępuje wymiaru formatki PL."),
    ("outer_sheet_thickness", "6.5", "PDF + 13 płyt CAD", "Oddzielić od profili i osadzenia sklejki."),
    ("rack_sheet_thickness", "9", "PDF + CAD", "Stała grubość materiału, nie skalować wraz z rackiem."),
    ("rack_support_left_thickness", "18", "CAD", "Asymetria względem prawej strony do wyjaśnienia."),
    ("rack_support_right_thickness", "15", "CAD", "PDF podaje Phenol 18; wartość konfliktowa."),
    ("foam_sections", "MG8015/8040/8045/8060/8080", "PDF s.3", "Kody z rysunku; dane materiałowe i ugięcie niepotwierdzone."),
    ("joint_clearance", "unknown", "brak zatwierdzonej tolerancji", "Dla każdego połączenia oddzielnie, niezależnie od rozstawienia widoku."),
    ("trolley_travel", "unknown", "fotografia potwierdza wysuw", "Do pomiaru w CAD; nie wyliczać z wysokości fotografii."),
    ("device_fit", "unconfirmed", "mail", "Wymiary, złącza, przewody, dostęp i środek ciężkości wymagają danych."),
]

summary = {
    "schema": "rockpro.reference-analysis/1", "state": "inventory_draft", "family_candidate": "trolley_mixer_removable_hood_rack",
    "source_sha256": inventory["source_sha256"], "inventory_sha256": sha(BASE / "native/inventory.json"),
    "source_manifest_sha256": sha(BASE / "source_manifest.json"),
    "executable_template": False, "production_approved": False, "device_fit_confirmed": False,
    "node_counts": dict(Counter(r["type"] for r in rows)), "node_count": len(rows),
    "top_level_groups": [{"source_id": k, "name": by_id[k]["name"], "role": groups[k]} for k in groups],
    "parts": mapped, "hardware_roots": hardware_roots, "latch_pairs": pairs, "handle_cutout_candidates": handle_links,
    "profile_part_counts": dict(Counter(r["name"] for r in profile_parts)),
    "observed_case_subtractions": component_cuts,
    "source_subtraction_count_including_catalog_internals": sum(f["operation"] == "Z_SUBTRACT" for r in rows for f in r.get("features", [])),
    "conflicts": [{"id": a, "area": b, "evidence": c, "next_action": d} for a,b,c,d in conflicts],
    "parameters": [{"name": a, "reference_value": b, "source": c, "note": d} for a,b,c,d in parameters],
    "checks": {"source_integrity": "PASS", "unique_ids_and_paths": "PASS", "part_bounds_finite": "PASS",
               "native_copy_inspection": "PASS", "user_context_preserved": "PASS", "owned_docs_closed": "PASS",
               "six_unique_latch_origin_pairs": "PASS", "reference_fit_and_clearances": "NOT RUN",
               "parametric_resize": "NOT RUN", "live_animation": "NOT RUN", "manufacturing_release": "NOT RUN"},
}
assert len(mapped) == 449 and len(panels) == 13
assert summary["profile_part_counts"] == {"EG-0300": 16, "EG-0100": 17}
write("reference_map.json", summary)
with (BASE / "parts_map.csv").open("w", encoding="utf-8-sig", newline="") as f:
    keys = ["source_id", "source_path", "source_name", "source_type", "owner", "role", "proposed_stage", "role_source_id", "local_aabb_size_mm", "is_procurement_item"]
    writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", delimiter=";")
    writer.writeheader(); writer.writerows(mapped)

def table(headings, data):
    clean = lambda x: str(x).replace("|", "/").replace("\n", " ")
    return "\n".join(["| " + " | ".join(headings) + " |", "|" + "---|"*len(headings)] +
                     ["| " + " | ".join(clean(x) for x in row) + " |" for row in data])

report = """# T2 — mapa konstrukcji i analiza wzorca

26.10.2026. Analiza zapisanej rewizji z T2.zip, dokumentacji konstruktora,
pięciu fotografii i maila „Temat II”. Oryginał nie był zapisywany. Odczyt
SDK wykonano na nowej ukrytej kopii w istniejącej sesji IronCAD 2027.

## Główny wniosek

To osobna rodzina skrzyni transportowej do miksera: płytki spód roboczy,
zdejmowana wysoka czapka, zdejmowana klapa czołowa, wyjmowany rack i transport
na dwóch kołach narożnych z rączką teleskopową. W PDF zawiasy mają „---”.
Zdjęcia potwierdzają demontaż czapki/klapy; nie projektować tu zawiasów z T1.
Nie przenosić reguły pokrywy 10–15% na wysoką czapkę tej rodziny.

![T2 po zdjęciu czapki i wyjęciu racka](source/DiGiCo%20Quantum%201%2712_Opened%203.jpg)

## Potwierdzona struktura

449 węzłów = korzeń sceny + 113 zespołów + 335 wystąpień części.
To nie jest liczba zakupowych pozycji. Model zawiera m.in. nity i części
składowe gotowych okuć. Wszystkie 335 odczytanych obrysów mają poprawne,
skończone wartości; nie oznacza to walidacji kształtu ani pasowania.

"""
report += table(["Zespół źródłowy", "ID", "Rola", "Ważna zależność"], [
    ("Spód",4499,"Podstawa robocza / transportowa","Ma również model urządzenia i piany w zespole Srodek."),
    ("Klapa",4601,"Zdejmowana osłona czołowa","Jeden uchwyt; dwa górne elementy zamków łączą z czapką."),
    ("Czapka",7036,"Wysoka osłona zdejmowana ze spodu","W drzewie zawiera również rack i podpory; własność CAD nie oznacza wspólnego ruchu."),
    ("Rack",6366,"Osobny wyjmowany moduł","W modelu pod Czapka, na zdjęciu wyjmowany oddzielnie."),
    ("3473_uchwyt_zewnetrzny(3)",7901,"Rączka teleskopowa","Transport i jej wycięcia powiązać z parą kół oraz stanem wysuwu."),
])
report += "\n\n## Części katalogowe i liczenie\n\n"
report += table(["Element", "Potwierdzone wystąpienia", "Znaczenie"], [
    ("L905-915", "6 par", "12 głównych połówek; 6 zespołów _2 jest zagnieżdżonych, nie dodawać ich do liczby zamków."),
    ("H7159", "3 zespoły", "Dwa na przeciwległych bokach czapki, jeden na klapie. Historyczny wzorzec, nie nowy domyślny układ 4 uchwytów."),
    ("37600S", "2 zespoły", "Koła narożne; nie układ czterech obrotowych kół/gniazd z T1."),
    ("3473", "1 zespół", "Rączka teleskopowa z wewnętrzną hierarchią; nie skalować jej segmentów."),
    ("EG-0300", "16 części", "Dodatkowo 16 zespołów o tej samej nazwie; nie liczyć podwójnie."),
    ("EG-0100", "17 części", "Dodatkowo 17 zespołów o tej samej nazwie; różne długości i zakończenia."),
    ("Płyty zewnętrzne", "13 części", "Wszystkie 6,5 mm. Układ 5 spód + 4 klapa + 4 czapka."),
    ("Rack", "4 płyty + 2 profile 6162", "Grubość płyt 9 mm; perforacja, podłużne otwory i fazy."),
])
report += "\n\n## Pary zamków\n\nPoniższe pary mają jednoznaczne, zgodne początki ram w zapisanej scenie (poniżej 0,01 mm). To dowód parowania wystąpień, nie odbiór mechaniczny zamka.\n\n"
report += table(["Połówka _1", "Zespół drugiej połówki", "Połączenie"], [(p["upper_source_id"],p["lower_source_id"],root_labels[p["upper_owner"]]+" ↔ Czapka") for p in pairs])
report += "\n\n## Mapa płyt\n\nWymiary poniżej to lokalne obrysy części z SDK, w mm. Zachowano kolejność osi; nie jest to automatyczna lista cięcia. Kontur i jego orientacja muszą być zatwierdzone osobno.\n\n"
report += table(["ID", "Zespół", "Nazwa", "Lokalny obrys mm", "Cechy odejmujące"], [
    (r["source_id"],root_labels[r["owner"]],r["source_name"]," × ".join(f"{v:g}" for v in r["local_aabb_size_mm"]),sum(f["operation"]=="Z_SUBTRACT" for f in by_id[r["source_id"]].get("features",[])))
    for r in mapped if r["source_id"] in panels])
report += "\n\n## Wycięcia i obróbki\n\n"
report += "Trzy główne wycięcia uchwytów mają obrys cechy ok. 76,002 × 128 mm i wysunięcie narzędzia 11 mm. To długość odejmowania, nie grubość sklejki ani automatycznie wymagana głębokość kieszeni. Szkic zawiera linie i łuki; zachować pełny kontur, nie zastępować go prostokątem.\n\n"
report += table(["Uchwyt", "Płyta / wycięcie", "Dodatkowe cele"], [(x["hardware_source_id"],f'{x["panel_source_id"]} / {x["feature_id"]}', ", ".join(f'{v["part_id"]} / {v["feature_id"]}: 4 mm' for v in x["additional_targets"]) or "brak wskazanych dodatkowych celów") for x in handle_links])
report += "\n\nTo kandydaci powiązań na podstawie układu wzorca. Nie wykonano próby przesunięcia uchwytu ani automatycznego podążania otworu. Dwie boczne podpory racka mają dodatkowe, różne kontury podfrezowań 4 mm; jeden szablon uchwytu może więc mieć kilka typów celów i głębokości.\n\n"
report += "Wycięcia zamków: 6 cech Upper part w spodzie/klapie i 6 Lower Part w czapce. Przykładowy górny obrys narzędzia 76 × 22 mm, dolny do odczytu z pełnego szkicu. Eksport zachowuje nazwy krzywych FILLET, lecz nie ich geometrię — blokuje to uznanie eksportu za kompletny szablon. Cechy H Block w profilach zachowano jako nieprzypisane odciążenia do osobnego powiązania z okuciem.\n\n"
report += "W spodzie są również okrągłe odejmowania o średnicy 76 mm w płytach przy kołach i wycięcia rączki. Ostateczne szablony wymagają jawnej listy płyt/profili oraz tolerancji, zgodnie z notą konstruktora o sprawdzeniu przy frezowaniu.\n\n"
report += f'Zarejestrowano {len(component_cuts)} odejmowań w elementach skrzyni/racka/pian, po wyłączeniu wewnętrznych cech katalogowych okuć i modelu urządzenia. Cała historia zawiera {summary["source_subtraction_count_including_catalog_internals"]} odejmowań; nie przenosić tej drugiej liczby do procesu produkcji skrzyni.\n'
report += "\n## Parametry i źródła\n\n" + table(["Parametr", "Wartość odniesienia", "Źródło", "Ograniczenie"], parameters)
report += "\n\n## Rozbieżności i braki\n\n" + table(["ID", "Obszar", "Dowód", "Dalsza czynność"], conflicts)
report += """

Nie zakładamy, że PDF albo CAD jest poprawny w każdej z tych rozbieżności.
Obrys nie zastępuje konturu; część różnic może pochodzić z rewizji lub fazowania.
Nie wysłano maila, nie pobierano historycznych linków i nie uznano danych producenta
za potwierdzony pomiar urządzenia.

## Docelowe powiązania i kolejność prac

1. Zamrozić tę rewizję i rozstrzygnąć źródło wymiarów urządzenia. Niezależnie można budować szkielet geometryczny ze statusem „dopasowanie niepotwierdzone”.
2. Zdefiniować lokalny układ rodziny oraz osobne komponenty: spód, czapka, klapa, rack. Zachować surowe drzewo jako pochodzenie; role nie wynikają z samych nazw ani z jednego rodzica CAD.
3. Zdefiniować dwa złącza: spód–czapka i klapa–czapka. Każde ma ramę, profile, tolerancje, cele obróbek i dozwolony kierunek rozłączenia. Nie dodawać fikcyjnej osi zawiasu.
4. Obliczyć wnętrze, formatki i osadzenia profili przed CAD. Osobne grubości 6,5/9/15/18 mm, bez jednolitego RP_Thickness dla wszystkich elementów.
5. Po potwierdzeniu wariantów dodać 6 zamków parami i uchwyty wraz z całym zestawem powiązanych wycięć. Alias SKU, kontur, cel i głębokość są wersjonowane. Istniejąca historia gotowych okuć pozostaje nieprzezroczysta.
6. Rack, jego podpory i piany liczyć z koperty urządzenia i przestrzeni wyjmowania. Podpora racka może jednocześnie być celem płytkiego podfrezowania uchwytu.
7. Transport jako jeden podgraf: para kół narożnych, rączka, jej prowadzenie i wycięcia. Dwa stany rączki oraz pozycja ciągnięcia mają własne kontrole kolizji i dostępności. Nie dodawać górnych gniazd kół z rodziny T1 bez wymagania.
8. Na nowej kopii wykonać zmianę szerokości/głębokości/wysokości, powrót do stanu bazowego, pomiar, zapis/otwarcie i wizualne sprawdzenie. Osobno sprawdzić zdejmowanie obu osłon i wyjmowanie racka.

### Etapy modelu i podglądu (propozycja)

Kolory oznaczają etap w panelu, nie zmianę koloru historycznego wzorca.

| Etap | Kolor | Zawartość |
|---|---|---|
| 0. Dane i obliczenia | szary | Źródła, pomiary, rozbieżności i ramy |
| 1. Poszycie | zielony | Spód, czapka i klapa jako trzy komponenty |
| 2. Profile i złącza | niebieski | Osadzenia, długości, zakończenia, szczeliny |
| 3. Narożniki i wzmocnienia | fioletowy | Ochrona i usztywnienie |
| 4. Uchwyty | pomarańczowy | Uchwyt plus jego otwory i wszystkie podfrezowania |
| 5. Zamknięcia | żółty | Sześć par zamków, obróbki obu stron i profili |
| 6. Transport | turkusowy | Dwa koła, teleskop, prowadzenie i ich obróbki |
| 7. Wnętrze i rack | granatowy | Piany, dystanse, rack i podpory |
| 8. Kontrola i wydanie | czerwony/zielony statusu | Kolizje, demontaż, BOM, formatki, zapis/otwarcie |

Numery opisują prezentację. Graf wykonania wynika z zależności: np. wycięcie
podpory w etapie uchwytu wymaga wcześniejszej definicji/obliczenia podpory.
Podgląd nie może narzucać błędnej kolejności modelowania. Ukrycie gotowego
uchwytu nie usuwa jego otworu. Cofnięcie operacji oznacza osobną zmianę planu.

## Kontrole wykonane w tej analizie

"""
report += table(["Kontrola", "Wynik"], summary["checks"].items())
report += """

PASS oznacza tu poprawny odczyt i spójność mapowania. Nie wykonano zmiany
geometrii, nowego szablonu parametrycznego, próby udźwigu ani odbioru produkcyjnego.
Aktywny projekt użytkownika i jego flaga Modified pozostały takie same.
Własna ukryta kopia została zamknięta; nie pozostawiono dodatkowego projektu w IronCADzie.

## Pliki dowodowe

- `source_manifest.json`: SHA256 ZIP, maila i wszystkich 11 wypakowanych plików.
- `reference_map.json`: 449 węzłów, przypięte role, pary zamków, kandydaci obróbek i braki.
- `parts_map.csv`: tabela filtrowania w Excelu, bez traktowania wierszy jako zakupowego BOM.
- `native/inventory.json`: surowy odczyt części, macierzy i cech.
- `native/result.json`: wynik natywny i stan użytkownika przed/po.
- `pdf_text.json` oraz `render/`: odczyt i renderowane arkusze dokumentacji.
- `validation.json`: końcowe kontrole integralności i kompletności analizy.
"""
(BASE / "T2_ANALIZA.md").write_text(report, encoding="utf-8")
write("validation.json", {"passed": True, "analysis_only": True, "node_count": len(rows),
                          "unique_latch_pairs": len(pairs), "outer_panels": len(panels),
                          "case_subtractions": len(component_cuts), "checks": summary["checks"],
                          "outputs": {n: sha(BASE / n) for n in ("reference_map.json", "parts_map.csv", "T2_ANALIZA.md")}})
print(json.dumps({"passed": True, "nodes": len(rows), "latch_pairs": len(pairs),
                  "case_subtractions": len(component_cuts), "output": str(BASE / "T2_ANALIZA.md")}, ensure_ascii=False))
