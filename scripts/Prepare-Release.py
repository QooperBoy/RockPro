"""Create a draft revision bundle from the verified prototype registry receipt."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.core_case.release_bundle import create_bundle,inspect_bundle,prototype_bom,sha

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--registry-report',type=Path,required=True)
p.add_argument('--project-id',required=True)
p.add_argument('--revision-id',required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
report_path=a.registry_report.resolve(strict=True)
report=json.loads(report_path.read_text(encoding='utf-8'));model=Path(report['result']).resolve(strict=True)
if sha(model)!=report['result_sha256']:raise ValueError('Registry model changed')
staging=a.output.resolve().with_name(a.output.name+'-inputs')
staging.mkdir(parents=True,exist_ok=False)
bom=staging/'occurrence_bom.csv';bom.write_bytes(prototype_bom(report))
binding=dict(project_id=a.project_id,revision_id=a.revision_id,model_sha256=report['result_sha256'],
    input_version='registry-report-v1',input_sha256=sha(report_path),
    rule_version='part-registry-v1',rules_sha256=report['registry']['sha256'],
    template_version='epson-prototype-03',template_sha256=report['source_sha256'])
artifacts=[dict(role=role,path=str(path),model_sha256=binding['model_sha256'],revision_id=a.revision_id)
           for role,path in [('bom',bom),('evidence',report_path)]]
checks=[dict(name=r['label'],status='PASS' if r['passed'] else 'FAIL') for r in report['checks']]
checks.append(dict(name='purchase_bom_and_material_approval',status='NOT RUN'))
manifest=create_bundle(model,a.output,binding,artifacts,checks,
    manual_steps=['Rysunki i pliki produkcyjne: przygotowanie i odbiór konstruktora dla tej rewizji.',
                  'BOM zakupowy i materiał: potwierdzić SKU, ilości zakupowe oraz materiał. CSV rozlicza zarządzane korzenie modelu; złożone okucie nie jest automatycznie jedną sztuką zakupową.'])
print(json.dumps(inspect_bundle(a.output/'manifest.json',model),ensure_ascii=False))
