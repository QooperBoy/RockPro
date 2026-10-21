import itertools
import math
import tempfile
import unittest
from pathlib import Path
import project_store
from layout import calculate_layout, save_layout, get_layout
from worker import dispatch

class LayoutTests(unittest.TestCase):
    def test_orientations_and_axis(self):
        for order in itertools.permutations('XYZ'):
            for axis in 'XYZ':
                r=calculate_layout(dict(x=100,y=200,z=300,count=3,orientation=''.join(order),arrangement=axis,gap=10,clearance=5,separator=9,lid_height=30))
                expected=[dict(X=100,Y=200,Z=300)[v] for v in order]
                a='XYZ'.index(axis); expected[a]=expected[a]*3+38
                self.assertEqual(r['internal'],[v+10 for v in expected])
                self.assertEqual(len(r['boxes']),5)
                self.assertTrue(r['checks']['contained'])
    def test_accessory_fits_and_expands(self):
        for side in ('X','Y'):
            r=calculate_layout(dict(side=side,side_width=90,side_depth=1500,side_height=900))
            self.assertGreaterEqual(r['internal'][2],940)
            self.assertEqual(sum(b['kind']=='accessory' for b in r['boxes']),1)
            self.assertFalse(r['checks']['collisions'])
    def test_invalid_inputs(self):
        for spec in (dict(count=1.5),dict(count=True),dict(x=math.nan),dict(x=math.inf),dict(gap=-1),dict(orientation='XXY'),dict(arrangement='foo'),dict(lid_height=1000),dict(side='left'),dict(foo=1)):
            with self.assertRaises(ValueError): calculate_layout(spec)
    def test_parameters_account_for_walls(self):
        r=calculate_layout(dict(count=1,x=100,y=200,z=300,clearance=10,thickness=9,lid_height=50))
        self.assertEqual(r['external'],[138,238,338])
        self.assertEqual(r['parameters']['RP_BaseHeight'],288)
    def test_save_roundtrip_and_invalidation(self):
        old=project_store.DB_PATH
        try:
            with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
                project_store.DB_PATH=Path(folder)/'db.sqlite3'
                with project_store.db() as c:
                    c.execute('INSERT INTO projects (id,name,client,device,quantity,notes,source,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',('p','test','','',1,'','test.ics','now','now'))
                    c.executemany('INSERT INTO stages (project_id,key,label,status,note,updated_at) VALUES (?,?,?,?,?,?)',[('p',k,l,'approved','','now') for k,l in project_store.STAGES])
                r=save_layout('p',dict(count=4,side='Y'),0)
                self.assertEqual(r['database'],str(project_store.DB_PATH))
                self.assertEqual(r['spec'],get_layout('p')['spec'])
                with project_store.db() as c:
                    statuses=dict(c.execute('SELECT key,status FROM stages'))
                self.assertEqual(statuses['geometry'],'outdated')
                self.assertEqual(statuses['layout'],'review')
                self.assertEqual(statuses['inquiry'],'approved')
        finally: project_store.DB_PATH=old
    def test_mcp_contract(self):
        self.assertEqual(dispatch('preview_layout',{'spec':{}})['spec']['count'],2)
        with self.assertRaises(ValueError):dispatch('preview_layout',{'spec':{},'shell':'bad'})
    def test_ranking_formula_and_global_minimum(self):
        r=calculate_layout(dict(x=100,y=200,z=300,count=4,gap=20,separator=9,clearance=10,thickness=9,lid_height=30))
        expected=[]
        for order in itertools.permutations('XYZ'):
            for a in range(3):
                d=[dict(X=100,Y=200,Z=300)[k] for k in order]
                d[a]=4*d[a]+3*(20+9)
                volume=math.prod(v+2*10+2*9 for v in d)/1_000_000
                expected.append(volume)
        self.assertAlmostEqual(r['ranking']['best']['volume_l'],min(expected))
        self.assertEqual(len(r['ranking']['variants']),18)
        for field in ('orientations','arrangements'):
            rows=r['ranking'][field]
            self.assertEqual([v['volume_l'] for v in rows],sorted(v['volume_l'] for v in rows))
            self.assertAlmostEqual(rows[0]['score'],0)
            self.assertAlmostEqual(rows[-1]['score'],1)
    def test_equal_volume_choices_have_equal_score(self):
        r=calculate_layout(dict(x=100,y=100,z=100,count=1,lid_height=30))
        self.assertTrue(all(v['score']==0 for v in r['ranking']['orientations']))
        self.assertTrue(all(v['score']==0 for v in r['ranking']['arrangements']))
    def test_ranking_uses_accessory_and_marks_infeasible(self):
        r=calculate_layout(dict(x=100,y=200,z=300,count=3,side='X',side_depth=400,side_width=80,lid_height=200))
        valid=[v for v in r['ranking']['variants'] if v['valid']]
        self.assertTrue(any(not v['valid'] for v in r['ranking']['variants']))
        for item in valid:
            self.assertAlmostEqual(item['volume_l'],math.prod(item['external'])/1_000_000)
        self.assertAlmostEqual(r['ranking']['best']['volume_l'],min(v['volume_l'] for v in valid))

if __name__=='__main__': unittest.main()
