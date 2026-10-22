"""Filesystem-only preview of saved whole-hardware rows; writes one NEW JSON."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Integracja'/'rockpro_cad'/'core_case'))
from hinge_placement import plan_hinge_pairs
from latch_placement import _center, _matrix, _need, _vector


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--poses',required=True)
    parser.add_argument('--catalog',required=True)
    parser.add_argument('--part-code',choices=['B1930','270836'],default='270836')
    for name in ('case-min','source-size','target-size'):
        parser.add_argument('--'+name,required=True,type=float,nargs=3)
    parser.add_argument('--output',required=True,help='New file; existing files are never overwritten')
    args=parser.parse_args(argv)
    try:
        poses_bytes=Path(args.poses).read_bytes()
        catalog_bytes=Path(args.catalog).read_bytes()
        poses=json.loads(poses_bytes.decode('utf-8-sig'))
        catalog=json.loads(catalog_bytes.decode('utf-8-sig'))
        item=next((v for v in catalog['items'] if v['code']==args.part_code),None)
        _need(item is not None,'Part absent from explicitly supplied catalog')
        roots=[r for r in poses['rows'] if r.get('kind')=='assembly' and len(r.get('occurrence_path',[]))==2]
        if args.part_code=='B1930':
            report=dict(status='blocked',scope='offline_classification_preview',production_approved=False,
                        diagnostics=['PART_IS_BRACE_NOT_HINGE'],occurrences=[],predicted_occurrences=[],
                        source_root_ids=[r['id'] for r in roots if r.get('name')=='B1930'],
                        next_step='Use 270836/270836_góra for hinge candidate; do not pair B1930 as hinge halves')
        else:
            source_rows=[]
            selected=[]
            for role,name in [('lid','270836_góra'),('base','270836')]:
                candidates=[]
                for row in roots:
                    if row.get('name')!=name:
                        continue
                    bounds=row['bounding_box_local']
                    _need(bounds.get('valid') is True and bounds.get('unit')=='mm','Measured local bbox in mm required')
                    local=bounds['minimum']+bounds['maximum']
                    _vector(local,6);_matrix(row['matrix_world_mm'])
                    candidates.append((_center(local,row['matrix_world_mm'])[1][0],row,local))
                _need(len(candidates)==2,'Exactly two saved roots required for '+name)
                for side,(_,row,local) in zip(('left','right'),sorted(candidates,key=lambda v:v[0])):
                    source_rows.append(dict(id=row['id'],role=role,side=side,
                                            matrix_world_mm=row['matrix_world_mm'],local_bounds_mm=local))
                    selected.append(row)
            # This pinned historical report shape does not establish raw parity.
            report=plan_hinge_pairs(source_rows,args.case_min,args.source_size,args.target_size)
            report['historical_reader_warnings']=[error for row in selected for error in row.get('errors',[])]
            report['source_capture']=dict(modified=poses.get('cad_document',{}).get('before',{}).get('modified'),
                                          disk_equivalence=poses.get('cad_document',{}).get('disk_equivalence'))
            report['diagnostics']+=['HISTORICAL_REPORT_NOT_RAW_PARITY_PROOF']
            report['next_step']='Fresh raw world orientations/parities and source binding required before native placement'
        report['part_code']=args.part_code
        report['catalog_classification']={key:item.get(key) for key in ('name_pl','name_en','source_url')}
        report['native_proof']='NOT_RUN'
        report['input_sha256']={'poses':hashlib.sha256(poses_bytes).hexdigest(),
                                'catalog':hashlib.sha256(catalog_bytes).hexdigest()}
        with Path(args.output).open('x',encoding='utf-8') as output:
            json.dump(report,output,ensure_ascii=False,indent=2,allow_nan=False)
        print(json.dumps({'status':report['status'],'predicted_count':len(report['predicted_occurrences']),
                          'diagnostics':report['diagnostics'],'output':args.output},ensure_ascii=False))
        return 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print(json.dumps({'status':'error','message':str(error)},ensure_ascii=False))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
