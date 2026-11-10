import copy
import json
from pathlib import Path
import sqlite3
import http.client
import threading
from http.server import ThreadingHTTPServer
import tempfile
import unittest
from unittest.mock import patch

from rockpro_cad import configurator as c
from rockpro_cad import studio_parts as parts
from rockpro_cad.mcp import project_store
from rockpro_cad.reference_studio import make_handler


def concept():
    return dict(schema='rockpro.configurator/3', name='Próba kreatora', type='case',
                internal_mm=[600,500,350], thickness_mm=9.8,
                cooperation='independent', hardware=[], covers=[dict(id='lid-a',label='Wieko',face='top',depth_mm=45,
                    kind='hinged',hinge_edge='high',requires=[],height_override=False)])


def three_piece():
    d=concept();d['type']='three_piece';d['covers'][0]['kind']='removable'
    front=copy.deepcopy(d['covers'][0]);front.update(id='front',label='Przód',face='front',depth_mm=40)
    d['covers'].append(front)
    return d


class ConfiguratorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/'projects.sqlite3'
        self.patcher=patch.object(project_store,'DB_PATH',self.db);self.patcher.start();self.addCleanup(self.patcher.stop)

    def test_catalogue_keeps_aliases_as_one_definition_and_preserves_unknown_sku(self):
        catalog=parts.catalog();rows={r['id']:r for r in catalog['items']}
        self.assertIn('H7159',rows);self.assertIn('27095',rows)
        self.assertIn('17251S_1',rows['17251S']['aliases']);self.assertNotIn('17251S_1',rows)
        self.assertIsNone(rows['source-caster-epson']['sku'])
        self.assertFalse(rows['2643']['selectable'])
        self.assertTrue(all(not r['automatic_placement_approved'] and not r['production_approved'] for r in rows.values()))
        catalog['items'][0]['name']='mutated';catalog['categories']['handles']='mutated'
        self.assertNotEqual(parts.catalog()['items'][0]['name'],'mutated')
        self.assertEqual(parts.catalog()['categories']['handles'],'Uchwyty')

    def test_part_selection_refuses_unknown_revision_duplicates_and_empty_source(self):
        ref=dict(part_id='H7159',revision=1)
        for refs in [[dict(part_id='unknown',revision=1)], [dict(part_id='H7159',revision=2)],
                     [dict(part_id='H7159',revision=True)], [ref,ref],
                     [dict(part_id='2643',revision=1)], [dict(ref,quantity=4)]]:
            d=concept();d['hardware']=refs
            with self.subTest(refs=refs),self.assertRaises(ValueError):c.preview(d)

    def test_parts_roundtrip_and_summary_never_place_or_resize_hardware(self):
        d=concept();before=c.preview(d)
        d['hardware']=[dict(part_id='H7159',revision=1),dict(part_id='EG-0500/1',revision=1)]
        after=c.preview(d);summary=after['hardware_summary']
        self.assertEqual(after['panels'],before['panels']);self.assertEqual(after['sections'],before['sections'])
        self.assertEqual(summary['definition_count'],2);self.assertFalse(summary['purchase_bom_ready'])
        self.assertEqual(summary['placement_status'],'not_started');self.assertTrue(summary['warnings'])
        self.assertEqual(after['joint_fitting_status'],'awaiting_mounting_layout')
        self.assertTrue(all(j['gap_mm'] is None and j['plywood_trim_mm'] is None for j in after['joints']))
        saved=c.save_draft(d);self.assertEqual(c.read_draft(saved['id'])['draft'],d)
        d['hardware'].append(dict(part_id='EG-0500/2',revision=1))
        self.assertFalse(c.preview(d)['hardware_summary']['warnings'])

    def test_existing_v3_without_hardware_keeps_empty_selection(self):
        d=concept();d.pop('hardware');before=copy.deepcopy(d)
        self.assertEqual(c.preview(d)['draft']['hardware'],[])
        self.assertEqual(d,before)

    def test_section_envelope_and_required_interior_survive_lid_changes(self):
        d=concept();before=copy.deepcopy(d);model=c.preview(d)
        self.assertEqual(d,before);self.assertEqual(model['sections'][0]['size_mm'],[619.6,519.6,369.6])
        self.assertEqual(sum(p['section']=='body' for p in model['panels']),5)
        d['covers'][0]['depth_mm']=50
        changed=c.preview(d)
        self.assertEqual(changed['sections'][0],model['sections'][0]);self.assertEqual(changed['draft']['internal_mm'],[600,500,350])
        self.assertFalse(changed['cad_ready'])

    def test_three_piece_front_stays_flush_with_top_and_bottom_after_resize(self):
        d=three_piece()
        for height,top_depth,thickness in [(350,45,9.8),(500,120,12),(200,30,6)]:
            with self.subTest(height=height):
                d['internal_mm']=[800,600,height];d['thickness_mm']=thickness;d['covers'][0]['depth_mm']=top_depth
                model=c.preview(d);body,top,front=model['sections']
                self.assertEqual(front['position_mm'][2],body['position_mm'][2])
                self.assertAlmostEqual(front['position_mm'][2]+front['size_mm'][2],top['position_mm'][2]+top['size_mm'][2])
                self.assertEqual(body['size_mm'][2],height+2*thickness)
                # Actual panel extents, not merely metadata, must share the upper plane.
                def upper(key):return max(p['center_mm'][2]+p['size_mm'][2]/2 for p in model['panels'] if p['section']==key)
                self.assertAlmostEqual(upper(front['id']),upper(top['id']))
                self.assertEqual(len(model['joints']),2)

    def test_gap_is_unknown_hardware_result_and_never_expands_the_envelope(self):
        d=three_piece();model=c.preview(d)
        self.assertEqual(model['joint_fitting_status'],'awaiting_hardware')
        self.assertEqual(model['panel_dimensions_status'],'nominal_not_cutting')
        for joint in model['joints']:
            self.assertIsNone(joint['gap_mm']);self.assertIsNone(joint['plywood_trim_mm'])
        for previous_gap in (.5,2,8.63):
            old=copy.deepcopy(d);old.update(schema='rockpro.configurator/2',joint_gap_mm=previous_gap)
            original=copy.deepcopy(old);converted=c.convert_legacy(old)
            self.assertEqual(old,original)
            self.assertNotIn('joint_gap_mm',converted)
            self.assertEqual(c.preview(converted)['panels'],model['panels'])
            self.assertEqual(c.preview(converted)['sections'],model['sections'])
        d['joint_gap_mm']=2
        with self.assertRaises(ValueError):c.preview(d)

    def test_exactly_three_fixed_types_without_subtype_or_double_front(self):
        self.assertEqual(set(c.TYPES),{'case','cabinet','three_piece'})
        for type_,face in [('case','top'),('cabinet','front')]:
            for kind in ('hinged','removable'):
                d=concept();d['type']=type_;d['covers'][0].update(face=face,kind=kind)
                self.assertEqual(len(c.preview(d)['sections']),2)
        d=three_piece();d['covers'][0]['kind']='hinged'
        with self.assertRaises(ValueError):c.preview(d)
        d=concept();d['subtype']='double_front'
        with self.assertRaises(ValueError):c.preview(d)
        d=concept();d['type']='cabinet';d['covers'][0]['face']='front';other=copy.deepcopy(d['covers'][0]);other['id']='other';d['covers'].append(other)
        with self.assertRaises(ValueError):c.preview(d)

    def test_legacy_conversion_is_explicit_non_mutating_and_refuses_two_fronts(self):
        old=three_piece();old.update(schema='rockpro.configurator/1',type='case',subtype='two_covers');old['covers'][0]['kind']='hinged'
        before=copy.deepcopy(old);new=c.convert_legacy(old)
        self.assertEqual(old,before);self.assertNotIn('subtype',new);self.assertEqual(new['type'],'three_piece')
        self.assertTrue(all(x['kind']=='removable' for x in new['covers']))
        with self.assertRaises(ValueError):c.save_draft(old)
        saved=c.save_draft(new);self.assertEqual(saved['revision'],1)
        # Seed a genuine old-format record, as produced before the type reduction.
        with project_store.db() as conn:
            conn.execute('UPDATE configurator_drafts SET payload=? WHERE id=?',(json.dumps(before),saved['id']))
        with self.assertRaisesRegex(ValueError,'Archiwalny'):
            c.save_draft(new,saved['id'],1)
        self.assertEqual(c.read_draft(saved['id'])['draft'],before)
        self.assertNotEqual(c.save_draft(new)['id'],saved['id'])
        old['covers'][0]['face']='front'
        with self.assertRaises(ValueError):c.convert_legacy(old)

    def test_dependencies_are_bound_and_cycles_are_refused(self):
        d=three_piece();d['cooperation']='custom'
        other=d['covers'][1];other.update(id='lid-b',requires=['lid-a'])
        self.assertEqual(c.preview(d)['sections'][2]['requires'],['lid-a'])
        d['covers'][0]['requires']=['lid-b']
        with self.assertRaisesRegex(ValueError,'Cykl'):c.preview(d)
        d['covers'][0]['requires']=['missing']
        with self.assertRaises(ValueError):c.preview(d)

    def test_tall_top_lid_requires_explicit_override_without_growing_base(self):
        d=concept();d['covers'][0]['depth_mm']=115
        with self.assertRaisesRegex(ValueError,'odstępstwo'):c.preview(d)
        d['covers'][0]['height_override']=True
        self.assertEqual(c.preview(d)['draft']['internal_mm'],[600,500,350])
        d=three_piece();d['covers'][0]['depth_mm']=115
        self.assertTrue(c.preview(d)['sections'])

    def test_incompatible_subtype_and_invalid_dimensions_are_refused(self):
        for field,value in [('type','other'),('type','workstation'),('thickness_mm',True),('cooperation','invalid')]:
            d=concept();d[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):c.preview(d)
        d=concept();d['internal_mm'][0]=0
        with self.assertRaises(ValueError):c.preview(d)
        d=concept();d['covers'][0]['kind']='sliding'
        with self.assertRaises(ValueError):c.preview(d)

    def test_case_removable_save_preserves_geometry_and_hinge_side(self):
        d=concept();d['covers'][0]['hinge_edge']='low';before=c.preview(d)
        d['covers'][0]['kind']='removable';saved=c.save_draft(d)
        restored=c.read_draft(saved['id'])['draft'];after=c.preview(restored)
        self.assertEqual(restored,d)
        self.assertEqual(after['panels'],before['panels'])
        self.assertEqual(after['sections'][1]['kind'],'removable')
        restored['covers'][0]['kind']='hinged'
        self.assertEqual(c.preview(restored)['sections'][1]['hinge_edge'],'low')

    def test_save_reload_history_and_stale_write_are_atomic(self):
        d=concept();saved=c.save_draft(d);self.assertEqual(saved['revision'],1)
        d['name']='Zmieniona nazwa';second=c.save_draft(d,saved['id'],1)
        self.assertEqual(c.read_draft(saved['id']),second)
        with self.assertRaises(c.DraftConflict):c.save_draft(concept(),saved['id'],1)
        with sqlite3.connect(self.db) as conn:
            history=conn.execute('SELECT payload FROM configurator_draft_versions ORDER BY revision').fetchall()
        conn.close()
        self.assertEqual(len(history),2);self.assertEqual(json.loads(history[0][0])['name'],'Próba kreatora')
        self.assertEqual(c.list_drafts()[0]['name'],'Zmieniona nazwa')

    def test_invalid_draft_cannot_create_database_or_replace_saved_data(self):
        d=concept();d['covers'][0]['depth_mm']=0
        with self.assertRaises(ValueError):c.save_draft(d)
        self.assertFalse(self.db.exists())
        saved=c.save_draft(concept())
        with self.assertRaises(ValueError):c.save_draft(d,saved['id'],1)
        self.assertEqual(c.read_draft(saved['id']),saved)

    def test_http_save_uses_origin_revision_and_roundtrip(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),make_handler({}, {}, 'test'))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port)
        try:
            conn.request('GET','/test/wizard/parts');response=conn.getresponse()
            self.assertEqual(response.status,200)
            catalogue=json.loads(response.read());self.assertIn('H7159',{r['id'] for r in catalogue['items']})
            command=dict(draft=concept(),id=None,expected_revision=0)
            conn.request('POST','/test/wizard/save',json.dumps(command),{'Origin':'https://foreign.example','X-RockPro-Session':'test'})
            response=conn.getresponse();self.assertEqual(response.status,403);response.read();self.assertFalse(self.db.exists())
            headers={'Origin':f'http://127.0.0.1:{server.server_port}','X-RockPro-Session':'test'}
            conn.request('POST','/test/wizard/save',json.dumps(command),headers)
            response=conn.getresponse();self.assertEqual(response.status,200);saved=json.loads(response.read())
            conn.request('GET','/test/wizard/drafts/'+saved['id']);response=conn.getresponse();self.assertEqual(json.loads(response.read()),saved)
            command['id']=saved['id']
            conn.request('POST','/test/wizard/save',json.dumps(command),headers)
            response=conn.getresponse();self.assertEqual(response.status,409);response.read()
        finally:
            conn.close();server.shutdown();server.server_close();thread.join(timeout=2)


if __name__=='__main__':unittest.main()
