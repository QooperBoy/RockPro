"""Prepare a constructor questionnaire without changing or approving catalog data."""
import argparse
from collections import Counter
from datetime import date
import hashlib
from html import escape
import json
from pathlib import Path
from urllib.parse import urlsplit

IDENTITY = {"supplier_or_model_not_identified", "other_supplier_requires_lookup"}
VARIANTS = {"downloaded_candidate_catalog_code_conflict", "configuration_needs_review"}


def question(item):
    status = item["status"]
    if status == "configuration_needs_review":
        return "Potwierdź pełny kod profilu, przekrój i długość handlową. Czy CAD to ten wariant, czy tylko referencja przekroju?"
    if status == "downloaded_candidate_catalog_code_conflict":
        return "Kod katalogu różni się od kandydata CAD. Czy to alias tego samego produktu, czy inny wariant? Podaj pełny SKU i dokument/model potwierdzający."
    text = (item.get("code", "") + " " + item.get("name", "")).casefold()
    for keyword, prompt in [
        ("prowadnic", "Podaj producenta, model, długość złożoną, wysuw, nośność i stronność prowadnicy; podeślij kartę lub CAD."),
        ("siłownik", "Podaj model, siłę [N], długości otwartą/zamkniętą, skok i końcówki montażowe; podeślij kartę lub CAD."),
        ("koło", "Podaj producenta i model: skrętne czy stałe, wariant hamulca, nośność, płytka montażowa i wysokość; podeślij kartę lub CAD."),
        ("profil zamkniety", "Potwierdź materiał, grubość ścianki i długość handlową profilu 15×15 oraz normę lub dostawcę."),
        ("rura", "Potwierdź średnicę zewnętrzną, grubość ścianki i długość roboczą; czy kielich rury pozostaje w konstrukcji?"),
        ("rack", "Podaj producenta/model listwy, gabaryty, standard mocowania i zasilanie; podeślij kartę lub CAD."),
        ("ustalić opis", "Co oznacza ten kod? Podaj nazwę, producenta, pełny SKU i zdjęcie/kartę lub przykład użycia w modelu."),
    ]:
        if keyword in text:
            return prompt
    return "Potwierdź dostawcę, pełny SKU i nazwę. Podeślij kartę, link, zdjęcie lub CAD; dla części własnej rysunek z wymiarami. Warianty z logo/bez logo potwierdź osobno."


def build_report(manifest, digest, report_date):
    if manifest.get("schema") != "rockpro.company-cad-assets/1":
        raise ValueError("Expected preserved company CAD manifest v1")
    items = manifest["items"]
    if len({x["id"] for x in items}) != len(items):
        raise ValueError("Duplicate record IDs; do not merge catalog rows")
    assets = {x["file"]: x for x in manifest.get("assets", [])}
    groups = {"identification": [], "variants": []}
    for item in items:
        group = "identification" if item["status"] in IDENTITY else "variants" if item["status"] in VARIANTS else None
        if group is None:
            continue
        configurations = sorted({assets[p].get("configuration") or "brak konfiguracji"
            for p in item.get("asset_files", []) + item.get("reference_files", []) if p in assets})
        groups[group].append(dict(id=item["id"], code=item.get("code"), name=item.get("name"),
            manufacturer=item.get("manufacturer"), source_status=item["status"],
            candidate_sku=item.get("primary_manufacturer_sku"), candidate_configurations=configurations,
            source_url=item.get("source_url"), question=question(item),
            answer="", confirmed_sku="", evidence_url="", decision="DO POTWIERDZENIA"))
    return dict(schema="rockpro.catalog-questions/1", report_date=report_date,
        source_updated_at=manifest.get("updated_at"), source_manifest_sha256=digest,
        source_catalog_sha256=manifest.get("catalog_sha256"), source_records=len(items),
        source_coverage=dict(Counter(x["status"] for x in items)),
        scope="Pytania do konstruktora; bez zatwierdzenia mapowania, montażu i zmiany źródeł.",
        counts={k: len(v) for k, v in groups.items()}, groups=groups)


def link(url):
    parsed = urlsplit(url or "")
    if parsed.scheme == "https" and parsed.netloc:
        return f'<a href="{escape(url, quote=True)}" rel="noreferrer">Źródło produktu</a>'
    return "Brak potwierdzonego linku"


