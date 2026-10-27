"""Offline compiler checks with an explicit synthetic source manifest (not CAD proof)."""
import copy
import unittest
from unittest.mock import patch
from rockpro_cad import studio_placement
from rockpro_cad import studio_native_t1 as n
from rockpro_cad.core_case.profile_rules import rules, value
from rockpro_cad.core_case.t1_mounting import SOCKET_SEAT
from rockpro_cad.mcp.test_studio_structure import complete


def manifest():
    # Synthetic source identities; no private ICS files or inventory are required.
    assets=[]
    poses={
        'H7159':([[1,0,0],[0,0,1],[0,-1,0]],[0,0,0]),
        '17251S':(n.I,[0,-15.646126539485,-11.9]),
        '270836':([[-1,0,0],[0,0,1],[0,1,0]],[-4.8170105088013,1.01,10.70980476265]),
        'W0968Z':(n.I,[-x for x in SOCKET_SEAT]),
        'source-caster-epson':([[-1,0,0],[0,0,-1],[0,-1,0]],[0,0,0]),
    }
    for sku in sorted(n.KNOWN):
        for half in (['base','lid'] if sku in ('17251S','270836') else ['complete']):
            a=dict(sku=sku,half=half,source='baseline',source_id=len(assets)+100)
            if sku in poses:a['native_to_mount_uvn']=dict(rotation=copy.deepcopy(poses[sku][0]),translation_mm=list(poses[sku][1]))
            assets.append(a)
    bindings=[];ids={}
    for index,r in enumerate(rules()):
        row=copy.deepcopy(r);sku=r['sku'];nid=500+index
        if sku=='EG-0500_1':nid=1146+6*['front','rear','left','right'].index(r['id'].split('/')[-1])
        if sku=='EG-0500_2':nid=1170+6*['front','rear','left','right'].index(r['id'].split('/')[-1])
        row['node_id']=nid
        section={'EG-0113':[35,35],'EG-0500_1':[26.7923697962,12.3011765193],'EG-0500_2':[21.1157008093,12.3], 'B1930':[40,36.5],'B1121':[31,40]}[sku]
        center=[f'{section[0]/2} mm',f'{section[1]/2} mm','('+r['cut_length']+')/2' if r['cut_length'] else '15.5 mm']
        row['position']=[r['center'][j]+''.join(f' - ({r["rotation"][k][j]}) * ({center[k]})' for k in range(3) if r['rotation'][k][j]) for j in range(3)]
        bindings.append(row);ids[nid]=row
    cuts=[];rel=[]
    def add(key,owner,template=10353,target=990,wp=None,size=None,rotation=None,delta=None):
        c=dict(key=key,mount_key=owner,template_id=template,target_id=target,world_rotation=rotation or copy.deepcopy(n.I),world_position=wp or ['0 mm']*3,through_target=size is None)
        if size:c['size']=size
        cuts.append(c);rel.append(dict(key=key,native_owner_rotation=rotation or copy.deepcopy(n.I),native_owner_translation_mm=delta or [0,0,0]))
    add('handles/left/1/opening','handles/left/1',delta=[-65,1,-39.067874119633],rotation=[[1,0,0],[0,0,1],[0,-1,0]])
    add('handles/left/1/flange_relief','handles/left/1',delta=[-68,0,-42.067874119633],rotation=[[1,0,0],[0,0,1],[0,-1,0]],size=['136 mm','84 mm','1.25 mm'])
    for family in ('latches','hinges'):
        for half in ('base','lid'):
            owner=family+'/1/'+half
            add(owner+'/panel',owner,12455,rotation=[[0,-1,0],[1,0,0],[0,0,-1]])
            add(owner+'/profile',owner,12932)
    add('stacking_sockets/left/front/opening','stacking_sockets/left/front',13218,rotation=[[0,1,0],[1,0,0],[0,0,-1]],delta=[-51.5,30.71088152752,-32.28911847248])
    for half,targets,start in [('base',[990,996,1002,1008],1146),('lid',[1014,1020,1026,1032],1170)]:
        for index,(wall,target) in enumerate(zip(['front','rear','left','right'],targets)):
            owner='profile_seating/'+str(start+index*6)
            for face in (0,1):add('edge_rebate/'+half+'/'+wall+'/'+str(face),owner,12932,target,['0 mm','0 mm','RP_BaseHeight'],['20 mm','RP_Length','.2 mm'])
            if half=='lid':add('lid_seating/'+wall,owner,12932,target,['0 mm','0 mm','RP_BaseHeight + RP_JointGap'],['.1 mm','RP_Length','RP_Thickness'])
    return dict(sources={k:dict(path=k+'.ics',sha256='a'*64) for k in ('baseline','templates')},assets=assets,profile_all_bindings=bindings,corrected_plan=dict(mounts=[],cuts=cuts),cut_transforms_relative_owner=rel,template_features=[dict(feature=dict(id=i)) for i in (10353,12455,12932,13218)])


