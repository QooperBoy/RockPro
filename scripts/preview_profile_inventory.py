"""Read saved profile/brace inventory and write a NEW blocked preview JSON."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Integracja'/'rockpro_cad'/'core_case'))
from latch_placement import _need, _vector, _matrix, _center


def build_preview(poses, catalog, case_min, source_size, target_size):
    """Only outer case-edge candidates are computed; source attachment is unknown."""
    for value in (case_min,source_size,target_size):_vector(value)
    _need(all(0 < v <= 10000 for v in source_size+target_size),'Positive sizes in mm required')
    families={'EG-0500_1':'EG-0500/1','EG-0500_2':'EG-0500/2','EG-0113':'EG-0113','B1930':'B1930'}
    items={v['code']:v for v in catalog['items']}
    for alias,code in families.items():
        _need(code in items and alias in items[code]['aliases'],'Explicit catalog alias binding required: '+alias)
    roots=[r for r in poses['rows'] if r.get('name') in families and r.get('kind')=='assembly'
           and len(r.get('occurrence_path',[]))==2]
    _need(roots,'No profile or brace source groups found')
    groups=[];members=[];missing=[]
    for root in roots:
        code=families[root['name']];rigid=code=='B1930'
        children=[r for r in poses['rows'] if r.get('occurrence_path',[])[:-1]==root['occurrence_path']]
        _need(len(children)==root['children'] and all(r.get('kind')=='part' for r in children),
              'Source group coverage or member kind is unresolved')
        group=dict(id=root['id'],code=code,occurrence_path=root['occurrence_path'],physical_ids=[])
        for row in children:
            bounds=row['bounding_box_local']
            _need(bounds.get('valid') is True and bounds.get('unit')=='mm','Valid local bbox in mm required')
            local=bounds['minimum']+bounds['maximum'];_vector(local,6)
            _need(all(local[i+3]>local[i] for i in range(3)),'Positive bbox extents required')
            matrix=row.get('matrix_world_mm');center=None
            if matrix is None:missing.append(row['id'])
            else:_matrix(matrix);center=_center(local,matrix)[1]
            members.append(dict(id=row['id'],group_id=root['id'],code=code,occurrence_path=row['occurrence_path'],
                                resize_policy='rigid_move_only' if rigid else 'cut_length_only_fixed_cross_section',
                                source_matrix_world_mm=matrix,local_bounds_mm=local,
                                observed_local_bbox_spans_mm=[local[i+3]-local[i] for i in range(3)],
                                source_bbox_center_world_mm=center,edge_binding=None,
                                confirmed_cut_axis=None,target_cut_length_mm=None,
                                reader_warnings=row.get('errors',[])))
            group['physical_ids'].append(row['id'])
        groups.append(group)
    edges=[]
    for axis in range(3):
        other=[i for i in range(3) if i!=axis]
        for sides in itertools.product((0,1),repeat=2):
            endpoints=[]
            for size in (source_size,target_size):
                start=case_min[:]
                for index,side in zip(other,sides):start[index]+=side*size[index]
                end=start[:];end[axis]+=size[axis]
                endpoints.append([start,end])
            edge_id='XYZ'[axis]+':'+'/'.join('XYZ'[i]+str(s) for i,s in zip(other,sides))
            edges.append(dict(edge_id=edge_id,run_axis='XYZ'[axis],source_endpoints_mm=endpoints[0],
                              target_endpoints_mm=endpoints[1],source_span_mm=source_size[axis],
                              target_span_mm=target_size[axis],source_member_binding_proven=False))
    doc=poses.get('cad_document',{})
    summary=[]
    for code in families.values():
        rows=[r for r in members if r['code']==code]
        spans={}
        for row in rows:
            value=round(row['observed_local_bbox_spans_mm'][2],6)
            spans[str(value)]=spans.get(str(value),0)+1
        summary.append(dict(code=code,group_count=sum(g['code']==code for g in groups),physical_count=len(rows),
                            missing_world_pose_count=sum(r['source_matrix_world_mm'] is None for r in rows),
                            local_bbox_Z_span_histogram_mm=spans,
                            note='Observed bbox coordinate spans; not an approved extrusion axis or cut length'))
    diagnostics=['SOURCE_RAW_PARITY_UNVERIFIED','SOURCE_MEMBER_EDGE_BINDINGS_UNPROVEN',
                 'PROFILE_CUT_PARAMETERS_UNBOUND','CLOSURE_INTERFACE_DATUM_UNPROVEN']
    if missing:diagnostics.append('SOURCE_WORLD_MATRICES_MISSING')
    return dict(status='blocked',scope='offline_profile_brace_inventory',units='mm',production_approved=False,
                native_proof='NOT_RUN',diagnostics=diagnostics,occurrences=[],groups=groups,members=members,
                summary=summary,missing_world_pose_ids=sorted(missing),case_edge_candidates=edges,
                case_min_mm=case_min[:],source_size_mm=source_size[:],target_size_mm=target_size[:],
                closure_interface_height_mm=None,
                source_capture=dict(modified=doc.get('before',{}).get('modified'),
                                    disk_equivalence=doc.get('disk_equivalence')),
                catalog=[{k:items[code].get(k) for k in ('code','name_pl','source_url','approved_for_automatic_placement')}
                         for code in families.values()])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('poses','catalog','output'):parser.add_argument('--'+name,required=True)
    for name in ('case-min','source-size','target-size'):
        parser.add_argument('--'+name,required=True,nargs=3,type=float)
    args=parser.parse_args(argv)
    try:
        raw=Path(args.poses).read_bytes();catalog_raw=Path(args.catalog).read_bytes()
        report=build_preview(json.loads(raw.decode('utf-8-sig')),json.loads(catalog_raw.decode('utf-8-sig')),
                             args.case_min,args.source_size,args.target_size)
        report['input_sha256']=dict(poses=hashlib.sha256(raw).hexdigest(),catalog=hashlib.sha256(catalog_raw).hexdigest())
        encoded=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)
        with Path(args.output).open('x',encoding='utf-8') as output:output.write(encoded)
        print(json.dumps(dict(status=report['status'],physical_members=len(report['members']),groups=len(report['groups']),
                              missing_world_poses=len(report['missing_world_pose_ids']),output=args.output)))
        return 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print(json.dumps(dict(status='error',message=str(error)),ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main())
