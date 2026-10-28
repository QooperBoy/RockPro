"""Save a NEW local Studio draft and matching JSON/BOM evidence, preserving old drafts."""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad import configurator,studio_requested_parts as p,studio_review,company_catalog
from rockpro_cad.mcp import project_store

def export(output,refresh=False):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    manifest=output/'project-evidence.json'
    old=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else None
    if old and not refresh:raise SystemExit('Output already saved; use --refresh to update the existing draft.')
    if project_store.DB_PATH.exists() and not (output/'before-project.sqlite3').exists():
        with sqlite3.connect(project_store.DB_PATH) as old,sqlite3.connect(output/'before-project.sqlite3') as backup:old.backup(backup)
    d=p.draft();model=configurator.preview(d);review=studio_review.review(d)
    if review['counts']['error']:raise ValueError('Resolve layout errors before saving')
    saved=configurator.save_draft(d,old['draft_id'],old['draft_revision']) if old else configurator.save_draft(d)
    (output/'RockPro_Penn_AdamHall.json').write_text(json.dumps(saved['draft'],ensure_ascii=False,indent=2),encoding='utf-8')
    company={r['id']:r for r in company_catalog.catalog()['items']}
    rows=[]
    for row in model['project_summary']['rows']:
        part=company.get(row.get('pricing_company_id'),{})
        rows.append(dict(row,price_raw=part.get('price_raw'),currency=part.get('currency'),source_unit=part.get('unit'),
            priced_sku=part.get('code'),source_url=part.get('source_url'),purchase_quantity=(row['quantity']+row.get('pack_size',1)-1)//row.get('pack_size',1)))
    evidence=dict(schema='rockpro.requested-case-export/1',draft_id=saved['id'],draft_revision=saved['revision'],
      studio_url='http://127.0.0.1:51342/FVpz8nmQczBPgO4yEpvwEugiffxTCB-J/wizard.html?draft='+saved['id'],
      summary=model['project_summary'],rows=rows,review=review,placements=model['placement']['items'],construction=model['construction']['items'],
      assumptions=['Wnętrze 800 × 650 × 800 mm; wieko dodatkowe 115 mm, zdejmowane.',
        'H2026: pełna siatka źródłowa; wycena wariantu H2026Z jest założeniem, wykończenie wymaga potwierdzenia.',
        'Pozostałe części: uproszczone modele 3D, nie CAD producenta. Wentylacja: gabaryty z rysunku /07Z do potwierdzenia dla /07K.',
        'Profil 30 mm bez dobranego SKU. Wycięcia, pasowanie i nośność uchwytów na zdejmowanym wieku niezatwierdzone.',
        'Ceny według snapshotu firmowego. Waluta i netto/brutto nieoznaczone; brak ceny wentylacji. Nóżki: 8 szt. = 1 opakowanie.'])
    manifest.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(id=saved['id'],url=evidence['studio_url'],output=str(output))))

if __name__=='__main__':export(sys.argv[1],refresh='--refresh' in sys.argv[2:])
