import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from survey_model_bundle import prepare
from stage_verified_bundle import stage
from summarize_model_bundle import summarize,world_box


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

    def test_world_bounds_respect_translation_and_reflection(self):
        row={'bounds_local_m':[0,0,0,.1,.2,.01],
             'world_mm':[[-1,0,0,0],[0,1,0,0],[0,0,1,0],[500,20,30,1]]}
        self.assertEqual(world_box(row),[400,20,30,500,220,40])


if __name__=='__main__':unittest.main()