def saved(d=None):return dict(id='unit-fixture',revision=1,draft=d or complete())


class NativeT1Tests(unittest.TestCase):
    def setUp(self):
        self.envelopes=patch.dict(studio_placement.FOOTPRINTS,{"270836":[127.,174.5]})
        self.envelopes.start();self.addCleanup(self.envelopes.stop)

    def test_complete_and_owned_machining(self):
        record=saved();m=manifest();before=copy.deepcopy((record,m));spec=n.compile_t1(record,m)
        self.assertEqual((record,m),before)
        self.assertEqual([len(spec[k]) for k in ['panels','parts','cuts']],[12,60,48])
        all_ids={x['id'] for k in ('panels','parts') for x in spec[k]}
        self.assertTrue(all(c['owner_id'] in all_ids and c['target_id'] in all_ids for c in spec['cuts']))
        self.assertEqual(len(spec['structure_mapping']),8)
        self.assertEqual(spec['formula_check'],'PASS');self.assertEqual(spec['native_validation'],'NOT RUN')
        for part in spec['parts']:n.proper(part['rotation'])
        for cut in spec['cuts']:n.proper(cut['rotation'],allow_reflection=True)
        self.assertTrue(any(c['rotation'][2][2]==-1 for c in spec['cuts']))
        self.assertFalse(any('profile_length_expression' in p for p in spec['parts'] if p['part_id'] in n.FAMILIES))

    def test_variable_handle_count_and_actual_opposing_pose(self):
        d=complete();d['internal_mm']=[600,1600,800];d['placements'][0].update(count_per_wall=5,handles_per_wall=5,spread=.75)
        spec=n.compile_t1(saved(d),manifest());handles=[p for p in spec['parts'] if p['part_id']=='H7159']
        self.assertEqual(len(handles),10)
        self.assertEqual(len([c for c in spec['cuts'] if c['stage_id']=='handles']),20)
        for face in ['left','right']:self.assertEqual(len([p for p in handles if p['face']==face]),5)
        ys=lambda face:sorted(p['position_mm'][1] for p in handles if p['face']==face)
        for a,b in zip(ys('left'),ys('right')):self.assertAlmostEqual(a,b,places=7)
        # The same source-local cut offset follows the native owner after rotation.
        for owner in handles:
            c=next(c for c in spec['cuts'] if c['owner_id']==owner['id'] and c['id'].endswith('/opening'))
            target=next(p for p in spec['panels'] if p['id']==c['target_id'])
            world=n.plus(n.vec(c['position_mm'],target['rotation']),target['position_mm'])
            expected=n.plus(n.vec([-65,1,-39.067874119633],owner['rotation']),owner['position_mm'])
            for a,b in zip(world,expected):self.assertAlmostEqual(a,b,places=6)

    def test_one_and_sixteen_handles_and_rotated_owner(self):
        for count,depth in [(1,500),(16,8000)]:
            d=complete();d['internal_mm'][1]=depth
            d['placements'][0].update(count_per_wall=count,handles_per_wall=count,spread=.75,rotation_deg=90)
            spec=n.compile_t1(saved(d),manifest())
            self.assertEqual(len([p for p in spec['parts'] if p['part_id']=='H7159']),2*count)
            self.assertEqual(len([c for c in spec['cuts'] if c['stage_id']=='handles']),4*count)
        d=complete();d['placements'][1]['count']=3
        spec=n.compile_t1(saved(d),manifest())
        self.assertEqual(len([p for p in spec['parts'] if p['part_id']=='17251S']),6)
        self.assertEqual(len([c for c in spec['cuts'] if c['owner_id'].startswith('placement/closures:')]),12)

    def test_transport_seat_contact_and_changed_expression(self):
        spec=n.compile_t1(saved(),manifest())
        for socket in [p for p in spec['parts'] if p['part_id']=='W0968Z']:
            wheel=next(p for p in spec['parts'] if p['part_id']=='source-caster-epson' and p['stacking_pair']==socket['stacking_pair'])
            contact=n.plus(n.vec([-36,-132.1,0],wheel['rotation']),wheel['position_mm'])
            seat=n.plus(n.vec(SOCKET_SEAT,socket['rotation']),socket['position_mm'])
            self.assertEqual(seat[:2],contact[:2])
            self.assertGreater(abs(seat[0]-wheel['position_mm'][0]),35.9)
        for kind in ('panels','parts','cuts'):
            for row,changed in zip(spec[kind],spec['changed_expected'][kind]):
                for expression,expected in zip(row['position_expressions'],changed['position_mm']):self.assertAlmostEqual(value(expression,spec['changed_parameters']),expected,places=5)
        self.assertEqual(spec['fixed_parameters'],{'RP_GruboscSklejki':9.8})

    def test_block_unknown_collision_missing_cut_and_unsaved(self):
        with self.assertRaisesRegex(ValueError,'zapisany'):n.compile_t1(complete(),manifest())
        bad=complete();bad['hardware'].append(dict(part_id='27095',revision=1))
        with self.assertRaisesRegex(ValueError,'27095'):n.compile_t1(saved(bad),manifest())
        bad=complete();bad['thickness_mm']=10
        with self.assertRaisesRegex(ValueError,'9,8'):n.compile_t1(saved(bad),manifest())
        bad=complete();bad['placements'][0].update(count_per_wall=16,handles_per_wall=16)
        with self.assertRaises(ValueError):n.compile_t1(saved(bad),manifest())
        m=manifest();m['corrected_plan']['cuts']=[c for c in m['corrected_plan']['cuts'] if c['key']!='handles/left/1/opening']
        with self.assertRaisesRegex(ValueError,'Niekompletne'):n.compile_t1(saved(),m)
        m=manifest();m['assets'][0]['source']='unbound'
        with self.assertRaisesRegex(ValueError,'Nieznane'):n.compile_t1(saved(),m)

    def test_legal_lid_ceiling_uses_signed_probe_without_override(self):
        for height,lid in [(800.,119.95),(800.,120.),(110/.15,110.)]:
            d=complete();d['internal_mm'][2]=height;d['covers'][0]['depth_mm']=lid
            record=saved(d);before=copy.deepcopy(record)
            spec=n.compile_t1(record,manifest())
            self.assertEqual(record,before)
            self.assertFalse(record['draft']['covers'][0]['height_override'])
            self.assertEqual(spec['parameters']['RP_WysokoscPokrywy'],lid)
            self.assertEqual(spec['formula_check'],'PASS')
            # Both the original legal point and the separate check case must
            # reconstruct; signed/reference probes cannot change the result.
            for kind in ('panels','parts','cuts'):
                for original,changed in zip(spec[kind],spec['changed_expected'][kind]):
                    for field,expr in [('position_mm','position_expressions'),('size_mm','size_expressions')]:
                        if field not in original:continue
                        for formula,a,b in zip(original[expr],original[field],changed[field]):
                            self.assertAlmostEqual(value(formula,spec['parameters']),a,places=5)
                            self.assertAlmostEqual(value(formula,spec['changed_parameters']),b,places=5)
        d=complete();d['covers'][0]['depth_mm']=120.01
        with self.assertRaisesRegex(ValueError,'15%'):n.compile_t1(saved(d),manifest())

    def test_narrow_stack_is_blocked_but_exact_clearance_and_no_stack_work(self):
        d=complete();d['internal_mm'][0]=380.
        with self.assertRaisesRegex(ValueError,'Gniazda kół'):n.compile_t1(saved(d),manifest())
        d['construction']['stacking']=False
        d['hardware']=[r for r in d['hardware'] if r['part_id']!='W0968Z']
        self.assertFalse(any(p['part_id']=='W0968Z' for p in n.compile_t1(saved(d),manifest())['parts']))
        d=complete();d['internal_mm'][0]=400.4
        spec=n.compile_t1(saved(d),manifest())
        self.assertEqual(len([p for p in spec['parts'] if p['part_id']=='W0968Z']),4)

if __name__=='__main__':unittest.main()
