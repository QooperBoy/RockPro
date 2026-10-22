"""Repeatable source-bound corner POC: hidden ICAPI only; no desktop actions.

An existing light context ICS must already be open. The explicit original is
byte-copied to a new artifacts directory and opened invisibly/read-only. All
source identity, raw face evidence and geometry are rechecked before reuse.
Default is offline planning. --native executes A / resize XYZ / return A.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.parts.native import NativePartsAdapter,file_sha256,same_document_path
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.core_case.corner_mount import capture_corner_binding,plan_corner_resize
from rockpro_cad.core_case.corner_native import background_guard,exclusive_copy,export_corner_assets,execute_corner_case,compare_corner_persistence
from rockpro_cad.cad_lock import cad_writer_lock


def assert_final_hashes(source,source_sha,files):
    if file_sha256(source)!=source_sha:raise RuntimeError('original source hash changed; no acceptance')
    for path,sha in files.items():
        if file_sha256(path)!=sha:raise RuntimeError('pinned code/evidence/asset changed; no acceptance: '+str(path))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('context','source','evidence','trusted-registration','raw-evidence','contact-witnesses','output'):parser.add_argument('--'+arg,type=Path,required=True)
    parser.add_argument('--native',action='store_true')
    args=parser.parse_args();output=args.output.resolve();artifacts=(ROOT/'artifacts').resolve(strict=True)
    if output.exists() or not output.is_relative_to(artifacts):parser.error('output must be a NEW directory within checkout artifacts/')
    source=args.source.resolve(strict=True);context=args.context.resolve(strict=True)
    e=json.loads(args.evidence.read_text(encoding='utf-8'));t=json.loads(args.trusted_registration.read_text(encoding='utf-8'))
    raw=json.loads(args.raw_evidence.read_text(encoding='utf-8'));witnesses=json.loads(args.contact_witnesses.read_text(encoding='utf-8'))
    binding=capture_corner_binding(e,t);sha=file_sha256(source)
    if sha!=binding['source']['sha256_before'] or sha!=raw['snapshot_sha256'] or not same_document_path(source,raw['original_path']):parser.error('explicit original source does not match pinned disk-copy lineage')
    initial=e['case_frame']['size_mm'];plans=[('A-base',initial),('B-resize-XYZ',[1100,720,410]),('C-return',initial)]
    prepared=[{'id':id_,'plan':plan_corner_resize(binding,size)} for id_,size in plans]
    code=[ROOT/'Integracja/rockpro_cad/core_case'/name for name in ('corner_mount.py','corner_native.py','CornerSceneBridge.cs','native.py','native_reader.py','catalog_native.py')]+[ROOT/'Integracja/rockpro_cad/cad_lock.py',ROOT/'Integracja/rockpro_cad/parts/native.py',ROOT/'Integracja/rockpro_cad/parts/reader.py',Path(__file__).resolve()]
    pins={str(p.resolve()):file_sha256(p) for p in code+[args.evidence,args.trusted_registration,args.raw_evidence,args.contact_witnesses]}
    output.mkdir();manifest={'schema_version':1,'native_requested':args.native,'source':str(source),'source_sha256':sha,'context':str(context),'pinned_sha256':pins,'plans':prepared}
    write_receipt_once(output/'prepared_plans.json',manifest)
    if not args.native:print('PLAN_ONLY PASS: three deterministic source-bound plans; no CAD calls');return
    with cad_writer_lock():
        a=NativePartsAdapter.attach(context);guard=background_guard(a.base,output)
        snapshot=output/'source_snapshot.ics';exclusive_copy(source,snapshot)
        already,doc=guard.run('open-disk-copy-hidden',lambda:a.base.OpenFile2(str(snapshot),True,False))
        if already or not same_document_path(doc.Name,snapshot) or str(doc.FileGUID)!=binding['source']['guid'] or doc.Modified:raise RuntimeError('new hidden source ownership/identity guard')
        assets=export_corner_assets(context_source=context,source_path=snapshot,evidence=e,raw_evidence=raw,contact_registration=witnesses,folder=output/'assets')
        results=[]
        for item in prepared:
            print('START '+item['id'],flush=True)
            results.append(execute_corner_case(item['plan'],context_source=context,assets=assets,registration=witnesses,output_dir=output,operation_id=item['id']))
            print('PASS '+item['id']+' '+results[-1]['output_path'],flush=True)
        first,last=results[0]['after_reopen'],results[2]['after_reopen']
        return_comparison=compare_corner_persistence(first['observation']['occurrences'],last['observation']['occurrences'],source_volumes={r['id']:r['body_signature']['volume_m3'] for r in prepared[0]['plan']['occurrences']},semantic_occurrences=True)
        write_receipt_once(output/'return_comparison.json',return_comparison)
        source_after={'path':str(doc.Name),'guid':str(doc.FileGUID),'modified':bool(doc.Modified),'sha256':file_sha256(snapshot)}
        if source_after['modified'] or source_after['guid']!=binding['source']['guid'] or source_after['sha256']!=sha:raise RuntimeError('hidden source changed')
        final_pins=dict(pins);final_pins[str(snapshot)]=sha
        for asset in assets['roots']:final_pins[asset['asset_path']]=asset['asset_sha256']
        assert_final_hashes(source,sha,final_pins)
        write_receipt_once(output/'acceptance.json',{'passed':True,'schema_version':1,'source_path':str(source),'source_sha256_before':sha,'source_sha256_after':file_sha256(source),
          'source_relation':'byte-identical original disk copy, opened hidden read-only; no equivalence to historical unsaved memory claimed','hidden_source_after':source_after,
          'code_and_evidence_unchanged':True,'background_guard_unchanged':True,'physical_parts_per_case':18,'real_corner_parts_per_case':8,'proxy_panel_parts_per_case':10,
          'cases':[{'id':p['id'],'receipt':str(output/p['id']/'corner_native_receipt.json'),'output':r['output_path'],'sha256':r['output_sha256'],'snapshot':r['snapshot_path']} for p,r in zip(prepared,results)],
          'return_equivalence':True,'return_comparison':return_comparison,'visual_qa':'NOT_RUN','production_approved':False,'mounting_approved':False,
          'source_deviations':witnesses['limitations'],'resize_scope':'Regenerated native panels from dimensions; eight source opaque variants translated from three-face registrations; no persistent native mates.'})
        print('HIDDEN CORNER 410429 POC ACCEPTANCE PASS',flush=True)


if __name__=='__main__':main()
