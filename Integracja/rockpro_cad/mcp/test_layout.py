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
                    c.execute('INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?)',('p','test','','',1,'','test.ics','now','now'))
                    c.executemany('INSERT INTO stages VALUES (?,?,?,?,?,?)',[('p',k,l,'approved','','now') for k,l in project_store.STAGES])
                r=save_layout('p',dict(count=4,side='Y'))
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

if __name__=='__main__': unittest.main()
