"""Geometric integration test. Only master parameters are changed in each variant."""
from wholecase_common import *
import hashlib,traceback,math

cfg,legacy,base,doc,scene=get_doc();folder=Path(cfg['copy']).parent
m=json.loads((folder/'installed_manifest.json').read_text(encoding='utf-8'))
u=scene.QueryInterface(ICAPI.IZSceneDocUtility)
report={'variants':[],'passed':False,'scope':'64 components plus both wooden constructions; foam/partitions excluded'}
source_legacy,_,source_doc=connect(cfg['source'])
source_u=source_doc.QueryInterface(ICAPI.IZSceneDoc).QueryInterface(ICAPI.IZSceneDocUtility)
def source_state():
    return {'saved':bool(source_legacy.Saved),'front_bbox':list(source_u.GetElementById(180).QueryInterface(ICAPI.IZFeature).GetBoundingBox()),
            'larg':source_u.GetElementById(174).QueryInterface(ICAPI.IZSceneElement).ParameterMgr.GetParameterByName('Larg').Value}
report['source_before']=source_state()
def snap():
    rows={}
    for r in m['items']:
        e=u.GetElementById(r['id']);b=bbox(e,True);mat=matrix(e)
        rows[str(r['id'])]={'local':b,'world':transformed_bbox(b,mat),'matrix':mat}
    for id in (174,198):
        e=u.GetElementById(id);b=bbox(e,True);mat=matrix(e)
        rows[str(id)]={'local':b,'world':transformed_bbox(b,mat),'matrix':mat}
    for r in m.get('cutouts',[]):
        e=u.GetElementById(r['id']);b=list(e.QueryInterface(ICAPI.IZFeature).GetBoundingBox());mat=matrix(e)
        rows[str(r['id'])]={'local':b,'world':transformed_bbox(b,mat),'matrix':mat}
    for r in m['items']:
        for f in r.get('other_features',[]):
            e=u.GetElementById(f['id']);b=list(e.QueryInterface(ICAPI.IZFeature).GetBoundingBox());mat=matrix(e)
            rows[str(f['id'])]={'local':b,'world':transformed_bbox(b,mat),'matrix':mat}
    return rows
def errors(state,delta,reference):
    errs=[]
    def check(label,a,b):
        if abs(a-b)>2e-6:errs.append({'check':label,'actual':a,'expected':b,'difference_mm':(a-b)*1000})
    for r in m['items']:
        id=str(r['id']);s=state[id];b=reference[id]
        motion=[sum(delta.get(k,0)*v[j] for k,v in r['motion_world_relative'].items()) for j in range(3)]
        if r['half']==115:motion[2]+=delta.get('RP_BaseHeight',0)+delta.get('RP_LidHeight',0)
        for j in range(3):check(id+' origin '+str(j),s['matrix'][3][j],b['matrix'][3][j]+motion[j])
        for i in range(3):
            for j in range(3):check(id+' rotation',s['matrix'][i][j],b['matrix'][i][j])
        if r['kind']=='rigid':
            for j in range(6):check(id+' rigid shape '+str(j),s['local'][j],b['local'][j])
        else:
            axis=r['length_axis_world'];d=delta.get(r['length_parameter'],0);sgn=r['length_direction_world']
            for j in range(3):
                lo=(-.5 if r['kind']=='board' else min(0,sgn))*d
                hi=(.5 if r['kind']=='board' else max(0,sgn))*d
                check(id+' min '+str(j),s['world'][j],b['world'][j]+motion[j]+(lo if j==axis else 0))
                check(id+' max '+str(j),s['world'][j+3],b['world'][j+3]+motion[j]+(hi if j==axis else 0))
    for id,height in [('174','RP_LidHeight'),('198','RP_BaseHeight')]:
        for axis,key in enumerate(['RP_Length',height,'RP_Depth']):
            b=reference[id]['local'];s=state[id]['local']
            check(id+' construction extent '+str(axis),s[axis+3]-s[axis],b[axis+3]-b[axis]+delta.get(key,0))
    # Paired wheel and stacking cup must retain their XY offsets in every variant.
    for wheel,cup in [(594,13236),(678,13241),(9098,13231),(9115,13226)]:
        for axis in (0,1):
            center=lambda state,id:(state[str(id)]['world'][axis]+state[str(id)]['world'][axis+3])/2
            check(f'wheel/cup {wheel}/{cup} axis {axis}',center(state,wheel)-center(state,cup),center(reference,wheel)-center(reference,cup))
    # Independent physical checks, not derived from installer motion coefficients.
    for half,corners in [(174,[9090,9092,9094,9096]),(198,[9078,9083,9085,9087])]:
        for corner in corners:
            for axis in range(3):
                center=lambda data:(data[str(corner)]['world'][axis]+data[str(corner)]['world'][axis+3])/2
                refbox=reference[str(half)]['world']
                side=min((axis,axis+3),key=lambda j:abs(center(reference)-refbox[j]))
                check(f'corner {corner} to wooden face {axis}',center(state)-state[str(half)]['world'][side],center(reference)-refbox[side])
    for axis in (0,1):
        for end in (axis,axis+3):
            check(f'lid/base footprint gap {end}',state['174']['world'][end]-state['198']['world'][end],reference['174']['world'][end]-reference['198']['world'][end])
    check('lid/base vertical seam',state['174']['world'][2]-state['198']['world'][5],reference['174']['world'][2]-reference['198']['world'][5])
    for upper,lower in [(12631,12630),(12782,12781),(12953,12952),(13076,13075),(13209,13206),(13212,13215)]:
        for axis in range(3):
            center=lambda data,id:(data[str(id)]['world'][axis]+data[str(id)]['world'][axis+3])/2
            check(f'mating hardware {upper}/{lower} axis {axis}',center(state,upper)-center(state,lower),center(reference,upper)-center(reference,lower))
    for cut in m.get('cutouts',[]):
        id=str(cut['id']);current=state[id];ref=reference[id]
        for axis in range(6):check(id+' cut localshape '+str(axis),current['local'][axis],ref['local'][axis])
        if cut['binding_status']=='inactive_outside_wood':
            b=current['world'];wood=state[str(cut['construction'])]['world']
            if not any(b[j+3]<wood[j] or b[j]>wood[j+3] for j in range(3)):
                errs.append({'check':id+' orphan cut now intersects construction'})
        elif cut['binding_status']=='bound_to_hardware':
            fid=str(cut['fixture_id'])
            for axis in range(3):
                center=lambda data,id:(data[id]['world'][axis]+data[id]['world'][axis+3])/2
                check(id+' hole-to-hardware '+axis.__str__(),center(state,id)-center(state,fid),center(reference,id)-center(reference,fid))
            for i in range(3):
                for j in range(3):check(id+' cut rotation',current['matrix'][i][j],ref['matrix'][i][j])
        else:errs.append({'check':id+' uncovered cutout'})
    return errs