def render_html(report):
    out = ['<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>RockPro — pytania do Tomka</title>',
        '<style>body{font:16px/1.55 system-ui;color:#193333;background:#f6f8f7;margin:0}main{max-width:1000px;margin:auto;padding:32px}h1,h2{line-height:1.2}article{background:white;border:1px solid #ccd9d5;border-radius:8px;padding:20px;margin:18px 0;break-inside:avoid}small,.meta{color:#52665f}dl{display:grid;grid-template-columns:180px 1fr;gap:6px}dt{font-weight:600}dd{margin:0;overflow-wrap:anywhere}.answer{min-height:65px;border:1px dashed #a5b6b0;padding:10px;margin-top:12px}a{color:#146c63}code{overflow-wrap:anywhere}@media(max-width:600px){main{padding:16px}dl{display:block}dd{margin-bottom:12px}}@media print{body{background:white}main{padding:0}article{border-radius:0}}</style><main>',
        '<h1>RockPro — pytania do Tomka</h1>',
        f'<p class="meta">Przygotowano: {escape(report["report_date"])} · manifest: {escape(str(report["source_updated_at"]))}</p>',
        '<p>Cześć Tomek, potrzebujemy doprecyzować poniższe części, żeby używać właściwych modeli i wycięć. Wystarczy pełny kod, link, zdjęcie lub CAD. Przy częściach własnych przyda się rysunek z wymiarami.</p>',
        '<p><strong>Najpierw sekcja A.</strong> Sekcja B to kandydaci do potwierdzenia, nie zatwierdzone zamienniki. Dokument można wydrukować lub zapisać jako PDF z przeglądarki. Pola odpowiedzi są przeznaczone do wydruku; wersja danych JSON ma osobne pola do uzupełnienia.</p>']
    for group, title in [("identification", "A. Produkty do identyfikacji"), ("variants", "B. Kody i warianty do potwierdzenia")]:
        out.append(f'<h2>{title} — {len(report["groups"][group])} pozycji</h2>')
        for n, row in enumerate(report["groups"][group], 1):
            def esc(value):
                return escape(str(value)) if value is not None else "brak danych"
            out.append(f'<article data-record-id="{esc(row["id"])}"><h3>{n}. {esc(row["code"])}</h3><p>{esc(row["name"])}</p><dl><dt>Producent w źródle</dt><dd>{esc(row["manufacturer"])}</dd><dt>SKU strony / kandydata</dt><dd>{esc(row["candidate_sku"])}</dd><dt>Konfiguracje CAD</dt><dd>{esc(", ".join(row["candidate_configurations"]) or None)}</dd><dt>Link</dt><dd>{link(row["source_url"])}</dd></dl><p><strong>Pytanie:</strong> {esc(row["question"])}</p><div class="answer">Odpowiedź / właściwy SKU / dokument potwierdzający:</div><small>ID rekordu: {esc(row["id"])}</small></article>')
    out.append('<h2>C. Przekazanie projektu na produkcję</h2><ol>')
    for text in [
        "Jakie pliki i listy dostaje warsztat: rysunek z wymiarami, lista formatek, DXF czy gotowy program maszyny?",
        "Które operacje są ręczne, a które na maszynach? Podaj modele maszyn i wymagane formaty plików.",
        "Kto przygotowuje program i wpisuje wymiary: konstruktor, operator czy stolarz?",
        "Jakie tolerancje, luzy, grubości pianki i sposób wycinania naroży należy przyjąć?",
        "Jak oznaczacie części i rewizje? Podeślij jeden przykładowy komplet dokumentów przekazanych do wykonania.",
        "Czy możesz podesłać zbiorczą paczkę CAD/kart faktycznie używanych okuć i wskazać osoby zatwierdzające montaż?",
    ]:
        out.append(f'<li>{escape(text)}</li>')
    out.append('</ol><p>Odpowiedzi nie zmieniają automatycznie katalogu. Najpierw sprawdzamy SKU i dokument, potem osobno geometrię, orientację oraz obróbki na kopii CAD.</p>')
    out.append(f'<footer class="meta">Manifest SHA256: <code>{escape(report["source_manifest_sha256"])}</code><br>Bez cen, stanów magazynowych, danych klientów i pełnych modeli CAD. Nie wykonywano nowego sprawdzenia portali dostawców.</footer></main></html>')
    return "\n".join(out)


def generate(source, output, report_date):
    date.fromisoformat(report_date)
    raw = source.read_bytes()
    report = build_report(json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest(), report_date)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'PYTANIA_DO_TOMKA.html').write_text(render_html(report), encoding='utf-8')
    (output / 'ODPOWIEDZI_DO_UZUPELNIENIA.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--date', required=True)
    args = p.parse_args()
    print(json.dumps(generate(args.manifest, args.output, args.date)['counts']))


if __name__ == '__main__':
    main()
