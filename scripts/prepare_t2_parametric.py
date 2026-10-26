"""Build a private experimental recipe from the exact reviewed T2 inventory."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Integracja'))
from rockpro_cad.core_case.t2_parametric import make_recipe, REFERENCE, evaluate, validate_parameters


def add_checks(recipe):
    targets=[('wzorzec',REFERENCE),('zmiana_glebokosci_i_wysokosci',dict(REFERENCE,RP_GlebokoscObudowy=667.,RP_WysokoscObudowy=536.5)),
      ('uchwyty_i_wyciecia',dict(REFERENCE,RP_PrzesuniecieUchwytow=5.,RP_PodniesienieUchwytow=4.)),
      ('czapka_i_klapa_rack_nieruchomy',dict(REFERENCE,RP_UniesienieCzapki=120.,RP_OdsuniecieKlapy=180.)),
      ('rack_niezalezny',dict(REFERENCE,RP_UniesienieCzapki=120.,RP_OdsuniecieKlapy=180.,RP_UniesienieRacka=80.)),('powrot',REFERENCE)]
    from rockpro_cad.core_case.profile_rules import value
    recipe['checks']=[]
    for name,pars in targets:
        check={'name':name,'parameters':validate_parameters(pars),'nodes':[],'features':[],'parts':[]}
        for row in recipe['nodes']:
            check['nodes'].append({'id':row['id'],'world_position_mm':[evaluate(row['world_matrix'][3][j],{n:v[j] for n,v in row['motion'].items()},pars) for j in range(3)]})
        for row in recipe['features']:
            expected={'id':row['id'],'position_mm':[value(e,pars) for e in row['position']]}
            if row['scalable']:expected['bounds_mm']=row['bounds_mm'][:3]+[row['bounds_mm'][j]+value(row['dimensions'][j],pars) for j in range(3)]
            check['features'].append(expected)
        for row in recipe['measurements']:
            check['parts'].append({'id':row['id'],'world_position_mm':[evaluate(row['world_matrix'][3][j],{n:v[j] for n,v in row['motion'].items()},pars) for j in range(3)]})
        recipe['checks'].append(check)
    return recipe


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--reference',required=True,type=Path);parser.add_argument('--inventory',required=True,type=Path);parser.add_argument('--source',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);parser.add_argument('--pid',required=True,type=int);args=parser.parse_args()
    recipe=add_checks(make_recipe(json.loads(args.reference.read_text(encoding='utf-8-sig')),args.inventory.read_bytes()))
    recipe['source']=str(args.source.resolve(strict=True));recipe['mode']='t2-parametric';recipe['expected_pid']=args.pid
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f:json.dump(recipe,f,ensure_ascii=False,indent=2)
    print(json.dumps({'nodes':len(recipe['nodes']),'features':len(recipe['features']),'parts':len(recipe['measurements']),'checks':len(recipe['checks']),'parameters':recipe['parameters']}))
