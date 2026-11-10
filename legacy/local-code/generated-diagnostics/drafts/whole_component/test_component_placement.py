"""Whole-component placement probes; bbox centers are independent of origins."""
import copy
import itertools
import unittest

from component_placement import plan_component_placement, validate_component_placement


def fixture():
    rows=[]
    for index, slot in enumerate(itertools.product((0,1), repeat=3)):
        # Nonzero bbox center, source reflection preserved, no hole information.
        sx=-1 if index%2 else 1
        r=[[sx,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        center=[10+slot[i]*(n-20) for i,n in enumerate([100,80,60])]
        local=[2,3,4]
        r[3][:3]=[center[0]-sx*2,center[1]-3,center[2]-4]
        rows.append(dict(source_id=index+1,slot=list(slot),matrix_world_mm=r,
                         local_bounds_mm=[0,1,2,4,5,6]))
    return dict(schema_version=1,units='mm',source={'id':'fixture','sha256':'a'*64},
                case_frame={'matrix_world_mm':[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
                            'size_mm':[100,80,60]},target_size_mm=[140,100,90],components=rows)


def observation(request):
    rows=[]
    for row in request['components']:
        matrix=copy.deepcopy(row['matrix_world_mm'])
        for axis in range(3):
            matrix[3][axis]+=row['slot'][axis]*(request['target_size_mm'][axis]-request['case_frame']['size_mm'][axis])
        rows.append(dict(occurrence_id=request['source']['id']+'/'+str(row['source_id']),
                         source_id=row['source_id'],matrix_world_mm=matrix,
                         local_bounds_mm=copy.deepcopy(row['local_bounds_mm'])))
    return dict(schema_version=1,units='mm',source=copy.deepcopy(request['source']),components=rows)


class ComponentPlacementTests(unittest.TestCase):
    def test_nonzero_bbox_center_and_resize(self):
        request=fixture();before=copy.deepcopy(request)
        plan=plan_component_placement(request)
        self.assertEqual(request,before)
        self.assertEqual(plan['status'],'planned')
        self.assertFalse(plan['production_approved'])
        self.assertEqual(plan['components'][0]['bbox_center_local_mm'],[2,3,4])
        self.assertEqual(plan['components'][0]['bbox_center_case_mm'],[10,10,10])
        self.assertEqual(plan['components'][-1]['bbox_center_case_mm'],[130,90,80])
        self.assertTrue(validate_component_placement(plan,observation(request)))

    def test_reordering_stable_and_detached(self):
        request=fixture();a=plan_component_placement(request)
        request['components'].reverse()
        self.assertEqual(a,plan_component_placement(request))
        obs=observation(request);obs['components'].reverse()
        self.assertTrue(validate_component_placement(a,obs))
        request['source']['id']='changed'
        self.assertEqual(a['source']['id'],'fixture')

    def test_missing_duplicate_source_or_slot(self):
        for change in ('missing','id','slot'):
            request=fixture()
            if change=='missing':request['components'].pop()
            if change=='id':request['components'][1]['source_id']=1
            if change=='slot':request['components'][1]['slot']=request['components'][0]['slot'][:]
            with self.subTest(change=change),self.assertRaises(ValueError):plan_component_placement(request)

    def test_nonfinite_bool_scale_badrotation_and_units(self):
        for value in (float('nan'),float('inf'),True,2):
            request=fixture();request['components'][0]['matrix_world_mm'][0][0]=value
            with self.subTest(value=value),self.assertRaises(ValueError):plan_component_placement(request)
        request=fixture();request['components'][0]['matrix_world_mm'][0][1]=.1
        with self.assertRaises(ValueError):plan_component_placement(request)
        request=fixture();request['units']='m'
        with self.assertRaises(ValueError):plan_component_placement(request)

    def test_symmetry_full_tuples_not_only_marginals(self):
        request=fixture()
        request['components'][0]['matrix_world_mm'][3][0]+=1
        request['components'][-1]['matrix_world_mm'][3][0]-=1
        with self.assertRaises(ValueError):plan_component_placement(request)

    def test_observation_refuses_drift_identity_and_bounds(self):
        request=fixture();plan=plan_component_placement(request)
        for change in ('move','rotation','scale','source','bounds','missing','duplicate','boolpath'):
            obs=observation(request)
            if change=='move':obs['components'][0]['matrix_world_mm'][3][1]+=.01
            if change=='rotation':obs['components'][0]['matrix_world_mm'][0][0]*=-1
            if change=='scale':obs['components'][0]['matrix_world_mm'][1][1]=1.01
            if change=='source':obs['source']['sha256']='b'*64
            if change=='bounds':obs['components'][0]['local_bounds_mm'][0]+=.01
            if change=='missing':obs['components'].pop()
            if change=='duplicate':obs['components'][1]=copy.deepcopy(obs['components'][0])
            if change=='boolpath':obs['components'][0]['source_id']=True
            with self.subTest(change=change),self.assertRaises(ValueError):validate_component_placement(plan,obs)

    def test_forged_plan_and_observation_rejected(self):
        request=fixture();plan=plan_component_placement(request);obs=observation(request)
        plan['components'][0]['matrix_world_mm'][3][0]+=3
        obs['components'][0]['matrix_world_mm'][3][0]+=3
        with self.assertRaises(ValueError):validate_component_placement(plan,obs)

    def test_return_preserves_original_opaque_matrix(self):
        request=fixture();request['target_size_mm']=[100,80,60]
        plan=plan_component_placement(request)
        for actual,source in zip(plan['components'],request['components']):
            self.assertEqual(actual['matrix_world_mm'],source['matrix_world_mm'])
        self.assertTrue(validate_component_placement(plan,observation(request)))

    def test_rotated_translated_case_frame(self):
        request=fixture();obs=observation(request)
        # Independent row-vector multiplication maps case axes into world.
        frame=[[0,1,0,0],[-1,0,0,0],[0,0,1,0],[1000,-700,250,1]]
        for rows in (request['components'],obs['components']):
            for row in rows:
                a=row['matrix_world_mm']
                row['matrix_world_mm']=[[sum(a[i][k]*frame[k][j] for k in range(4))
                                         for j in range(4)] for i in range(4)]
        request['case_frame']['matrix_world_mm']=frame
        plan=plan_component_placement(request)
        self.assertEqual(plan['components'][0]['bbox_center_case_mm'],[10,10,10])
        self.assertEqual(plan['components'][0]['bbox_center_world_mm'],[990,-690,260])
        self.assertTrue(validate_component_placement(plan,obs))

    def test_plan_type_confusion_rejected(self):
        request=fixture();plan=plan_component_placement(request)
        plan['components'][0]['source_id']=True
        with self.assertRaises(ValueError):validate_component_placement(plan,observation(request))


if __name__=='__main__':unittest.main()
