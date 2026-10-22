"""Explicit local POC runner; no MCP/UI/DLL changes and no source activation.

The light source case and the validated native H7159 asset must already be open.
Default is plan-only. --native executes three independent copies, stopping on
the first failure. Output must be a new directory inside checkout artifacts/.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.core_case.hardware_poc import candidate_datum,plan_hardware_poc
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.parts.native import file_sha256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['source','asset','face-evidence','catalog-receipt','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--native',action='store_true')
    args=parser.parse_args()
    output=args.output.resolve();artifacts=(ROOT/'artifacts').resolve(strict=True)
    if not output.is_relative_to(artifacts) or output.exists():parser.error('output must be a NEW directory inside checkout artifacts/')
    source=args.source.resolve(strict=True);asset=args.asset.resolve(strict=True)
    evidence=json.loads(args.face_evidence.read_text(encoding='utf-8'))
    catalog=json.loads(args.catalog_receipt.read_text(encoding='utf-8'))
    if not catalog.get('passed') or Path(catalog['asset_path']).resolve()!=asset or file_sha256(asset)!=catalog['asset_sha256']:
        parser.error('asset does not match the prior native source lineage receipt')
    evidence['source_world_matrix_mm']=catalog['source_binding']['expected_world_matrix_mm']
    datum=candidate_datum(evidence,contact_face_id=194,exterior_face_id=353,expected_asset_sha256=catalog['asset_sha256'],expected_guid=evidence['document']['file_guid'])
    plans=[('A-base',[900,600,330]),('B-resize-XYZ',[1100,720,410]),('C-return',[900,600,330])]
    prepared=[{'id':id_,'plan':plan_hardware_poc(size,datum)} for id_,size in plans]
    output.mkdir()
    code=[ROOT/'Integracja/rockpro_cad/core_case'/name for name in ['hardware_poc.py','hardware_poc_native.py','native.py','NativeSceneBridge.cs','catalog_native.py','native_reader.py']]+[Path(__file__).resolve()]
    manifest={'schema_version':1,'native_requested':args.native,'source':str(source),'source_sha256':file_sha256(source),'asset':str(asset),'asset_sha256':file_sha256(asset),
       'face_evidence':str(args.face_evidence.resolve()),'face_evidence_sha256':file_sha256(args.face_evidence),'catalog_receipt':str(args.catalog_receipt.resolve()),
       'catalog_receipt_sha256':file_sha256(args.catalog_receipt),'code_sha256':{str(p.relative_to(ROOT)):file_sha256(p) for p in code},'plans':prepared}
    write_receipt_once(output/'prepared_plans.json',manifest)
    if not args.native:print('PLAN_ONLY PASS: 3 deterministic plans; no CAD called');return
    from rockpro_cad.core_case.hardware_poc_native import execute_hardware_poc
    results=[]
    for item in prepared:
        print('START '+item['id'],flush=True)
        result=execute_hardware_poc(item['plan'],source=source,asset_path=asset,asset_evidence=evidence,output_dir=output,operation_id=item['id'])
        results.append(result);print('PASS '+item['id']+' '+result['output_path'],flush=True)
    # Return has identical measured shape/positions; native node IDs may differ across independently regenerated scenes.
    a,c=results[0]['after_reopen'],results[2]['after_reopen']
    if [r['matrix_world_mm'] for r in a['proxy_measurements']]!=[r['matrix_world_mm'] for r in c['proxy_measurements']]:raise RuntimeError('return proxy pose differs')
    if [h['matrix_mm'] for h in a['handles']]!=[h['matrix_mm'] for h in c['handles']]:raise RuntimeError('return hardware pose differs')
    if any(file_sha256(p)!=manifest['code_sha256'][str(p.relative_to(ROOT))] for p in code):raise RuntimeError('code drifted during native acceptance')
    if file_sha256(source)!=manifest['source_sha256'] or file_sha256(asset)!=manifest['asset_sha256']:
        raise RuntimeError('final source or asset hash drifted; refusing acceptance')
    write_receipt_once(output/'acceptance.json',{'passed':True,'schema_version':1,'source_unchanged':file_sha256(source)==manifest['source_sha256'],
       'asset_unchanged':file_sha256(asset)==manifest['asset_sha256'],'production_approved':False,'physical_parts_per_case':37,'real_parts_per_case':26,'proxy_parts_per_case':11,
       'cases':[{'id':item['id'],'receipt':str(output/item['id']/'hardware_poc_receipt.json'),'output':r['output_path'],'sha256':r['output_sha256']} for item,r in zip(prepared,results)],
       'resize_scope':'Independent regeneration on copied native scenes using wall-relative anchors. No native persistent mates.', 'return_pose_equivalence':True})
    print('NATIVE H7159 POC ACCEPTANCE PASS',flush=True)


if __name__=='__main__':main()