def setvalues(delta):
    for k,v in m['base'].items():scene.ParameterMgr.GetParameterByName(k).Expression=f'{(v+delta.get(k,0))*1000:.12g} mm'
    scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update()
def save_report():
    (folder/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
try:
    setvalues({});initial=snap();report['baseline']=initial
    expected={str(r['id']):{'local':r['bbox_local'],'world':r['bbox_world'],'matrix':r['matrix_global']} for r in m['items']}
    control=json.loads((folder/'baseline_regeneration.json').read_text(encoding='utf-8'))
    report['baseline_definition']='Regenerated baseline. Two existing latch features change identically in an independent unmodified control copy.'
    report['preexisting_regeneration_effects']={id:{'before':control['before'][id]['bbox_local'],'after':control['after'][id]['bbox_local']} for id in ('12631','12782')}
    for id in ('12631','12782'):
        r=control['after'][id];expected[id]={'local':r['bbox_local'],'world':r['bbox_world'],'matrix':r['matrix_global']}
    inventory={str(r['id']):r for r in json.loads((folder/'geometry_inventory.json').read_text(encoding='utf-8'))}
    for id in ('174','198'):
        r=inventory[id];expected[id]={'local':r['bbox_local'],'world':transformed_bbox(r['bbox_local'],r['matrix_global']),'matrix':r['matrix_global']}
    for r in m.get('cutouts',[]):expected[str(r['id'])]={'local':r['bbox_local'],'world':r['bbox_world'],'matrix':r['matrix_global']}
    report['baseline_errors']=errors(initial,{},expected)
    print('Baseline errors',len(report['baseline_errors']),flush=True);save_report()
    variants=[('length',{'RP_Length':.06}),('depth',{'RP_Depth':.04}),('base_height',{'RP_BaseHeight':.03}),('lid_height',{'RP_LidHeight':.02}),
              ('combined',{'RP_Length':.06,'RP_Depth':.04,'RP_BaseHeight':.03,'RP_LidHeight':.02}),
              ('smaller',{'RP_Length':-.02,'RP_Depth':-.015,'RP_BaseHeight':-.01,'RP_LidHeight':-.005}),('return',{})]
    for name,delta in variants:
        print('Testing',name,flush=True);setvalues(delta);s=snap();errs=errors(s,delta,initial)
        report['variants'].append({'name':name,'delta':delta,'state':s,'errors':errs})
        print(name,'errors',len(errs),json.dumps(errs[:4]),flush=True);save_report()
    doc.Save();doc.Close();doc=base.OpenFile(cfg['copy'],False);scene=doc.QueryInterface(ICAPI.IZSceneDoc);u=scene.QueryInterface(ICAPI.IZSceneDocUtility)
    report['reopen_errors']=errors(snap(),{},initial)
    delta={'RP_Length':.025,'RP_Depth':.015};setvalues(delta)
    report['reopen_edit_errors']=errors(snap(),delta,initial)
    report['source_file_unchanged']=hashlib.sha256(Path(cfg['source']).read_bytes()).hexdigest()==cfg['source_hash']
    report['source_after']=source_state();report['source_session_unchanged']=report['source_before']==report['source_after']
    report['numeric_checks_passed']=not(report['baseline_errors'] or any(v['errors'] for v in report['variants']) or report['reopen_errors'] or report['reopen_edit_errors']) and report['source_file_unchanged'] and report['source_session_unchanged']
    report['ui_gate_pending']=True
except Exception:
    report['exception']=traceback.format_exc();print(ascii(report['exception']),flush=True)
finally:
    try:setvalues({});doc.Save()
    except Exception:report['restore_error']=traceback.format_exc();report['passed']=False
    save_report();print('Numeric checks:',report.get('numeric_checks_passed',False),'UI gate pending',report.get('ui_gate_pending',True),flush=True)
