"""Fixed in-process 17251S A/B POC using one explicitly owned legacy AddOn.
No application launch, UI, generic execution endpoint, or BRep examination.
"""
import argparse,ctypes,json,os,shutil,subprocess,sys
from pathlib import Path
from probe_latch_inprocess import ROOT,build
from probe_latch_session_bridge import OWNER,OLD_DLL
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.core_case.latch_native import SOURCE_SHA,foreground,_assert_row,_persistence
from rockpro_cad.core_case.corner_native import panel_occurrences,exclusive_copy
from rockpro_cad.core_case.corner_mount import plan_corner_resize
from rockpro_cad.core_case.latch_placement import plan_latch_pairs
from rockpro_cad.parts.native import file_sha256

VENDOR=Path(r'C:\Program Files\IronCAD\2027\ICAPI\Samples\C#\References\interop.ICApiIronCAD.dll')
def managed_name():
    return 'LatchInProcess_'+file_sha256(ROOT/'Integracja/rockpro_cad/core_case/LatchInProcess.cs')[:16]+'.dll'

def compile_managed(folder):
    source=ROOT/'Integracja/rockpro_cad/core_case/LatchInProcess.cs'
    version=int(file_sha256(source)[:4],16)
    identity=folder/'managed_identity.cs'
    identity.write_text('[assembly:System.Reflection.AssemblyVersion("1.0.0.'+str(version)+'")]\n',encoding='utf-8')
    command=[r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe','/nologo','/target:library','/platform:x64','/out:'+str(folder/managed_name()),'/reference:'+str(VENDOR),'/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll',str(source),str(identity)]
    result=subprocess.run(command,capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    write_receipt_once(folder/'managed_compile.json',{'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'source_sha256':file_sha256(source),'vendor_sha256':file_sha256(VENDOR)})
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    shutil.copyfile(VENDOR,folder/VENDOR.name)

def validate_case(before,after,case,source_rows):
    # Basic placement only. No internal feature/body access.
    _persistence(before,after)
    source={r['id']:r for r in source_rows}
    for observation in (before,after):
        if observation['top_level_roots']!=16:raise RuntimeError('Expected16roots')
        physical=[r for family in ('panels','corners','latches') for r in observation[family]]
        if len({r['native_id'] for r in physical})!=22:raise RuntimeError('Duplicate/missing whole physical IDs')
        for p in case['panels']:
            actual=next(r for r in observation['panels'] if r['name']=='RP:'+p['id'])
            _assert_row(actual,{'matrix_world_mm':p['native_matrix_mm'],'local_bounds_mm':p['local_bounds'][0]+p['local_bounds'][1]})
        for p in case['corners']:
            _assert_row(next(r for r in observation['corners'] if r['source_id']==p['id']),p)
        measured=[]
        for p in case['latches']:
            r=next(r for r in observation['latches'] if r['source_id']==p['id']);_assert_row(r,p)
            if any(r[k]!=source[p['id']][k] for k in ('name','kind','children_count')):raise RuntimeError('Opaque root identity/count changed')
            measured.append({'id':p['id'],'role':p['role'],'side':p['side'],'matrix_world_mm':r['matrix_world_mm'],'local_bounds_mm':r['local_bounds_mm']})
        plan_latch_pairs(measured,case['case_min'],case['size'],case['size'])
    gaps={}
    for r in measured:
        box=r['local_bounds_mm'];m=r['matrix_world_mm'];local=[(box[i]+box[i+3])/2 for i in range(3)]
        x=sum(local[i]*m[i][0] for i in range(3))+m[3][0]
        gaps.setdefault(r['role'],{})[r['side']]=x-case['case_min'][0] if r['side']=='left' else case['case_min'][0]+case['size'][0]-x
    return gaps

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--context',type=Path,required=True)
    p.add_argument('--corner-receipt',type=Path,required=True);p.add_argument('--corner-assets',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--expected-pid',type=int,required=True)
    p.add_argument('--compile-only',action='store_true');a=p.parse_args();folder=a.output.resolve()
    if folder.exists() or not folder.is_relative_to(ROOT/'artifacts'):p.error('New checkout artifacts directory required')
    if a.compile_only:folder.mkdir();build(folder,managed_name());compile_managed(folder);print('COMPILE PASS');return
    import comtypes.client
    from comtypes.automation import IDispatch
    app=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True)
    user=ctypes.WinDLL('user32');user.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    def state():
        pid=ctypes.c_ulong();hwnd=int(app.HWnd);user.GetWindowThreadProcessId(ctypes.c_void_p(hwnd),ctypes.byref(pid))
        return {'pid':pid.value,'hwnd':hwnd,'foreground':foreground(),'active_path':str(app.ActivePage.FullName),'saved':bool(app.ActivePage.Saved),'source_sha256':file_sha256(a.source)}
    before=state()
    if before['pid']!=a.expected_pid or not before['saved'] or before['source_sha256']!=SOURCE_SHA or before['active_path'].casefold()!=str(a.context.resolve()).casefold():raise RuntimeError('Exact saved context/source/host guard failed')
    def disp(v):return v._comobj if hasattr(v,'_comobj') else v.QueryInterface(IDispatch)
    collection=app.AddOns;matches=[]
    for i in range(int(collection.Count)):
        addon=disp(disp(collection)._invoke(5,1,0,i))
        if addon._invoke(3,2,0)==OWNER:matches.append(addon)
    if len(matches)!=1:raise RuntimeError('Exact owned AddOn missing/ambiguous')
    addon=matches[0];old={'dll':str(addon._invoke(13,2,0)),'function':str(addon._invoke(12,2,0))}
    if old['dll'].casefold()!=str(OLD_DLL).casefold() or old['function']!='RockProLatchProbe':raise RuntimeError('Owned configuration changed')
    with cad_writer_lock():
        folder.mkdir();write_receipt_once(folder/'before_compile.json',before);dll=build(folder,managed_name());compile_managed(folder)
        before_execute=state()
        if any(before_execute[k]!=before[k] for k in before if k!='foreground'):raise RuntimeError('Context changed during offline build')
        before=before_execute
        write_receipt_once(folder/'before_execute.json',before)
        pins={str(q):file_sha256(q) for q in (dll,folder/managed_name(),folder/VENDOR.name)}
        exclusive_copy(a.source,folder/'source_disk_copy.ics')
        common={'expected_pid':a.expected_pid,'original_source':str(a.source.resolve()),'context':str(a.context.resolve())}
        write_receipt_once(folder/'source_request.json',dict(common,source_copy=str(folder/'source_disk_copy.ics')))
        write_receipt_once(folder/'pins.json',pins)
        def check_cancel():
            if (folder/'cancel.marker').exists():raise RuntimeError('Cancelled at safe phase boundary')
        phase_guards=[]
        def invoke(phase):
            nonlocal before
            check_cancel()
            for q,sha in pins.items():
                if file_sha256(q)!=sha:raise RuntimeError('Compiled bridge pin changed')
            immediate=state()
            if any(immediate[k]!=before[k] for k in before if k!='foreground'):raise RuntimeError('Pre-execution context changed')
            before=immediate
            write_receipt_once(folder/(phase+'_outer_before.json'),before)
            addon._invoke(13,4,0,str(dll));addon._invoke(12,4,0,'RockProLatchManaged')
            if addon._invoke(3,2,0)!=OWNER or str(addon._invoke(13,2,0)).casefold()!=str(dll).casefold() or addon._invoke(12,2,0)!='RockProLatchManaged':raise RuntimeError('Fixed owned export differs')
            addon._invoke(11,1,0)
            report=json.loads((folder/(phase+'_receipt.json')).read_text(encoding='utf-8'))
            if report['process_id']!=a.expected_pid or not report['passed'] or report['remaining_owned']!=0:raise RuntimeError('In-process '+phase+' failed: '+str(report))
            phase_after=state()
            write_receipt_once(folder/(phase+'_outer_after.json'),phase_after)
            phase_guards.append({'phase':phase,'before':before,'after':phase_after,'unchanged':phase_after==before})
            if phase_after!=before:raise RuntimeError('Post-execution context/foreground changed')
        result={'passed':False,'before':before}
        try:
            print('SOURCE WHOLE ROOT READ/EXPORT',flush=True);invoke('source');check_cancel()
            fresh=json.loads((folder/'source_result.json').read_text(encoding='utf-8'));rows=fresh['rows']
            receipt=json.loads(a.corner_receipt.read_text(encoding='utf-8'));assets=json.loads(a.corner_assets.read_text(encoding='utf-8'))
            if not receipt['passed'] or receipt['source_sha256_before']!=SOURCE_SHA or assets['source_sha256']!=SOURCE_SHA:raise RuntimeError('Pinned corner provenance differs')
            frame=receipt['plan']['binding']['case_frame']['matrix_world_mm'];minimum=frame[3][:3];cases=[]
            for label,size in [('A_914x602x352',[914,602,352]),('B_1100x720x410',[1100,720,410])]:
                latch=plan_latch_pairs([{k:r[k] for k in ('id','role','side','matrix_world_mm','local_bounds_mm')} for r in rows],minimum,[914,602,352],size);corner=plan_corner_resize(receipt['plan']['binding'],size)
                ca=[]
                for root in corner['assemblies']:
                    asset=next(r for r in assets['roots'] if r['source_id']==root['id']);ca.append(dict(asset,matrix_world_mm=root['matrix_world_mm']))
                la=[dict(r,asset_path=next(s['asset_path'] for s in rows if s['id']==r['id']),asset_sha256=next(s['asset_sha256'] for s in rows if s['id']==r['id'])) for r in latch['occurrences']]
                cases.append({'label':label,'size':size,'case_min':minimum,'output':str(folder/('POC_zatrzaski_'+label+'.ics')),'panels':panel_occurrences(size,frame),'corners':corner['occurrences'],'corner_assets':ca,'latches':la})
            check_cancel()
            write_receipt_once(folder/'execute_request.json',dict(common,cases=cases))
            print('EXECUTE A/B',flush=True);invoke('execute');results=[]
            for c in cases:
                pre=json.loads((folder/(c['label']+'_before.json')).read_text(encoding='utf-8'));post=json.loads((folder/(c['label']+'_after.json')).read_text(encoding='utf-8'))
                gaps=validate_case(pre,post,c,rows);output=Path(c['output']);archive=folder/(c['label']+'_snapshot.ics');exclusive_copy(output,archive)
                results.append({'output_path':str(output),'sha256':file_sha256(output),'archive_path':str(archive),'archive_sha256':file_sha256(archive),'center_edge_gaps_mm':gaps})
            result.update(passed=True,cases=results,visual_qa='NOT_RUN',production_approved=False,scope='Regular10panel proxies+8real corners+4opaque latch halves, not full Epson. Regenerated A/B; no persistent mating constraints.')
        except Exception as e:result['error']=repr(e);raise
        finally:
            try:
                if addon._invoke(3,2,0)!=OWNER:raise RuntimeError('Owned UUID changed')
                addon._invoke(13,4,0,old['dll']);addon._invoke(12,4,0,old['function']);result['own_addon_configuration_restored']=True
            except Exception as cleanup_error:
                result['passed']=False;result['addon_restore_error']=repr(cleanup_error)
            finally:
                try:
                    result['before']=before;result['phase_guards']=phase_guards
                    result['after']=state();result['guards_unchanged']=result['after']==before
                    if not result['guards_unchanged']:result['passed']=False
                except Exception as guard_error:
                    result['passed']=False;result['guards_unchanged']=False;result['final_state_error']=repr(guard_error)
                finally:
                    write_receipt_once(folder/'acceptance.json',result)
    if result.get('passed') is not True:raise RuntimeError('Final acceptance/cleanup guard failed; inspect acceptance.json')
    print('A/B PASS; own documents closed',flush=True)
    for c in result['cases']:print(c['output_path'],flush=True)
if __name__=='__main__':main()
