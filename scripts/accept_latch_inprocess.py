"""Fixed in-process 17251S A/B POC using one explicitly owned legacy AddOn.
No application launch, UI, generic execution endpoint, or BRep examination.
"""
import argparse,ctypes,json,os,shutil,subprocess,sys,math
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

def validate_case(before,after,case,source_rows,handle_reference=None):
    # Basic placement only. No internal feature/body access.
    _persistence(before,after)
    source={r['id']:r for r in source_rows}
    for observation in (before,after):
        if observation['top_level_roots']!=16+len(case.get('handles',[])):raise RuntimeError('Whole root count differs')
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
        handles=observation.get('handles',[])
        if len(handles)!=len(case.get('handles',[])):raise RuntimeError('H7159 pair count differs')
        for h in case.get('handles',[]):
            r=next(x for x in handles if x['occurrence_id']==h['id'])
            _assert_row(r,dict(matrix_world_mm=h['matrix_world_mm'],local_bounds_mm=handle_reference['local_bounds_mm']))
            if r['name']!='H7159' or r['kind']!='assembly' or r['children_count']!=13:raise RuntimeError('Opaque H7159 root changed')
        if handles:
            if len({r['native_id'] for r in handles}|{r['native_id'] for r in physical})!=24:raise RuntimeError('H7159 duplicate native ID')
            centers=[]
            for r in handles:
                b=r['local_bounds_mm'];m=r['matrix_world_mm'];v=[(b[i]+b[i+3])/2 for i in range(3)];centers.append([sum(v[k]*m[k][j] for k in range(3))+m[3][j] for j in range(3)])
            if abs(centers[0][0]+centers[1][0]-2*case['case_min'][0]-case['size'][0])>.003 or max(abs(centers[0][i]-centers[1][i]) for i in (1,2))>.003:raise RuntimeError('Whole H7159 center symmetry differs')
    for a,b in zip(before.get('handles',[]),after.get('handles',[])):
        _assert_row(b,a,identity=True)
        if a['occurrence_id']!=b['occurrence_id']:raise RuntimeError('H7159 occurrence ID changed')
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
    p.add_argument('--preserve-dirty-context',action='store_true',help='Preserve an already dirty user context exactly; never save or modify it')
    p.add_argument('--single-size',nargs=3,type=float,metavar=('W','D','H'))
    p.add_argument('--handle-proof',type=Path,help='Known successful H7159 POC04 receipt; optional whole pair')
    p.add_argument('--compile-only',action='store_true');a=p.parse_args();folder=a.output.resolve()
    if a.single_size and any(not math.isfinite(v) or v<550 or v>5000 for v in a.single_size):p.error('Single dimensions require550..5000mm')
    if folder.exists() or not folder.is_relative_to(ROOT/'artifacts'):p.error('New checkout artifacts directory required')
    if a.compile_only:folder.mkdir();build(folder,managed_name());compile_managed(folder);print('COMPILE PASS');return
    import comtypes.client
    from comtypes.automation import IDispatch
    from comtypes import IUnknown
    app=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True)
    def page_identity(page):
        raw=page._comobj if hasattr(page,'_comobj') else page
        return raw.QueryInterface(IUnknown)
    active_page_anchor=page_identity(app.ActivePage)  # Hold canonical COM ref until cleanup.
    user=ctypes.WinDLL('user32');user.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    def state():
        pid=ctypes.c_ulong();hwnd=int(app.HWnd);user.GetWindowThreadProcessId(ctypes.c_void_p(hwnd),ctypes.byref(pid))
        page=app.ActivePage
        return {'pid':pid.value,'hwnd':hwnd,'foreground':foreground(),'active_path':str(page.FullName),'saved':bool(page.Saved),'active_page_iunknown':int(ctypes.cast(page_identity(page),ctypes.c_void_p).value),'source_sha256':file_sha256(a.source)}
    before=state()
    if before['pid']!=a.expected_pid or (not before['saved'] and not a.preserve_dirty_context) or before['source_sha256']!=SOURCE_SHA or (before['active_path'].casefold()!=str(a.context.resolve()).casefold() and not (a.preserve_dirty_context and before['active_path']=='')):raise RuntimeError('Exact saved context/source/host guard failed')
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
        common={'expected_pid':a.expected_pid,'original_source':str(a.source.resolve()),'context':before['active_path'],'allow_dirty_context':bool(a.preserve_dirty_context)}
        source_request=dict(common,source_copy=str(folder/'source_disk_copy.ics'))
        handle_proof=None
        if a.handle_proof:
            handle_proof=json.loads(a.handle_proof.read_text(encoding='utf-8'))
            from rockpro_cad.core_case.hardware_poc import validate_datum
            if handle_proof.get('passed') is not True or handle_proof['asset_sha256']!='56271ce17f5e792c2d82b320a7947f81c5e15dd9b3d9362c2af073992858d73f':raise RuntimeError('Known successful H7159 asset proof required')
            validate_datum(handle_proof['plan']['datum'])
            if file_sha256(handle_proof['asset_path'])!=handle_proof['asset_sha256']:raise RuntimeError('H7159 asset drift')
            handle_copy=folder/'H7159_getter_asset_copy.ics';exclusive_copy(handle_proof['asset_path'],handle_copy)
            source_request['handle_asset']={'path':str(handle_copy),'sha256':handle_proof['asset_sha256']}
        write_receipt_once(folder/'source_request.json',source_request)
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
        result={'passed':False,'before':before,'user_context_already_dirty':not before['saved'],'dirty_context_preservation_explicit':bool(a.preserve_dirty_context),'context_memory_disk_equivalence':'not claimed; context never saved/modified/closed'}
        try:
            print('SOURCE WHOLE ROOT READ/EXPORT',flush=True);invoke('source');check_cancel()
            fresh=json.loads((folder/'source_result.json').read_text(encoding='utf-8'));rows=fresh['rows']
            receipt=json.loads(a.corner_receipt.read_text(encoding='utf-8'));assets=json.loads(a.corner_assets.read_text(encoding='utf-8'))
            if not receipt['passed'] or receipt['source_sha256_before']!=SOURCE_SHA or assets['source_sha256']!=SOURCE_SHA:raise RuntimeError('Pinned corner provenance differs')
            frame=receipt['plan']['binding']['case_frame']['matrix_world_mm'];minimum=frame[3][:3];cases=[]
            requested=[('single_'+'x'.join(format(v,'g') for v in a.single_size),a.single_size)] if a.single_size else [('A_914x602x352',[914,602,352]),('B_1100x720x410',[1100,720,410])]
            for label,size in requested:
                latch=plan_latch_pairs([{k:r[k] for k in ('id','role','side','matrix_world_mm','local_bounds_mm')} for r in rows],minimum,[914,602,352],size);corner=plan_corner_resize(receipt['plan']['binding'],size)
                ca=[]
                for root in corner['assemblies']:
                    asset=next(r for r in assets['roots'] if r['source_id']==root['id']);ca.append(dict(asset,matrix_world_mm=root['matrix_world_mm']))
                la=[dict(r,asset_path=next(s['asset_path'] for s in rows if s['id']==r['id']),asset_sha256=next(s['asset_sha256'] for s in rows if s['id']==r['id'])) for r in latch['occurrences']]
                cases.append({'label':label,'size':size,'case_min':minimum,'output':str(folder/('POC_zatrzaski_'+label+'.ics')),'panels':panel_occurrences(size,frame),'corners':corner['occurrences'],'corner_assets':ca,'latches':la,'handles':[]})
                if handle_proof:
                    origin=handle_proof['plan']['datum']['origin_mm'];base=size[2]-104.13
                    for side,anchor_x in [('left',minimum[0]+180.5),('right',minimum[0]+size[0]-180.5)]:
                        matrix=[[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[anchor_x-origin[0],minimum[1]+origin[1],minimum[2]+base/2+origin[2],1]]
                        cases[-1]['handles'].append({'id':'H7159-'+side,'asset_path':source_request['handle_asset']['path'],'asset_sha256':handle_proof['asset_sha256'],'matrix_world_mm':matrix})
            check_cancel()
            write_receipt_once(folder/'execute_request.json',dict(common,cases=cases))
            print('EXECUTE '+str(len(cases))+' CASE(S)',flush=True);invoke('execute');results=[]
            for c in cases:
                pre=json.loads((folder/(c['label']+'_before.json')).read_text(encoding='utf-8'));post=json.loads((folder/(c['label']+'_after.json')).read_text(encoding='utf-8'))
                gaps=validate_case(pre,post,c,rows,fresh.get('handle_reference'));output=Path(c['output']);archive=folder/(c['label']+'_snapshot.ics');exclusive_copy(output,archive)
                results.append({'output_path':str(output),'sha256':file_sha256(output),'archive_path':str(archive),'archive_sha256':file_sha256(archive),'center_edge_gaps_mm':gaps,'size_mm':c['size'],'real_handle_assemblies':len(c['handles'])})
            result.update(passed=True,cases=results,visual_qa='NOT_RUN',production_approved=False,scope='Regular10panel proxies+8real corners+4opaque latch halves'+('+2whole H7159 assemblies' if handle_proof else '')+'; not full Epson. Regenerated dimensions; no persistent mating constraints, no cuts or collision approval.')
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
    print('CASE(S) PASS; own documents closed',flush=True)
    for c in result['cases']:print(c['output_path'],flush=True)
if __name__=='__main__':main()
