import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rockpro_cad import source_parts,studio_parts,configurator
from rockpro_cad.mcp.test_configurator import concept

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('source_parts_import',ROOT/'scripts/import_studio_source_parts.py')
importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)


class SourcePartsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.bundle=self.root/'bundle';(self.bundle/'native-02').mkdir(parents=True)
        (self.bundle/'manifest.json').write_text(json.dumps(dict(models=[dict(key='M03',sha256='a'*64)])),encoding='utf-8')
        folder=self.root/'preview/M03';folder.mkdir(parents=True)
        matrix=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
        rows=[dict(id=1,path='root/1',name='H7165/10Z',type='Z_ELEMENT_ASSEMBLY'),dict(id=2,path='root/1/2',name='geometry',type='Z_ELEMENT_PART'),
              dict(id=3,path='root/3',name='27083_1',type='Z_ELEMENT_ASSEMBLY'),dict(id=4,path='root/3/4',name='geometry',type='Z_ELEMENT_PART')]
        inv=dict(source_sha256='a'*64,rows=rows);path=self.bundle/'native-02/M03-inventory.json';path.write_text(json.dumps(inv),encoding='utf-8')
        geometry=b'\0'*144;(folder/'geometry.bin').write_bytes(geometry)
        model=dict(source_sha256='a'*64,inventory_sha256=importer.sha(path),geometry_sha256=importer.sha(folder/'geometry.bin'),elements=[
            dict(node_id=i,path=p,name='geometry',offset=o,floats=9,matrix=matrix,materials=[dict(count=3,color=16777215)],bounds=[0,0,0,.1,.1,.1])
            for i,p,o in [(2,'root/1/2',0),(4,'root/3/4',72)]])
        (folder/'model.json').write_text(json.dumps(model),encoding='utf-8')
        self.index=self.root/'preview/index.json';self.index.write_text(json.dumps(dict(models={'M03':'M03'})),encoding='utf-8')
        self.survey=self.root/'survey.json';self.survey.write_text(json.dumps(dict(passed=True,context_preserved=True,documents=[dict(disk_unchanged=True,rows=rows)])),encoding='utf-8')
        self.out=self.root/'out'

    def extract(self):
        importer.extract(self.bundle,self.index,self.survey,self.out)
        return source_parts.load(self.out/'catalog.json')

    def test_source_binding_geometry_and_flags_are_preserved_without_sku_approval(self):
        data=self.extract();self.assertEqual(len(data['items']),2)
        self.assertEqual(data['report']['source_codes_without_saved_geometry'],[])
        for row in data['items']:
            self.assertIsNone(row['sku']);self.assertFalse(row['production_approved']);self.assertFalse(row['automatic_placement_approved'])
            self.assertEqual(row['mounting_status'],'unknown');self.assertEqual(row['source_binding']['source_sha256'],'a'*64)
            model=json.loads((self.out/'models'/row['id']/'model.json').read_text())
            self.assertEqual(importer.sha(self.out/'models'/row['id']/'geometry.bin'),model['geometry_sha256'])

    def test_source_candidates_place_but_components_cannot_become_joint_hinges(self):
        data=self.extract()
        with patch.object(source_parts,'catalog',return_value=copy.deepcopy(data)):
            rows=studio_parts.catalog()['items'];self.assertGreater(len(rows),14)
            handle=next(r for r in rows if r.get('catalog_code_raw')=='H7165/10Z')
            d=concept();d['hardware']=[dict(part_id=handle['id'],revision=1)]
            d['placements']=[dict(id='h',part_id=handle['id'],revision=1,section_id='body',face='left',u=.5,v=.5,rotation_deg=0,pattern='symmetric',count_per_wall=4,handles_per_wall=4,opposite_wall=True,spread=.5)]
            self.assertEqual(configurator.preview(d)['placement']['instance_count'],8)
            hinge=next(r for r in rows if r.get('catalog_code_raw')=='27083_1')
            d['hardware']=[dict(part_id=hinge['id'],revision=1)]
            d['placements']=[dict(id='j',part_id=hinge['id'],revision=1,pattern='joint_line',joint_id='joint-lid-a',hinge_count=2,edge_inset_mm=80)]
            with self.assertRaises(ValueError):configurator.preview(d)

    def test_modified_dataset_failed_survey_and_false_approval_are_refused(self):
        data=self.extract();row=data['items'][0];row['production_approved']=True;row['definition_sha256']=source_parts.digest({k:v for k,v in row.items()if k!='definition_sha256'})
        path=self.out/'catalog.json';path.write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'approve'):source_parts.load(path)
        (self.root/'preview/M03/geometry.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):importer.extract(self.bundle,self.index,self.survey,self.root/'changed')
        self.survey.write_text(json.dumps(dict(passed=False)),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'survey'):importer.extract(self.bundle,self.index,self.survey,self.root/'bad')


if __name__=='__main__':unittest.main()
