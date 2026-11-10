import copy
import unittest
import cutting_plan as cut
from material_service import digest
import worker


def inputs(quantity=2, length=500, width=400):
    group=dict(material_id='test',finish='green',technology_id='saw',thickness_mm=9,
        required_date='2026-11-01',grain_axis='X',rotation_allowed=False,
        cut_length_mm=length,cut_width_mm=width,quantity=quantity,
        sources=[dict(project_id='test',row_id='floor',quantity=quantity)])
    demand=dict(groups=[group],bindings=[],total_parts=quantity,scope='synthetic_test',production_approved=False)
    demand['demand_sha256']=digest(demand)
    sheets=[dict(id='stock-1',material_id='test',finish='green',technology_id='saw',thickness_mm=9,
        length_mm=1000,width_mm=400,grain_axis='X',available_date='2026-10-01')]
    technology=dict(id='saw',profile_revision='test-only-1',kerf_mm=3,trim_mm=[0,0,0,0],cut_type='guillotine')
    return demand,sheets,technology


class CuttingTests(unittest.TestCase):
    def test_two_500_strips_on_1000_with_3_kerf_are_rejected(self):
        d,s,t=inputs();result=cut.solve_reference(d,s,t)
        self.assertEqual(result['status'],'no_result');self.assertIsNone(result['plan'])
        part=dict(type='part',group_index=0,rotated=False)
        invalid=dict(input_sha256=cut.validate_inputs(d,s,t),sheets=[dict(sheet_id='stock-1',tree=dict(
            type='cut',axis='X',at_mm=500,first=part,second=part))])
        with self.assertRaisesRegex(ValueError,'dimensions'):cut.verify_cut_plan(d,s,t,invalid)

    def test_feasible_plan_assigns_all_parts_and_explicit_guillotine_sequence(self):
        d,s,t=inputs();s[0]['length_mm']=1003
        result=worker.dispatch('solve_reference_cut_plan',dict(demand=d,sheets=s,technology=t))
        self.assertEqual(result['status'],'feasible');v=result['verification']
        self.assertEqual(len(v['placements']),2);self.assertEqual(len(v['cut_sequence']),1)
        self.assertEqual(v['placements'][1]['x_mm'],503)
        self.assertFalse(v['production_approved']);self.assertEqual(v['optimality'],'not_proven')
        plan=copy.deepcopy(result['plan']);plan['sheets'].append(plan['sheets'][0])
        with self.assertRaises(ValueError):cut.verify_cut_plan(d,s,t,plan)

    def test_material_grain_date_rotation_and_trims_are_enforced(self):
        for changes in [{'finish':'black'},{'grain_axis':'Y'},{'available_date':'2026-11-02'}]:
            d,s,t=inputs(quantity=1);s[0].update(changes)
            self.assertEqual(cut.solve_reference(d,s,t)['status'],'no_result')
        d,s,t=inputs(quantity=1);t['trim_mm']=[5,0,0,0];s[0]['length_mm']=505
        result=cut.solve_reference(d,s,t)
        self.assertEqual(result['verification']['placements'][0]['x_mm'],5)
        d,s,t=inputs(quantity=1,length=400,width=500)
        self.assertEqual(cut.solve_reference(d,s,t)['status'],'no_result')
        d['groups'][0].update(rotation_allowed=True,grain_axis='Y');d['demand_sha256']=digest({k:v for k,v in d.items() if k!='demand_sha256'})
        self.assertTrue(cut.solve_reference(d,s,t)['verification']['placements'][0]['rotated'])

    def test_timeout_does_not_return_partial_unverified_plan(self):
        d,s,t=inputs();times=iter([0,2])
        result=cut.solve_reference(d,s,t,max_seconds=1,clock=lambda:next(times))
        self.assertEqual(result['status'],'timeout');self.assertIsNone(result['last_verified_plan'])

    def test_changed_input_and_incomplete_quantities_are_refused(self):
        d,s,t=inputs(quantity=1);plan=cut.solve_reference(d,s,t)['plan']
        t['kerf_mm']=4
        with self.assertRaisesRegex(ValueError,'INPUT_MISMATCH'):cut.verify_cut_plan(d,s,t,plan)
        d,s,t=inputs(quantity=1);plan=cut.solve_reference(d,s,t)['plan'];plan['sheets']=[]
        with self.assertRaisesRegex(ValueError,'quantities'):cut.verify_cut_plan(d,s,t,plan)
        self.assertFalse(cut.export_neutral_csv(d)['machine_ready'])


if __name__=='__main__':unittest.main()
