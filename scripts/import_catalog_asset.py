"""Offline H7159 report import, A/B/C preview and optional draft sidecar.

Reads only explicit command-line input paths. Never opens a path from a report,
loads COM, touches a CAD file, or replaces an existing output directory/file.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.core_case.catalog_assets import (
    import_candidate,plan_candidate_pair,build_manifest_sidecar,CatalogAssetError)


def _read_json(path):
    data=path.read_bytes()
    if len(data)>16*1024*1024:raise ValueError('Explicit input JSON exceeds 16 MiB')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('Duplicate JSON key in explicit input file')
            result[k]=v
        return result
    return json.loads(data.decode('utf-8-sig'),object_pairs_hook=pairs)


def _write(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inventory','source-chain','catalog-receipt','face-evidence','poc-receipt','prepared-plans'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--trusted-bindings',type=Path,required=True,
                        help='Explicit independent expected SHA/GUID/subtree/revision bindings; never inferred from report path hints')
    parser.add_argument('--output-dir',type=Path,required=True,help='A new local directory; existing outputs are never replaced')
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--selected-occurrence-id',action='append',default=[])
    args=parser.parse_args(argv)
    if bool(args.manifest)!=bool(args.selected_occurrence_id):
        parser.error('--manifest and an exact --selected-occurrence-id must be supplied together')
    try:
        output=args.output_dir.resolve()
        if output.exists():raise ValueError('Output directory already exists; choose a new directory')
        # All input paths come directly from argv. Report path fields remain inert.
        names=('inventory','source_chain','catalog_receipt','face_evidence','poc_receipt','prepared_plans')
        bundle={name:getattr(args,name).read_bytes() for name in names}
        trusted=_read_json(args.trusted_bindings)
        asset=import_candidate(bundle,trusted)
        plans=[]
        for label,size in (('A',[900,600,330]),('B',[1100,720,410]),('C',[900,600,330])):
            request=dict(schema_version=1,units='mm',frame='case.closed',size=size,
                         thickness=9.,lid_height=80.,edge_inset_mm=100.,count=2)
            plan=plan_candidate_pair(asset,request)
            if plan['status']!='planned':raise ValueError('Offline '+label+' preview blocked: '+str(plan['diagnostics']))
            plans.append((label,plan))
        if plans[0][1]!=plans[2][1]:raise ValueError('A/C return proposal differs')
        sidecar=None;blocked=None
        if args.manifest:
            manifest=_read_json(args.manifest)
            try:sidecar=build_manifest_sidecar(manifest,asset,args.selected_occurrence_id)
            except ValueError as exc:
                blocked=dict(status='blocked',code=getattr(exc,'code','INVALID_MANIFEST'),message=str(exc),
                             production_approved=False,runtime_template_compatible=False)
        # Reserve the new directory only after complete, read-only validation.
        output.mkdir(parents=True,exist_ok=False)
        _write(output/'asset.json',asset)
        for label,plan in plans:_write(output/('preview-'+label+'.json'),plan)
        if sidecar is not None:_write(output/'sidecar.json',sidecar)
        if blocked is not None:_write(output/'sidecar_blocked.json',blocked)
        report=dict(schema_version=1,passed=True,import_status='measured_candidate',
             definition_id=asset['definition_id'],definition_revision=asset['definition_revision'],
             asset_content_sha256=asset['content_sha256'],component_physical_count=13,
             assembly_container_count=sum(r['kind']=='assembly' for r in asset['geometry_signature']),
             preview_cases=3,return_equivalent=True,preview_scope='two rigid H7159 candidate occurrences only; no device or shell generation',
             sidecar_status='blocked' if blocked else 'candidate_only' if sidecar else 'not_requested',
             sidecar_diagnostic=blocked,native_execution='NOT RUN',mounting_approved=False,production_approved=False,
             source_relation=asset['source_binding']['inventory_relation_status'],
             proof_scope=asset['proof_scope'])
        _write(output/'import_report.json',report)
        print(json.dumps(dict(passed=True,output_dir=str(output),sidecar_status=report['sidecar_status'],native_execution='NOT RUN'),ensure_ascii=False))
        return 0
    except (ValueError,KeyError,TypeError,OSError,RecursionError) as exc:
        print(json.dumps(dict(passed=False,code=getattr(exc,'code',type(exc).__name__),message=str(exc),native_execution='NOT RUN'),ensure_ascii=False))
        return 2


if __name__=='__main__':raise SystemExit(main())
