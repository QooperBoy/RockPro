"""Independent offline review; reads only ROC43 inputs, never expected outputs."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Integracja'))
from rockpro_cad.core_case import contracts as c
from rockpro_cad.core_case.manifest import build_manifest, validate_manifest, read_manifest
from rockpro_cad.core_case.test_manifest import inventory

fixtures = json.loads((ROOT / 'tests/core_design/cases.json').read_text(encoding='utf-8'))
recipe = json.loads((ROOT / 'tests/core_design/synthetic_template.json').read_text(encoding='utf-8'))
results = []

def check(label, predicate):
    try:
        good = bool(predicate())
        results.append(dict(check=label, status='PASS' if good else 'FAIL'))
    except Exception as exc:
        results.append(dict(check=label, status='FAIL', exception=type(exc).__name__, message=str(exc)))

def rejected(fn):
    try:
        fn()
    except c.ValidationError:
        return True
    return False

def spec():
    return copy.deepcopy(fixtures['cases'][0]['spec'])

check('order quantity absence stays unknown',lambda:'order_quantity' not in c.validate_case_spec(spec()))
for order_count in (1,7,100000):
    value=spec();value['order_quantity']=order_count
    check('order quantity independent '+str(order_count),lambda value=value,order_count=order_count:c.validate_case_spec(value)['order_quantity']==order_count and c.validate_case_spec(value)['layout']['count']==2)
for bad in (True,False,1.0,0,-1,100001,None,'7',float('nan'),float('inf')):
    value=spec();value['order_quantity']=bad
    check('invalid order quantity '+repr(bad),lambda value=value:rejected(lambda:c.validate_case_spec(value)))

for item in fixtures['cases']:
    request = dict(spec=copy.deepcopy(item['spec']), manifest=copy.deepcopy(fixtures['manifest']),
                   template_recipe=copy.deepcopy(recipe), scenario=dict(operation='plan'))
    before = copy.deepcopy(request)
    check('ROC43 input accepted and detached: ' + item['spec']['case_id'],
          lambda request=request, before=before: c.validate_request(request) == before and request == before)

for field, bad in [('schema_version',True),('schema_version',1.0),('template_version','wrong'),('units','m'),('axes','left-handed-XYZ')]:
    bad_recipe=copy.deepcopy(recipe);bad_recipe[field]=bad
    request=dict(spec=copy.deepcopy(fixtures['cases'][0]['spec']),manifest=copy.deepcopy(fixtures['manifest']),template_recipe=bad_recipe,scenario=dict(operation='plan'))
    check('recipe header rejects '+field+'='+str(bad),lambda request=request:rejected(lambda:c.validate_request(request)))

check('empty component set rejected',lambda:rejected(lambda:c.validate_component_set(dict(schema_version=1,template_version='synthetic-roc43-v1',source_reference='synthetic-review',definitions=[],occurrences=[],symmetry_groups=[]))))

for field in ('schema_version', 'revision', 'expected_revision'):
    for number in (True, 1.0, -1):
        value=spec();value[field]=number
        check(f'{field} rejects {number!r}', lambda value=value: rejected(lambda: c.validate_case_spec(value)))

for number in (True, 1.0, -1, float('nan')):
    request = dict(spec=spec(), manifest=copy.deepcopy(fixtures['manifest']),
                   scenario=dict(operation='reconcile', expected_revision=number, current_revision=999))
    check(f'reconcile rejects revision {number!r}', lambda request=request: rejected(lambda:c.validate_request(request)))

value=spec();value['template_version']='epson-v1'
check('real template rejects synthetic provenance',lambda:rejected(lambda:c.validate_case_spec(value,supported_templates=['epson-v1'])))

for basis in ([[-1,0,0],[0,1,0],[0,0,1]], [[1,0,0],[1,0,0],[0,0,1]],
              [[True,0,0],[0,1,0],[0,0,1]], [[float('inf'),0,0],[0,1,0],[0,0,1]]):
    frame=dict(origin=[0,0,0],u=basis[0],v=basis[1],n=basis[2])
    check('invalid handedness/orthogonality/type/finite basis rejected',lambda frame=frame:rejected(lambda:c.validate_wall_frame(frame)))

inv=inventory();original=copy.deepcopy(inv);draft=build_manifest(inv)
check('builder leaves input unchanged',lambda:inv==original)
check('repeat IDs require same persisted exact-source map',lambda:build_manifest(inv,draft['identity_map'])==draft)

def bad_manifest(label, mutation):
    value=copy.deepcopy(draft);mutation(value)
    result=validate_manifest(value,inv)
    check(label,lambda:not result.valid and not result.production_ready)

def changed_source(m):
    m['source_binding']['source']['sha256_before']='b'*64
    m['source_binding']['source']['sha256_after']='b'*64
    m['identity_map']['source_binding']=copy.deepcopy(m['source_binding'])

bad_manifest('manifest schema rejects bool',lambda m:m.update(schema_version=True))
bad_manifest('manifest schema rejects float',lambda m:m.update(schema_version=1.0))
bad_manifest('source binding tampering rejected against inventory',changed_source)
bad_manifest('part cannot masquerade as empty',lambda m:m['occurrences'][4].update(classification='empty',policy='exclude_explicit'))
bad_manifest('nonempty assembly cannot masquerade as physical',lambda m:m['occurrences'][1].update(classification='physical',policy='rigid_move'))
bad_manifest('orphan definition rejected',lambda m:m['definitions'].append(dict(m['definitions'][0],definition_id='orphan')))
bad_manifest('duplicate pairing group rejected',lambda m:m['pairings'][0]['group_ids'].append(m['pairings'][0]['group_ids'][0]))
bad_manifest('empty pairing group rejected',lambda m:m['pairings'][0].update(group_ids=[]))
bad_manifest('invented required pair roles rejected',lambda m:m['pairings'][0].update(required_roles=['invented']))
bad_manifest('caller promoted improper frame rejected',lambda m:m['frames'][0].update(status='approved',origin=[0,0,0],rotation=[[-1,0,0],[0,1,0],[0,0,1]]))
bad_manifest('missing node rejected',lambda m:m['occurrences'].pop())
bad_manifest('missing symmetry group rejected',lambda m:m['symmetry_groups'].pop())
bad_manifest('caller production flag rejected',lambda m:m.update(production_approved=True))

request=dict(spec=spec(),manifest=draft,scenario=dict(operation='plan'))
check('inventory draft cannot cross planning boundary',lambda:rejected(lambda:c.validate_request(request)))

ip=ROOT/'artifacts/parts-reader-native/20261021T160057Z/inventory.json'
native=json.loads(ip.read_text(encoding='utf-8'))
fresh=build_manifest(native,inventory_sha256=hashlib.sha256(ip.read_bytes()).hexdigest())
native_before=copy.deepcopy(native)
verification=validate_manifest(fresh,native)
check('all 403 source nodes exactly represented',lambda:len(fresh['occurrences'])==403 and {tuple(r['occurrence_path']) for r in native['rows']}=={tuple(o['source_ref']['occurrence_path']) for o in fresh['occurrences']})
check('all cached inventory accounted and planning blocked',lambda:verification.valid and verification.summary['accounting_complete'] and not verification.production_ready)
check('11 empty assemblies remain nonphysical',lambda:sum(o['classification']=='empty' for o in fresh['occurrences'])==11 and all(o['physical_quantity_approved'] is False for o in fresh['occurrences']))
check('35 invalid bboxes retained as blockers',lambda:sum(d.code=='INVALID_BOUNDING_BOX' for d in verification.diagnostics)==35)
check('validator leaves native evidence unchanged',lambda:native==native_before)
check('no geometry planner implementation fabricated',lambda:not callable(getattr(__import__('rockpro_cad.core_case',fromlist=['plan_case']),'plan_case',None)))

report=dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',checks=results,
            native_summary=verification.summary,source_hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['Integracja/rockpro_cad/core_case/contracts.py','Integracja/rockpro_cad/core_case/manifest.py']})
(Path(__file__).parent/'review-results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=len(results),failures=[r for r in results if r['status']!='PASS']),indent=2))
raise SystemExit(0 if report['status']=='PASS' else 1)
