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
from rockpro_cad.mcp import project_store
from rockpro_cad.reference_studio import make_handler


def concept():
    return dict(schema='rockpro.configurator/1', name='Próba kreatora', type='case', subtype='top',
                internal_mm=[600,500,350], thickness_mm=9.8, joint_gap_mm=2,
                cooperation='independent', covers=[dict(id='lid-a',label='Wieko',face='top',depth_mm=45,
                    kind='hinged',hinge_edge='high',requires=[],height_override=False)])


class ConfiguratorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/'projects.sqlite3'
        self.patcher=patch.object(project_store,'DB_PATH',self.db);self.patcher.start();self.addCleanup(self.patcher.stop)

    def test_section_envelope_and_required_interior_survive_lid_changes(self):
        d=concept();before=copy.deepcopy(d);model=c.preview(d)
        self.assertEqual(d,before);self.assertEqual(model['sections'][0]['size_mm'],[619.6,519.6,369.6])
        self.assertEqual(sum(p['section']=='body' for p in model['panels']),5)
        d['covers'][0]['depth_mm']=50
        changed=c.preview(d)
        self.assertEqual(changed['sections'][0],model['sections'][0]);self.assertEqual(changed['draft']['internal_mm'],[600,500,350])
        self.assertFalse(changed['cad_ready'])

    def test_opposing_and_split_covers_get_distinct_sections_and_joint_ids(self):
        d=concept();d['subtype']='custom';d['covers'][0]['face']='front'
        other=copy.deepcopy(d['covers'][0]);other.update(id='lid-b',face='front');d['covers'].append(other)
        model=c.preview(d);a,b=model['sections'][1:]
        self.assertEqual(a['size_mm'][0],(619.6-2)/2)
        self.assertAlmostEqual(b['position_mm'][0]-a['position_mm'][0]-a['size_mm'][0],2)
        self.assertEqual(len({j['id'] for j in model['joints']}),2)
        other['face']='rear';model=c.preview(d)
        self.assertLess(model['sections'][1]['position_mm'][1],0)
        self.assertGreater(model['sections'][2]['position_mm'][1],519.6)

    def test_dependencies_are_bound_and_cycles_are_refused(self):
        d=concept();d['subtype']='custom';d['cooperation']='custom'
        other=copy.deepcopy(d['covers'][0]);other.update(id='lid-b',face='front',requires=['lid-a']);d['covers'].append(other)
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
        d['subtype']='hood';d['covers'][0].update(kind='removable',height_override=False)
        self.assertTrue(c.preview(d)['sections'])

    def test_incompatible_subtype_and_invalid_dimensions_are_refused(self):
        for field,value in [('type','other'),('subtype','double_front'),('thickness_mm',True),('joint_gap_mm',float('nan'))]:
            d=concept();d[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):c.preview(d)
        d=concept();d['internal_mm'][0]=0
        with self.assertRaises(ValueError):c.preview(d)
        d=concept();d['covers'][0]['kind']='removable'
        with self.assertRaises(ValueError):c.preview(d)

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
