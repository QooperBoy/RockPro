"""Offline migration tests with explicit synthetic geometry, never CAD evidence."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad import accessory_parameters as a, studio_placement
from rockpro_cad.mcp.test_studio_native_t1 import manifest, saved
from rockpro_cad.studio_native_t1 import compile_t1


def fixture():
    with patch.dict(studio_placement.FOOTPRINTS,{'270836':[127.,174.5]}):
        record=saved()
        record['draft']['placements'][-1]['edge_inset_mm']=150
        spec=compile_t1(record,manifest())
    rows=[]
    for i,s in enumerate(spec['panels']+spec['parts']):
        position=s['position_mm'];world=[r+[0] for r in s['rotation']]+[position+[1]]
        root=dict(id=10+i*2,name=s['label']+' | '+s['id'],path='root/2/'+str(10+i*2),world_mm=world)
        rows.append(root)
        sku=s.get('part_id');low=[0,0,0];high=s.get('size_mm',[1,1,1])
        if sku=='H7159':low=[-1,-80.5,-53.5];high=[1,80.5,53.5]
        if sku=='270836':low=[-68.3170105,-20.71,-108.5];high=[58.6829895,-1.7,66]
        if sku=='source-caster-epson':
            low=[-52.5 if s['rotation'][0][0]<0 else -86,-40,-132.1]
            high=[86 if s['rotation'][0][0]<0 else 52.5,40,0]
        if sku=='W0968Z':low=[-68,13.2108815,-61.79];high=[68,103.2108815,-28.2]
        matrix=[[1,0,0,0],[0,1,0,0],[0,0,1,0],position+[1]]
        rows.append(dict(id=11+i*2,name='Synthetic leaf',path=root['path']+'/'+str(11+i*2),world_mm=matrix,bounds_local_m=[v/1000 for v in low+high]))
    return spec,dict(rows=rows,errors=[],source='synthetic.ics',source_sha256='a'*64)


class AccessoryParameterTests(unittest.TestCase):
    def setUp(self):
        self.request,self.inventory=fixture()
        self.spec=a.migrate(self.request,self.inventory)

    def test_baseline_preserved_and_no_input_mutation(self):
        req,inv=copy.deepcopy((self.request,self.inventory))
        result=a.migrate(self.request,self.inventory)
        self.assertEqual((req,inv),(self.request,self.inventory))
        for collection in ('panels','parts','cuts'):
            for old,new in zip(req[collection],result[collection]):
                for x,y in zip(old['position_mm'],new['position_mm']):self.assertAlmostEqual(x,y,places=7)
                self.assertEqual(old['rotation'],new['rotation'])
        self.assertEqual({p['physical_group'] for p in result['panels']+result['parts']},{'lid','foundation'})
        self.assertEqual([g['label'] for g in result['physical_groups']],['Wieko 1','Podstawa'])
        for p in result['panels']:
            if p['id'].startswith('panel/body/'):
                self.assertEqual(p['physical_group'],'foundation')

    def test_regroup_existing_copy_preserves_parameters_and_cuts(self):
        old=copy.deepcopy(self.spec)
        old['physical_groups']=[dict(id='body',label='Korpus 1'),dict(id='lid',label='Korpus 2'),dict(id='foundation',label='Podstawa')]
        for row in old['panels']+old['parts']:
            if row.get('section_id')=='body':row['physical_group']='body'
        receipt=dict(passed=True,sources_unchanged=True,parameters=old['parameters'],output_path='prior-copy.ics',output_sha256='b'*64,
                     final_file_reopened=dict(passed=True,occurrences=[dict(id=r['id'],native_id=1000+i) for i,r in enumerate(old['panels']+old['parts'])]))
        changed=a.regroup_saved_copy(old,receipt)
        self.assertEqual(changed['parameters'],old['parameters'])
        self.assertEqual(changed['cuts'],old['cuts'])
        self.assertEqual([g['label'] for g in changed['physical_groups']],['Wieko 1','Podstawa'])
        self.assertEqual(changed['sources'][0]['path'],'prior-copy.ics')
        self.assertTrue(all(r['physical_group'] in ('lid','foundation') for r in changed['panels']+changed['parts']))
        receipt['passed']=False
        with self.assertRaises(ValueError):a.regroup_saved_copy(old,receipt)

    def test_hinge_pitch_moves_both_halves_and_cut(self):
        old=[p for p in self.spec['parts'] if p.get('part_id')=='270836']
        result=a.evaluate(self.spec,dict(RP_Zawiasy_TrybOdBrzegow=0,RP_Zawiasy_RozstawZadany=280))
        new=[p for p in result['parts'] if p.get('part_id')=='270836']
        xs=sorted({p['position_mm'][0] for p in new})
        self.assertAlmostEqual(xs[1]-xs[0],280)
        for before,after in zip(old,new):
            dx=after['position_mm'][0]-before['position_mm'][0]
            for c in [c for c in result['cuts'] if c['owner_id']==before['id']]:
                orig=next(x for x in self.spec['cuts'] if x['id']==c['id'])
                target=next(x for x in result['panels']+result['parts'] if x['id']==c['target_id'])
                worlddelta=sum((c['position_mm'][k]-orig['position_mm'][k])*target['rotation'][k][0] for k in range(3))
                self.assertAlmostEqual(worlddelta,dx)

    def test_handles_share_height_and_spacing_across_walls(self):
        result=a.evaluate(self.spec,dict(RP_Uchwyty_TrybOdBrzegow=0,RP_Uchwyty_RozstawZadany=240,RP_Uchwyty_WysokoscOdDolu=400))
        for face in ('left','right'):
            handles=sorted([p for p in result['parts'] if p.get('part_id')=='H7159' and p['face']==face],key=lambda x:x['position_mm'][1])
            self.assertAlmostEqual(handles[1]['position_mm'][1]-handles[0]['position_mm'][1],240)
            self.assertTrue(all(abs(p['position_mm'][2]-409.8)<1e-7 for p in handles))

    def test_axes_independent_and_sockets_follow_caster_contact(self):
        result=a.evaluate(self.spec,dict(RP_KolaX_MarginesLewy=110))
        original={p['id']:p for p in self.spec['parts']}
        wheels={p['id']:p for p in result['parts'] if p.get('part_id')=='source-caster-epson'}
        for wheel in wheels.values():self.assertEqual(wheel['position_mm'][1],original[wheel['id']]['position_mm'][1])
        for socket in [p for p in result['parts'] if p.get('part_id')=='W0968Z']:
            wheel=wheels[socket['paired_wheel_id']]
            seat=wheel['position_mm'][0]-36*wheel['rotation'][0][0]
            self.assertAlmostEqual(socket['position_mm'][0],seat)
        pad=next(p for p in result['panels'] if p['id']=='structure/pad/0')
        self.assertAlmostEqual(pad['position_mm'][0],wheels['structure/wheel-00']['position_mm'][0]-60)

    def test_collision_and_illegal_modes_rejected(self):
        for changes in (dict(RP_KolaX_TrybOdBrzegow=0,RP_KolaX_RozstawZadany=80),dict(RP_KolaY_MarginesLewy=0),dict(RP_Uchwyty_TrybOdBrzegow=.5),dict(RP_GruboscSklejki=12)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):a.evaluate(self.spec,changes)

    def test_derived_cannot_be_independently_overridden(self):
        with self.assertRaises(ValueError):a.evaluate(self.spec,dict(RP_KolaX_RozstawRzeczywisty=300))

    def test_source_pose_mismatch_rejected(self):
        self.inventory['rows'][0]['world_mm'][3][0]+=1
        with self.assertRaises(ValueError):a.migrate(self.request,self.inventory)

    def test_checks_cover_modes_axes_and_safe_arithmetic(self):
        self.assertEqual(len(a.with_checks(self.spec)['check_cases']),6)
        for expression in ('__import__("os")','x.real','[1][0]'):
            with self.assertRaises((ValueError,KeyError)):a.number(expression,{})


if __name__=='__main__':unittest.main()
