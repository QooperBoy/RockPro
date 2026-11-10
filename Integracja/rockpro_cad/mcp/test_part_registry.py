import unittest
from rockpro_cad.part_registry import contract, metadata, legacy_export_family, stage_for
from rockpro_cad.process_observer import stage_key
from rockpro_cad.core_case.transport_rules import make_rules
from rockpro_cad.core_case.test_transport_rules import fixture
from rockpro_cad.core_case.profile_rules import value

class RegistryTests(unittest.TestCase):
    def test_stage_six_contains_wheels_sockets_and_pads_only(self):
        c=contract();self.assertEqual(c['stages'][5]['id'],'wheels')
        for family in ('wheel','socket','stacking_sockets','wheelpads'):
            self.assertEqual(stage_for(family),'wheels')
            self.assertEqual(stage_key(dict(operation='native.create',family=family)),'wheels')
        self.assertEqual(stage_for('corner'),'corners')
        self.assertEqual(stage_for('unrelated_socket_connector'),'other')
        with self.assertRaises(ValueError):legacy_export_family('Electrical socket')
        self.assertEqual(legacy_export_family('RockPro  socketleftfront'),'stacking_sockets')

    def test_all_transport_pairs_share_stage_and_parameterized_xy_after_resize(self):
        rows=make_rules(fixture());by={r['id']:r for r in rows}
        for length,depth,height,lid in ((650,500,300,81),(850,620,350,90),(2000,3000,3600,400)):
            values=dict(RP_Length=length,RP_Depth=depth,RP_BaseHeight=height,RP_LidHeight=lid,RP_DisplayGap=0)
            wheels=[r for r in rows if r['kind']=='wheel'];self.assertEqual(len(wheels),4)
            for wheel in wheels:
                socket=by['socket/'+wheel['pair']]
                self.assertEqual(wheel['stacking_interface_id'],socket['stacking_interface_id'])
                self.assertEqual(wheel['stage_id'],socket['stage_id'])
                self.assertNotEqual(wheel['family_id'],socket['family_id'])
                p=[value(x,values) for x in wheel['anchor']]
                contact=[p[j]+sum(wheel['contact_local_mm'][k]*wheel['rotation'][k][j] for k in range(3)) for j in range(3)]
                target=[value(x,values) for x in socket['anchor']]
                self.assertEqual(contact[:2],target[:2]);self.assertEqual(target[2],height+lid)


    def test_export_retains_explicit_socket_identity_and_rejects_wrong_ics(self):
        import importlib.util,json,tempfile,zipfile,hashlib
        from pathlib import Path
        script=Path(__file__).resolve().parents[3]/'scripts'/'prepare_layer_viewer.py'
        spec=importlib.util.spec_from_file_location('registry_export_test',script)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'native.zip';ics=root/'source.ics';ics.write_bytes(b'pinned model')
            with zipfile.ZipFile(source,'w') as z:
                z.writestr('tree.json',json.dumps({'t':[{'id':17,'t':'p','i':'1','n':'arbitrary user rename'}]}))
                z.writestr('0.json',json.dumps(dict(id=1,v=[0,0,0,1,0,0,0,1,0],n=[0,0,1]*3,p=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],c=[dict(t=3,c='808040')])))
            report=dict(passed=True,source_export_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),result_sha256=hashlib.sha256(ics.read_bytes()).hexdigest(),registry=contract(),bindings=[dict(node_id=17,occurrence_id='socket/left/front',stacking_interface_id='caster100/left/front',**metadata('socket'))])
            path=root/'receipt.json';path.write_text(json.dumps(report),encoding='utf-8')
            model=module.convert(source,root/'output',ics,path)
            row=model['elements'][0]
            self.assertEqual(row['stage_id'],'wheels');self.assertEqual(row['family_id'],'stacking_sockets')
            self.assertEqual(row['stacking_interface_id'],'caster100/left/front')
            self.assertEqual(row['materials'][0]['color'],0x408080)
            ics.write_bytes(b'different model')
            with self.assertRaisesRegex(ValueError,'ICS binding'):module.convert(source,root/'wrong',ics,path)
