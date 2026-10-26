import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from survey_model_bundle import prepare, safe_member_name
from stage_verified_bundle import stage
from summarize_model_bundle import summarize,world_box,build


class BundleTests(unittest.TestCase):
    def test_source_changes_rejected_and_original_can_be_staged_without_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source';source.mkdir();(source/'model.ics').write_bytes(b'original')
            archive=root/'models.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('model.ics',b'original')
            prepare(source,archive,root/'first')
            (source/'model.ics').write_bytes(b'user edit')
            with self.assertRaisesRegex(ValueError,'do not match'):prepare(source,archive,root/'second')
            stage(root/'first/manifest.json',root/'pristine')
            self.assertEqual((root/'pristine/model.ics').read_bytes(),b'original')
            self.assertEqual((source/'model.ics').read_bytes(),b'user edit')
            with self.assertRaises(FileExistsError):stage(root/'first/manifest.json',root/'pristine')

    def test_same_named_assembly_and_solid_are_not_two_catalog_occurrences(self):
        def node(i,name,path,kind):return {'id':i,'name':name,'path':path,'type':kind}
        rows=[node(1,'','root','Z_ELEMENT_UNKNOWN'),node(2,'H1234','root/2','Z_ELEMENT_ASSEMBLY'),
              node(3,'H1234','root/2/3','Z_ELEMENT_PART'),node(4,'H1234','root/4','Z_ELEMENT_PART')]
        r=summarize({'rows':rows,'errors':[],'source':'x','source_sha256':'a','api_version':'25'},'M01',set())
        c=r['catalog_candidates'][0]
        self.assertEqual(c['occurrences'],2)
        self.assertEqual(c['requires_plywood_cutout'],'unknown')
        self.assertFalse(r['executable_template'])
        self.assertFalse(r['history_complete'])
        for row in rows:
            if row['type']=='Z_ELEMENT_PART':row['features']=[]
        complete=summarize({'rows':rows,'errors':[],'source':'x','source_sha256':'a','api_version':'25'},'M01',set())
        self.assertTrue(complete['history_complete'])

    def test_world_bounds_respect_translation_and_reflection(self):
        row={'bounds_local_m':[0,0,0,.1,.2,.01],
             'world_mm':[[-1,0,0,0],[0,1,0,0],[0,0,1,0],[500,20,30,1]]}
        self.assertEqual(world_box(row),[400,20,30,500,220,40])

    def test_invalid_world_matrix_is_missing_evidence_not_a_valid_box(self):
        row={'bounds_local_m':[0,0,0,.1,.2,.01],
             'world_mm':[[1,0,0,0],[0,1,0,0],[0,0,1,0],[500,20,30,1]]}
        for bad in ([], [[1,0,0]], [[True,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]):
            with self.subTest(matrix=bad):
                changed=copy.deepcopy(row);changed['world_mm']=bad
                self.assertIsNone(world_box(changed))
        row['world_mm'][0][3]=1
        self.assertIsNone(world_box(row))

    def test_windows_aliases_and_incomplete_manifests_refused_before_staging(self):
        for name in ('../a.ics','/a.ics','C:/a.ics','a.ics:stream','a.ics.','NUL.ics','x\\a.ics','x/./a.ics'):
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'Unsafe'):
                safe_member_name(name)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=root/'models.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('model.ics',b'a');z.writestr('second.ics',b'b')
            manifest={'contract':'rockpro-model-survey-v1','archive_matches_extracted':True,
                      'archive':str(archive),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
                      'files':{'model.ics':{'bytes':1,'sha256':hashlib.sha256(b'a').hexdigest()}}}
            path=root/'manifest.json';path.write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'every archive member'):stage(path,root/'out')
            self.assertFalse((root/'out').exists())
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('model.ics',b'a');z.writestr('MODEL.ICS',b'a')
            manifest['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
            path.write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'aliased'):stage(path,root/'alias')
            self.assertFalse((root/'alias').exists())

    def test_empty_native_read_writes_no_parts_without_claiming_a_case_envelope(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);native=root/'native';native.mkdir()
            manifest={'models':[{'key':'M01','sha256':'a'*64,'name':'source.ics'}]}
            (root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            data={'source':'source.ics','source_sha256':'a'*64,'api_version':'29',
                  'rows':[],'errors':[]}
            (native/'M01-inventory.json').write_text(json.dumps(data),encoding='utf-8')
            report=build(root/'manifest.json',native,root/'report',[])
            self.assertEqual(report['parts_total'],0)
            self.assertFalse(report['models'][0]['history_complete'])
            self.assertIsNone(report['models'][0]['scene_envelope_conservative_mm'])
            self.assertEqual(len((root/'report/czesci.csv').read_text(encoding='utf-8-sig').splitlines()),1)


if __name__=='__main__':unittest.main()
