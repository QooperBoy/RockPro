"""Filesystem-only wheel/socket evidence preview; no native operations."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Integracja'/'rockpro_cad'/'core_case'))
from wheels_sockets import preview_wheels_sockets


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--poses',required=True)
    parser.add_argument('--catalog',required=True)
    for name in ('case-min','source-size','target-size'):
        parser.add_argument('--'+name,required=True,nargs=3,type=float)
    parser.add_argument('--output',required=True,help='New JSON file; no overwrite')
    args=parser.parse_args(argv)
    try:
        raw=Path(args.poses).read_bytes();catalog_raw=Path(args.catalog).read_bytes()
        source=json.loads(raw.decode('utf-8-sig'));catalog=json.loads(catalog_raw.decode('utf-8-sig'))
        item=next((v for v in catalog['items'] if v.get('code')=='W0968Z'),None)
        if item is None or 'PN - W0968Z' not in item['aliases']:
            raise ValueError('Explicit W0968Z/PN - W0968Z catalog binding required')
        containers=[r for r in source['rows'] if r.get('name')=='koła' and
                    r.get('kind')=='assembly' and len(r.get('occurrence_path',[]))==2]
        if len(containers)!=1:raise ValueError('Unique saved wheel container required')
        prefix=containers[0]['occurrence_path']
        children=[r for r in source['rows'] if r.get('occurrence_path',[])[:-1]==prefix]
        wheel_roots=[r for r in children if r.get('kind')=='assembly']
        socket_roots=[r for r in source['rows'] if r.get('name')=='PN - W0968Z' and
                      r.get('kind')=='assembly' and len(r.get('occurrence_path',[]))==2]
        def normalize(rows):
            result=[]
            for row in rows:
                bounds=row['bounding_box_local']
                if bounds.get('valid') is not True or bounds.get('unit')!='mm':
                    raise ValueError('Whole local bbox in mm required')
                result.append(dict(id=row['id'],matrix_world_mm=row.get('matrix_world_mm'),
                                   local_bounds_mm=bounds['minimum']+bounds['maximum']))
            return result
        report=preview_wheels_sockets(normalize(wheel_roots),normalize(socket_roots),
                                      args.case_min,args.source_size,args.target_size)
        report['wheel_sku']=None
        report['socket_catalog']={k:item.get(k) for k in ('code','name_pl','name_en','source_url')}
        report['unplanned_pad_ids']=[r['id'] for r in children if r.get('kind')=='part']
        report['historical_reader_warnings']=[error for r in wheel_roots+socket_roots for error in r.get('errors',[])]
        doc=source.get('cad_document',{})
        report['source_capture']=dict(modified=doc.get('before',{}).get('modified'),
                                      disk_equivalence=doc.get('disk_equivalence'))
        report['input_sha256']=dict(poses=hashlib.sha256(raw).hexdigest(),catalog=hashlib.sha256(catalog_raw).hexdigest())
        report['next_evidence']=['Four raw whole-wheel world matrices preserving parity',
                                 'Explicit wheel/socket contact XY registrations and four pair IDs',
                                 'Confirmed wheel identity and source binding; no load calculation in this scope']
        encoded=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)
        with Path(args.output).open('x',encoding='utf-8') as output:output.write(encoded)
        print(json.dumps(dict(status=report['status'],predicted_count=len(report['predicted_occurrences']),
                              candidate_pairs=len(report['candidate_pairs']),missing_wheel_pose_ids=report['missing_wheel_pose_ids'],
                              output=args.output)))
        return 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print(json.dumps(dict(status='error',message=str(error)),ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main())
