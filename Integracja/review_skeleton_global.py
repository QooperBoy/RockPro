"""Independent global placement audit from measured plate AABBs; no CAD calls."""
import argparse
import json
import math
from pathlib import Path


def validate_global(data, tolerance_mm=0.002):
    checks, errors = [], []
    def check(label, actual, expected):
        ok = math.isfinite(actual) and abs(actual-expected) <= tolerance_mm
        checks.append({'check':label,'actual_mm':actual,'expected_mm':expected,'passed':ok})
        if not ok:
            errors.append(label)
    try:
        params = data['parameters_mm']
        bounds = {}
        for half in ('base','lid'):
            boxes=[p['bbox_mm'] for p in data['halves'][half]['panels']]
            bounds[half]=[min(b[j] for b in boxes) for j in range(3)]+[max(b[j+3] for b in boxes) for j in range(3)]
        for j in range(3):
            check('base origin '+str(j),bounds['base'][j],0)
        for half in ('base','lid'):
            check(half+' X origin',bounds[half][0],0)
            check(half+' Y origin',bounds[half][1],0)
            check(half+' max X',bounds[half][3],params['RP_Length'])
            check(half+' max Y',bounds[half][4],params['RP_Depth'])
        check('base max Z',bounds['base'][5],params['RP_BaseHeight'])
        check('lid min Z',bounds['lid'][2],params['RP_BaseHeight']+params['RP_DisplayGap'])
        check('lid max Z',bounds['lid'][5],params['RP_BaseHeight']+params['RP_DisplayGap']+params['RP_LidHeight'])
        check('actual display gap',bounds['lid'][2]-bounds['base'][5],params['RP_DisplayGap'])
    except (KeyError,ValueError,TypeError) as exc:
        errors.append('Invalid measurement input: '+str(exc))
    return {'passed':not errors,'tolerance_mm':tolerance_mm,'checks':checks,'errors':errors}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('folder',type=Path)
    args=parser.parse_args()
    results=[]
    for path in sorted(args.folder.glob('measured_*.json')):
        result=validate_global(json.loads(path.read_text(encoding='utf-8')))
        result['file']=path.name
        results.append(result)
    report={'passed':bool(results) and all(r['passed'] for r in results),'results':results}
    output=args.folder/'independent_global_review.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'files':len(results),'errors':[{r['file']:r['errors']} for r in results if r['errors']],'report':str(output)},ensure_ascii=True))
    raise SystemExit(0 if report['passed'] else 1)
