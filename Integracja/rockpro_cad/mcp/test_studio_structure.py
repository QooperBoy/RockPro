import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from rockpro_cad import configurator as c
from rockpro_cad.studio_structure import REQUIRED
from rockpro_cad.mcp import project_store
from rockpro_cad.mcp.test_configurator import concept
from rockpro_cad.mcp.test_studio_closures import row
from rockpro_cad.mcp.test_studio_placement import handles


def complete():
    d=concept();d['internal_mm']=[600,500,800];d['covers'][0]['depth_mm']=115
    d['construction']=dict(enabled=True,wheels=True,stacking=True)
    d['hardware']=[dict(part_id=p,revision=1) for p in REQUIRED+['source-caster-epson','W0968Z','H7159','17251S','270836']]
    d['placements']=[handles(),row(count=2),dict(row('270836','seam-lid-a-rear',2),id='hinges')]
    return d


class StructureTests(unittest.TestCase):
    def test_full_families_and_proper_rotations(self):
        p=c.preview(complete());items=p['construction']['items']
        self.assertEqual(len({x['id'] for x in items}),len(items))
        self.assertEqual(p['construction']['counts']['410429'],8)
        self.assertEqual(p['construction']['counts']['EG-0113'],16)
        self.assertEqual(p['project_summary']['total_count'],76)
        self.assertEqual(p['project_summary']['unplaced_selection'],[])
        self.assertFalse(p['project_summary']['purchase_bom_ready'])
        self.assertEqual({x['family_id'] for x in items},
            {'profiles','corners','braces','wheels','wheel_pads','stacking_sockets'})
        for x in items:
            a,b,z=x['rotation'];cross=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
            self.assertEqual(sum(u*v for u,v in zip(cross,z)),1,x['id'])

    def test_wheels_sockets_and_supports_follow_dimensions(self):
        for size in [[600,500,800],[900,650,900],[400.4,380,800]]:
            d=complete();d['internal_mm']=size;p=c.preview(d);rows=p['construction']['items']
            wheels={x['stacking_pair']:x for x in rows if x['family_id']=='wheels'}
            height=sum(s['size_mm'][2] for s in p['sections'])
            for socket in [x for x in rows if x['family_id']=='stacking_sockets']:
                wheel=wheels[socket['stacking_pair']]
                # Source caster contact is displaced from its mounting origin.
                point=[-36.,-132.1,0.]
                contact=[wheel['position_mm'][j]+sum(point[k]*wheel['rotation'][k][j] for k in range(3)) for j in range(3)]
                self.assertEqual(socket['seat_world_mm'][:2],contact[:2])
                self.assertAlmostEqual(socket['seat_world_mm'][2],height)
                self.assertEqual(socket['stage_id'],'wheels')
            for pad in [x for x in rows if x['family_id']=='wheel_pads']:
                self.assertGreaterEqual(pad['position_mm'][1],35)
                self.assertLessEqual(pad['position_mm'][1]+pad['size_mm'][1],p['sections'][0]['size_mm'][1]-35)

    def test_socket_clearance_uses_actual_seats_and_does_not_resize_case(self):
        for width in (380.,396.4,400.3):
            d=complete();d['internal_mm'][0]=width;before=copy.deepcopy(d)
            with self.assertRaisesRegex(ValueError,'Gniazda kół'):
                c.preview(d)
            self.assertEqual(d,before)
            d['construction']['stacking']=False
            self.assertFalse(any(r['family_id']=='stacking_sockets' for r in c.preview(d)['construction']['items']))
        d=complete();d['internal_mm'][0]=400.4
        rows=c.preview(d)['construction']['items']
        front=[r for r in rows if r['family_id']=='stacking_sockets' and r['seat_world_mm'][1]==100]
        self.assertEqual(len(front),2)
        self.assertAlmostEqual(abs(front[0]['seat_world_mm'][0]-front[1]['seat_world_mm'][0])-136,2)
        self.assertEqual(d['internal_mm'][0],400.4)

    def test_profile_interruptions_follow_closures(self):
        d=complete();p=c.preview(d)
        for closure in p['placement']['items']:
            if not closure.get('seam_id'):continue
            center=closure['position_mm'][0];half=closure['footprint_mm'][0]/2+5
            for x in p['construction']['items']:
                if not x['id'].startswith('joint/') or '/'+closure['face']+'/' not in x['id']:continue
                a,b=sorted([x['position_mm'][0],x['position_mm'][0]+x['rotation'][2][0]*x['length_mm']])
                self.assertTrue(b<=center-half+.001 or a>=center+half-.001)
        moved=copy.deepcopy(d);moved['placements'][1]['edge_inset_mm']=150
        self.assertNotEqual(c.preview(moved)['construction'],p['construction'])

    def test_native_caster_frames_keep_wheel_contact_and_socket_seat_in_sync(self):
        p=c.preview(complete());rows={r['id']:r for r in p['construction']['items']}
        for right in (False,True):
            for rear in (False,True):
                key='wheel-'+str(int(right))+str(int(rear));wheel=rows[key];socket=rows['socket/'+key]
                self.assertEqual(wheel['rotation'],[[1 if right else -1,0,0],[0,0,1],[0,-1 if right else 1,0]])
                self.assertAlmostEqual(socket['seat_world_mm'][0]-wheel['position_mm'][0],-36 if right else 36)
                self.assertAlmostEqual(socket['seat_world_mm'][1],wheel['position_mm'][1])
                self.assertEqual(wheel['stacking_pair'],socket['stacking_pair'])
                self.assertEqual(wheel['stage_id'],socket['stage_id'])

    def test_uprights_respect_joint_gap_and_keep_edge_profile_ids(self):
        for size,lid_height in [([600,500,800],115),([900,650,900],125)]:
            draft=complete();draft['internal_mm']=size;draft['covers'][0]['depth_mm']=lid_height
            p=c.preview(draft);rows={r['id']:r for r in p['construction']['items']}
            w,d,b=p['sections'][0]['size_mm'];lid=draft['covers'][0]['id']
            for corner in ('00','10','01','11'):
                body=rows['upright/body/'+corner];top=rows['upright/'+lid+'/'+corner]
                self.assertAlmostEqual(body['position_mm'][2],30)
                self.assertAlmostEqual(body['length_mm'],b-60)
                self.assertAlmostEqual(top['position_mm'][2],b+8.63+30)
                self.assertAlmostEqual(top['length_mm'],lid_height-8.63-60)
            for level in ('bottom','top'):
                for face in ('front','rear','left','right'):
                    item=rows['edge/'+level+'/'+face]
                    axis=0 if face in ('front','rear') else 1
                    end=item['position_mm'][axis]+item['rotation'][2][axis]*item['length_mm']
                    ends=sorted([item['position_mm'][axis],end])
                    self.assertAlmostEqual(ends[0],30)
                    self.assertAlmostEqual(ends[1],(w if axis==0 else d)-30)

    def test_joint_cross_sections_and_segment_endpoints_match_native_axes(self):
        draft=complete();draft['placements']=[]
        p=c.preview(draft);w,d,b=p['sections'][0]['size_mm']
        joints=[r for r in p['construction']['items'] if r['id'].startswith('joint/')]
        self.assertEqual(len(joints),8)
        for item in joints:
            face=item['id'].split('/')[-2];male=item['part_id']=='EG-0500/1'
            axis=0 if face in ('front','rear') else 1;origin=item['position_mm'];r=item['rotation']
            expected_direction=-1 if face in ('rear','right') else 1
            self.assertEqual(r[2][axis],expected_direction)
            bounds=sorted([origin[axis],origin[axis]+r[2][axis]*item['length_mm']])
            expected=[0,w] if axis==0 else [3,d-3]
            for a,e in zip(bounds,expected):self.assertAlmostEqual(a,e)
            self.assertAlmostEqual(origin[2],b-19.4965848981016 if male else b+23.7593904046396)
            transverse=origin[1-axis]
            # Male/female seating is different on long and short edges.
            low=11.05058825963358 if male and axis==0 else -1.25058825963358 if male else -1.25 if axis==0 else 11.05
            expected_transverse=low if face in ('front','left') else (d if axis==0 else w)-low
            self.assertAlmostEqual(transverse,expected_transverse)
        # With closure interruptions, even negative-Z rows stay inside the
        # same native extent and never cover the reserved closure intervals.
        p=c.preview(complete())
        for item in p['construction']['items']:
            if not item['id'].startswith('joint/'):continue
            face=item['id'].split('/')[-2];axis=0 if face in ('front','rear') else 1
            a,z=sorted([item['position_mm'][axis],item['position_mm'][axis]+item['rotation'][2][axis]*item['length_mm']])
            self.assertGreaterEqual(a,-1e-8);self.assertLessEqual(z,(w if axis==0 else d)+1e-8)
            for closure in p['placement']['items']:
                if not closure.get('seam_id') or closure['face']!=face:continue
                center=closure['position_mm'][axis];half=closure['footprint_mm'][0]/2+5
                self.assertTrue(z<=center-half+1e-8 or a>=center+half-1e-8)

    def test_brace_native_datums_and_lid_orientation_survive_resize(self):
        for size in ([600,500,800],[850,650,900]):
            draft=complete();draft['internal_mm']=list(size);p=c.preview(draft)
            w,d,h=p['sections'][0]['size_mm'];lid=draft['covers'][0]['id']
            rows={r['id']:r for r in p['construction']['items']}
            for section,z in [('body',h-40),(lid,h+8.63)]:
                expected={'00':[-4.7,-4.7,z],'10':[w+4.7,-4.7,z],
                          '01':[25.8,d-28.35,z],'11':[w-25.8,d-28.35,z]}
                for corner,position in expected.items():
                    row=rows['brace/'+section+'/'+corner]
                    for a,b in zip(row['position_mm'],position):self.assertAlmostEqual(a,b)
                    self.assertEqual(row['rotation'],rows['brace/body/'+corner]['rotation'])
            self.assertEqual(rows['brace/body/01']['rotation'],[[-1,0,0],[0,0,1],[0,1,0]])
            self.assertEqual(rows['brace/body/11']['rotation'],[[0,1,0],[0,0,1],[1,0,0]])

    def test_invalid_requests_and_legacy_are_not_silently_changed(self):
        d=complete()
        for change in [dict(wheels=False,stacking=True,enabled=True),dict(enabled=1,wheels=True,stacking=True)]:
            bad=copy.deepcopy(d);bad['construction']=change
            with self.assertRaises(ValueError):c.preview(bad)
        bad=copy.deepcopy(d);bad['hardware']=[x for x in bad['hardware'] if x['part_id']!='410429']
        with self.assertRaises(ValueError):c.preview(bad)
        bad=copy.deepcopy(d);bad['covers'][0]['depth_mm']=45
        with self.assertRaises(ValueError):c.preview(bad)
        legacy=concept();self.assertEqual(c.preview(legacy)['construction']['items'],[])
        self.assertNotIn('construction',legacy)

    def test_save_reopen_preserves_complete_recipe(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(project_store,'DB_PATH',Path(temp)/'test.sqlite3'):
            saved=c.save_draft(complete());read=c.read_draft(saved['id'])
            self.assertEqual(read,saved)
            self.assertEqual(c.preview(saved['draft']),c.preview(read['draft']))


if __name__=='__main__':unittest.main()
