"""Install persistent native IronCAD expressions on the isolated case copy."""
from wholecase_common import *
import math

def rotation(m):return [r[:3] for r in m[:3]]
def parent_rotation(row):
    a=rotation(row['matrix_parent']);g=rotation(row['matrix_global'])
    r=[[sum(a[k][i]*g[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    assert max(abs(sum(r[i][k]*r[j][k] for k in range(3))-(i==j)) for i in range(3) for j in range(3))<1e-8
    return r

def expression(value, coeff, depth, baselines):
    result=f'{value:.17g} m'
    for k,c in coeff.items():
        if abs(c)>1e-8:result+=f' + ({c:.12g}) * ('+'Parent\\'*depth+f'Params\\{k} - {baselines[k]:.17g} m)'
    return result

def factor(x,axis):
    lo,hi=[(.5580497847074,1.4720497847074),(.89642617949408,1.49842617949408)][axis]
    mid=(lo+hi)/2
    if abs(x-mid)<(hi-lo)*.12:return -.5
    return -1. if x<mid else 0.

def install():
    cfg,legacy,base,doc,scene=get_doc();u=scene.QueryInterface(ICAPI.IZSceneDocUtility)
    folder=Path(cfg['copy']).parent
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    aux={r['id']:r for r in json.loads((folder/'auxiliary.json').read_text(encoding='utf-8'))}
    for row in manifest['items']:
        if row['id'] in (695,698,13346):
            row['kind']='board';fid={695:696,698:699,13346:13347}[row['id']]
            row['feature']=aux[fid];row['other_features']=[aux[13349]] if row['id']==13346 else []
    baseline=manifest['base'];pm=scene.ParameterMgr;changes=[]
    def get(id):return u.GetElementById(id)
    def pos(row,motion):
        r=parent_rotation(row);s=get(row['id']).QueryInterface(ICAPI.IZSceneElement)
        row['motion_world_relative']=motion
        row['installed_position_expressions']=[]
        for i in range(3):
            coeff={k:sum(v[j]*r[i][j] for j in range(3)) for k,v in motion.items()}
            ex=expression(row['position'][i],coeff,row['depth'],baseline)
            s.PositionTransformComponentExpression[i]=ex
            row['installed_position_expressions'].append(ex)
        changes.append(row['id'])
    for name,val in baseline.items():
        try:p=pm.GetParameterByName(name)
        except Exception:p=None
        if not p:p=pm.CreateParameter(ICAPI.Z_PARAMETER_TYPE_LENGTH,name,val)
        p.Expression=f'{val:.17g} m'
        p.ParamTableVisibility=True
        p.Notes={'RP_Length':'Dlugosc bazowa dolu. Pokrywa zachowuje zastany offset -18.5 mm.',
                 'RP_Depth':'Wspolna szerokosc konstrukcji obu polow.',
                 'RP_BaseHeight':'Wysokosc konstrukcji dolnej; przesuwa cala pokrywe.',
                 'RP_LidHeight':'Wysokosc konstrukcji pokrywy; styk z dolem pozostaje na miejscu.'}[name]
    oldrows={r['id']:r for r in json.loads((folder/'geometry_inventory.json').read_text(encoding='utf-8'))}
    top=dict(oldrows[115]);top['depth']=1
    pos(top,{'RP_BaseHeight':[0,0,1],'RP_LidHeight':[0,0,1]})
    manifest['top']=top
    for id,h in [(174,'RP_LidHeight'),(198,'RP_BaseHeight')]:
        sb=get(id).QueryInterface(ICAPI.IZSizeBox)
        sb.LengthExpression='Parent\\Parent\\Params\\RP_Length'+(' - 18.5 mm' if id==174 else '')
        sb.WidthExpression='Parent\\Parent\\Params\\'+h
        sb.HeightExpression='Parent\\Parent\\Params\\RP_Depth'
    for row in manifest['items']:
        box=row['bbox_world'];c=[(box[i]+box[i+3])/2 for i in range(3)]
        motion={'RP_Length':[factor(c[0],0),0,0],'RP_Depth':[0,factor(c[1],1),0]}
        is_top=row['half']==115
        if is_top:
            # Everything inherits the top assembly translation. Attach to outer face or seam.
            zcoeff=-1. if c[2]<-1.215 else 0.
            motion['RP_LidHeight']=[0,0,zcoeff]
        else:
            zcoeff=0. if c[2]<-1.45 else (1. if c[2]>-1.32 else .5)
            motion['RP_BaseHeight']=[0,0,zcoeff]
        if row['kind'] in ('profile','board'):
            f=row['feature'];g=f['matrix_global'];size_axis=2 if row['kind']=='profile' else 1
            axis=max(range(3),key=lambda i:abs(g[size_axis][i]));sgn=g[size_axis][axis]
            if abs(abs(sgn)-1)>1e-5:raise RuntimeError(f'Nonaxial extrusion {row["id"]}')
            param=['RP_Length','RP_Depth','RP_LidHeight' if is_top else 'RP_BaseHeight'][axis]
            row['length_parameter']=param;row['length_axis_world']=axis;row['length_direction_world']=sgn
            row['feature_depth']=row['depth']+1
            sb=get(f['id']).QueryInterface(ICAPI.IZSizeBox)
            setattr(sb,['LengthExpression','WidthExpression','HeightExpression'][size_axis],expression(f['sizebox'][size_axis],{param:1},row['feature_depth'],baseline))
            row['feature_size_axis']=size_axis
            row['resize_policy']='centered_width' if row['kind']=='board' else 'from_extrusion_start'
            if axis<2:
                motion[param]=[0,0,0];motion[param][axis]=-.5 if row['kind']=='board' else (-1 if sgn>0 else 0)
            else:
                motion[param]=[0,0,(-1 if sgn>0 else 0) if is_top else (0 if sgn>0 else 1)]
            # Keep independent subtractive features at their respective end/edge.
            for extra in row['other_features']:
                if any('SOLVE' in (x or '') for x in extra['position_expressions']):
                    extra['replaced_face_constraint_expressions']=extra['position_expressions']
                p=extra['matrix_global'][3]
                desired=factor(p[axis],axis) if axis<2 else (0 if is_top else 1)
                diff=desired-motion[param][axis]
                vector=[0,0,0];vector[axis]=diff
                extra['depth']=row['depth']+1
                pos(extra,{param:vector})
        pos(row,motion)
        print('Bound',row['id'],row['kind'],flush=True)
    # Manufacturing cutouts follow the same datum as the matching hardware.
    items={r['id']:r for r in manifest['items']}
    cuts=json.loads((folder/'cutouts.json').read_text(encoding='utf-8'))
    manifest['cutouts']=cuts
    for cut in cuts:
        name=cut['name']
        if name=='Hole_HWDrill':
            cut['binding_status']='inactive_outside_wood'
            cut['reason']='Existing orphan cut is above the lower construction; retained and checked for non-intersection.'
            continue
        if name=='H2026_lower hole':candidates=[12413]
        elif name=='W0968z - hole':candidates=[13226,13231,13236,13241]
        elif name=='Średni uchwyt':candidates=[11797,11874,12105,12182]
        elif 'zamek' in name.lower():candidates=[12631,12782,12953,13076] if cut['half']==115 else [12630,12781,12952,13075]
        else:raise RuntimeError('Unmapped cutout '+str(cut['id']))
        center=lambda row:[(row['bbox_world'][i]+row['bbox_world'][i+3])/2 for i in range(3)]
        c=center(cut)
        fixture=min(candidates,key=lambda id:sum((center(items[id])[i]-c[i])**2 for i in range(3)))
        cut['fixture_id']=fixture;cut['binding_status']='bound_to_hardware'
        motion={k:list(v) for k,v in items[fixture]['motion_world_relative'].items()}
        if cut['part'] in (179,200):
            motion.setdefault('RP_Depth',[0,0,0])[1]+=1
        if cut['part']==208:
            motion.setdefault('RP_Length',[0,0,0])[0]+=1
        pos(cut,motion)
        print('Cutout',cut['id'],'->',fixture,flush=True)
    scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update()
    doc.Save()
    manifest['installed_ids']=changes
    (folder/'installed_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Installed',len(changes),'native bindings',flush=True)
if __name__=='__main__':install()
