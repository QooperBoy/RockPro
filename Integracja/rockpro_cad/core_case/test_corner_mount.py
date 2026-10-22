"""Synthetic source transforms, raw panel planes and independent corner TDD."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case import corner_mount as api

I=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
FRAME=[[0,1,0,0],[-1,0,0,0],[0,0,1,0],[100,200,300,1]]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def point(local,matrix):
    return [matrix[3][j]+sum(local[k]*matrix[k][j] for k in range(3)) for j in range(3)]


def planes(size,frame=FRAME):
    result=[]
    for axis,side in itertools.product(range(3),range(2)):
        other=[i for i in range(3) if i!=axis];vertices=[]
        for a,b in itertools.product(range(2),repeat=2):
            p=[0.,0.,0.];p[axis]=size[axis]*side;p[other[0]]=size[other[0]]*a;p[other[1]]=size[other[1]]*b
            vertices.append(point(p,frame))
        normal=[(1 if side else -1)*frame[axis][j] for j in range(3)]
        result.append(dict(axis=axis,side=side,node_id=500+axis*2+side,face_id=600+axis*2+side,
                           vertices_world_mm=vertices,normal_world=normal))
    return result


def make_fixture():
    size=[900.,600.,330.]
    assemblies=[dict(id=100,occurrence_path=[0,4],matrix_world_mm=copy.deepcopy(I)),
                dict(id=200,occurrence_path=[1,4],matrix_world_mm=copy.deepcopy(I))]
    # An opaque reflected assembly is preserved rather than made proper.
    assemblies[1]['matrix_world_mm'][0][0]=-1
    assemblies[1]['matrix_world_mm'][3]=[20.,40.,60.,1]
    occurrences=[];bindings=[]
    for index,slot in enumerate(itertools.product(range(2),repeat=3)):
        parent=assemblies[slot[2]];cadid=1000+index;anchor_local=[2.,3.,4.]
        anchor_case=[slot[j]*size[j]+(-12 if slot[j]==0 else 12) for j in range(3)]
        anchor_world=point(anchor_case,FRAME)
        world=copy.deepcopy(I)
        if index%2:world[0][0]=-1
        world[3]=[anchor_world[j]-sum(anchor_local[k]*world[k][j] for k in range(3)) for j in range(3)]+[1]
        root=parent['matrix_world_mm'];local=copy.deepcopy(I)
        for i in range(3):
            for j in range(3):local[i][j]=sum(world[i][k]*root[j][k] for k in range(3))
        local[3]=[sum((world[3][k]-root[3][k])*root[j][k] for k in range(3)) for j in range(3)]+[1]
        path=parent['occurrence_path']+[sum(1 for r in occurrences if r['assembly_id']==parent['id'])]
        occurrences.append(dict(id=cadid,assembly_id=parent['id'],occurrence_path=path,matrix_world_mm=world,
            matrix_parent_mm=local,local_bounds_mm=[-40.,-40.,-40.,40.,40.,40.],
            body_signature=dict(volume_m3=.00001,faces=20,edges=40,vertices=24,lumps=1)))
        bindings.append(dict(id=cadid,assembly_id=parent['id'],occurrence_path=path,slot=list(slot),anchor_local_mm=anchor_local))
    evidence=dict(schema_version=1,units='mm',matrix_convention='row-vector',
        source=dict(sha256_before='a'*64,sha256_after='a'*64,guid='corner-source-guid'),
        case_frame=dict(matrix_world_mm=copy.deepcopy(FRAME),size_mm=size,panel_planes=planes(size)),
        assemblies=assemblies,occurrences=occurrences)
    trusted=dict(schema_version=1,evidence_content_sha256=digest(evidence),source_sha256='a'*64,
        source_guid='corner-source-guid',assembly_ids=[100,200],occurrence_bindings=bindings)
    return evidence,trusted


def observed_for(plan):
    binding=plan['binding'];size=plan['target_size_mm']
    return dict(schema_version=1,units='mm',case_frame=dict(matrix_world_mm=copy.deepcopy(FRAME),size_mm=copy.deepcopy(size),panel_planes=planes(size)),
        assemblies=copy.deepcopy(binding['assemblies']),occurrences=[{k:copy.deepcopy(row[k]) for k in
         ('id','assembly_id','occurrence_path','matrix_world_mm','matrix_parent_mm','local_bounds_mm','body_signature')} for row in plan['occurrences']])


class CornerMountTests(unittest.TestCase):
    def call(self,function,*args):
        try:return function(*args)
        except NotImplementedError as exc:self.fail(str(exc))

    def binding(self):return self.call(api.capture_corner_binding,*make_fixture())

    def test_capture_preserves_eight_opaque_orientations_and_two_roots(self):
        evidence,trusted=make_fixture();before=copy.deepcopy((evidence,trusted))
        binding=self.call(api.capture_corner_binding,evidence,trusted)
        self.assertEqual((evidence,trusted),before);self.assertEqual(len(binding['occurrences']),8)
        self.assertEqual(binding['assemblies'],evidence['assemblies'])
        self.assertFalse(binding['mounting_approved']);self.assertFalse(binding['production_approved'])
        for bound,raw in zip(binding['occurrences'],evidence['occurrences']):
            self.assertEqual(bound['source_world_mm'],raw['matrix_world_mm'])
            self.assertEqual(bound['source_parent_mm'],raw['matrix_parent_mm'])

    def test_independent_xyz_resize_and_return_preserve_source_parity(self):
        binding=self.binding();initial=self.call(api.plan_corner_resize,binding,[900.,600.,330.])
        ids=[r['occurrence_id'] for r in initial['occurrences']]
        for size in ([1100.,600.,330.],[900.,720.,330.],[900.,600.,410.],[1100.,720.,410.],[900.,600.,330.]):
            plan=self.call(api.plan_corner_resize,binding,size);self.assertEqual(plan['status'],'planned')
            self.assertEqual([r['occurrence_id'] for r in plan['occurrences']],ids)
            for row in plan['occurrences']:
                wanted_case=[row['slot'][j]*size[j]+(-12 if row['slot'][j]==0 else 12) for j in range(3)]
                self.assertEqual(row['anchor_world_mm'],point(wanted_case,FRAME))
                self.assertEqual(row['matrix_world_mm'][:3],row['source_world_mm'][:3])
                self.assertEqual(row['requested_motion_mm'][:3],I[:3])
                self.assertEqual(row['body_signature'],next(r['body_signature'] for r in binding['occurrences'] if r['id']==row['id']))
            self.assertTrue(self.call(api.validate_corner_observation,plan,observed_for(plan)))
        self.assertEqual(self.call(api.plan_corner_resize,binding,[900.,600.,330.]),initial)

    def test_source_binding_missing_duplicate_or_ambiguous_slots_rejected(self):
        for mutation in ('missing','duplicate_id','duplicate_slot','wrong_assembly','hash'):
            evidence,trusted=make_fixture()
            if mutation=='missing':evidence['occurrences'].pop()
            elif mutation=='duplicate_id':evidence['occurrences'][1]['id']=evidence['occurrences'][0]['id']
            elif mutation=='duplicate_slot':trusted['occurrence_bindings'][1]['slot']=trusted['occurrence_bindings'][0]['slot']
            elif mutation=='wrong_assembly':trusted['occurrence_bindings'][0]['assembly_id']=999
            else:trusted['source_sha256']='b'*64
            trusted['evidence_content_sha256']=digest(evidence)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.call(api.capture_corner_binding,evidence,trusted)

    def test_bad_caseframe_plane_or_source_parent_composition_rejected(self):
        for mutation in ('reflected_frame','plane_off','collinear','wrong_normal','parent_drift'):
            evidence,trusted=make_fixture()
            if mutation=='reflected_frame':evidence['case_frame']['matrix_world_mm'][0][1]=-1
            elif mutation=='plane_off':evidence['case_frame']['panel_planes'][0]['vertices_world_mm'][0][1]+=10
            elif mutation=='collinear':evidence['case_frame']['panel_planes'][0]['vertices_world_mm']=[[1,2,3],[2,3,4],[3,4,5]]
            elif mutation=='wrong_normal':evidence['case_frame']['panel_planes'][0]['normal_world']=[0,0,1]
            else:evidence['occurrences'][0]['matrix_parent_mm'][3][0]+=10
            trusted['evidence_content_sha256']=digest(evidence)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.call(api.capture_corner_binding,evidence,trusted)

    def test_asymmetric_original_offsets_are_not_silently_averaged(self):
        evidence,trusted=make_fixture()
        evidence['occurrences'][0]['matrix_world_mm'][3][0]+=5
        evidence['occurrences'][0]['matrix_parent_mm'][3][0]+=5
        trusted['evidence_content_sha256']=digest(evidence)
        with self.assertRaises(ValueError):self.call(api.capture_corner_binding,evidence,trusted)

    def test_nonfinite_bool_units_and_unknown_fields_rejected(self):
        for field,value in (('units','m'),('schema_version',True),('exec','x')):
            evidence,trusted=make_fixture();evidence[field]=value;trusted['evidence_content_sha256']=digest(evidence)
            with self.subTest(field=field),self.assertRaises(ValueError):self.call(api.capture_corner_binding,evidence,trusted)
        binding=self.binding()
        for size in ([True,600,330],[900,float('inf'),330],[900,600,float('nan')],[0,600,330],[50001,600,330]):
            with self.subTest(size=size),self.assertRaises(ValueError):self.call(api.plan_corner_resize,binding,size)

    def test_observation_must_reject_new_reflection_scale_body_or_root_drift(self):
        plan=self.call(api.plan_corner_resize,self.binding(),[1100.,720.,410.])
        for mutation in ('reflection','scaling','body','root','plane'):
            observed=observed_for(plan)
            if mutation=='reflection':observed['occurrences'][0]['matrix_world_mm'][0][0]*=-1
            elif mutation=='scaling':observed['occurrences'][0]['matrix_world_mm'][0][0]*=1.1
            elif mutation=='body':observed['occurrences'][0]['body_signature']['faces']+=1
            elif mutation=='root':observed['assemblies'][0]['matrix_world_mm'][3][0]+=1
            else:observed['case_frame']['panel_planes'][0]['vertices_world_mm'][0][1]+=5
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.call(api.validate_corner_observation,plan,observed)

    def test_forged_plan_and_observation_common_shift_cannot_self_validate(self):
        plan=self.call(api.plan_corner_resize,self.binding(),[1100.,720.,410.])
        for row in plan['occurrences']:
            row['matrix_world_mm'][3][0]+=30;row['matrix_parent_mm'][3][0]+=30
        plan['content_sha256']=digest({k:v for k,v in plan.items() if k!='content_sha256'})
        with self.assertRaises(ValueError):self.call(api.validate_corner_observation,plan,observed_for(plan))


if __name__=='__main__':unittest.main()
