import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import worker
import device_catalog as catalog
import device_layout_service as service
import layout
import project_store as store
from test_device_catalog import fixture


class BoundDeviceLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patches=[patch.object(worker,'ROOT',self.root),patch.object(store,'DB_PATH',self.root/'db.sqlite3')]
        for p in self.patches:p.start()
        source=self.root/'source.ics';source.write_bytes(b'synthetic only')
        self.project=store.save_project('Source layout QA',source=str(source))['project']['id']
        self.device=catalog.save_device_record(fixture(),0)
        self.constraints=dict(allowed_orientations=['XYZ','YXZ'],allowed_arrangements=['X','Y'],removal_clearance_mm=10,max_external_mm=None)
        self.base=dict(count=1,clearance=20,lid_height=25,lid_hinge_height=0,lid_constructor_override=False)
        self.proposals=worker.dispatch('preview_catalog_layouts',dict(catalog_id=self.device['catalog_id'],spec=self.base,constraints=self.constraints))
        self.spec=self.proposals['variants'][0]['layout']['spec'];self.binding=self.proposals['device_binding']

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def save(self,spec=None,expected=0,binding=None):
        return worker.dispatch('save_bound_device_layout',dict(project_id=self.project,spec=self.spec if spec is None else spec,
            binding=self.binding if binding is None else binding,expected_revision=expected))

    def change_device(self):
        record=fixture();record['observations'][0]['value']=450
        return catalog.save_device_record(record,1)

    def test_saved_layout_retains_source_and_only_allowed_removable_ranking(self):
        saved=self.save();read=layout.get_layout(self.project)
        self.assertEqual(read['device_binding'],self.binding);self.assertEqual(read['device_source_status'],'current')
        self.assertEqual(read['device_source_info']['identity']['model'],'EB-L630U')
        self.assertFalse(saved['production_approved']);self.assertTrue(saved['removal_check']['passed'])
        self.assertEqual(len(saved['ranking']['variants']),4)
        self.assertEqual({r['key'] for r in saved['ranking']['orientations']},{'XYZ','YXZ'})

    def test_source_revision_change_blocks_old_proposal_and_invalidates_downstream(self):
        self.save();changed=self.change_device()
        self.assertEqual(changed['invalidated_projects'],[self.project])
        read=layout.get_layout(self.project);self.assertEqual(read['device_source_status'],'stale')
        self.assertEqual(read['device_binding']['device_revision'],1)
        with self.assertRaisesRegex(ValueError,'DEVICE_REVISION_CONFLICT'):self.save(expected=1)
        with self.assertRaisesRegex(ValueError,'DEVICE_REVISION_CONFLICT'):service.preview_bound_device_layout(self.binding,self.spec)
        card=store.get_project(self.project)['project']
        self.assertEqual({s['status'] for s in card['stages'] if s['key'] in ('devices','layout','production')},{'outdated'})
        self.assertEqual(layout.get_layout(self.project)['revision'],1)

    def test_layout_cas_and_source_binding_write_roll_back_together(self):
        layout.save_layout(self.project,dict(x=400),0)
        with self.assertRaisesRegex(ValueError,'LAYOUT_CONFLICT'):self.save(expected=0)
        read=layout.get_layout(self.project);self.assertIsNone(read['device_binding']);self.assertEqual(read['revision'],1)
        self.save(expected=1)
        with self.assertRaisesRegex(ValueError,'LAYOUT_CONFLICT'):self.save(expected=1)
        self.assertEqual(layout.get_layout(self.project)['revision'],2)

    def test_manual_dimensions_and_plain_save_require_explicit_unlink(self):
        self.save()
        with self.assertRaisesRegex(ValueError,'DIMENSION_OVERRIDE'):self.save(self.spec|dict(x=999),1)
        with self.assertRaisesRegex(ValueError,'DEVICE_LAYOUT_BOUND'):layout.save_layout(self.project,self.spec|dict(x=999),1)
        unlinked=worker.dispatch('unlink_layout_device',dict(project_id=self.project,expected_revision=1))
        self.assertIsNone(unlinked['device_binding']);self.assertEqual(unlinked['revision'],2)
        layout.save_layout(self.project,self.spec|dict(x=999),2)
        self.assertEqual(layout.get_layout(self.project)['spec']['x'],999)
        self.assertEqual(layout.get_layout(self.project,1)['device_binding'],self.binding)

    def test_disallowed_choice_and_access_limit_do_not_write(self):
        with self.assertRaisesRegex(ValueError,'CHOICE_NOT_ALLOWED'):self.save(self.spec|dict(orientation='ZYX'))
        binding=copy.deepcopy(self.binding);binding['constraints']['removal_clearance_mm']=25
        with self.assertRaisesRegex(ValueError,'LAYOUT_REJECTED'):self.save(binding=binding)
        self.assertFalse(layout.get_layout(self.project)['saved'])

    def test_unconfirmed_dimensions_remain_draft_blockers(self):
        record=fixture();record['observations'][0]['confirmation']='unconfirmed';catalog.save_device_record(record,1)
        proposals=service.preview_catalog_layouts(self.device['catalog_id'],self.base,self.constraints)
        saved=self.save(spec=proposals['variants'][0]['layout']['spec'],binding=proposals['device_binding'])
        self.assertIn('DEVICE_DIMENSIONS_UNCONFIRMED',saved['release_blockers']);self.assertFalse(saved['production_approved'])

    def test_stale_source_never_starts_cad_or_prepares_a_case(self):
        saved=self.save();self.change_device()
        with patch.object(worker,'_change_dimensions_on_copy') as execute:
            with self.assertRaisesRegex(ValueError,'DEVICE_REVISION_CONFLICT'):
                worker.change_dimensions_on_copy(saved['parameters'],project_id=self.project,layout_revision=1)
            execute.assert_not_called()
        import core_service
        with self.assertRaisesRegex(ValueError,'DEVICE_REVISION_CONFLICT'):core_service.prepare_case_request(self.project,1)

    def test_source_change_during_cad_preserves_unregistered_copy_and_its_provenance(self):
        saved=self.save();copy_path=self.root/'retained/case.ics';copy_path.parent.mkdir()
        def native(changes,source):
            copy_path.write_bytes(b'synthetic CAD result');self.change_device();return dict(copy=str(copy_path),passed=True)
        with patch.object(worker,'_change_dimensions_on_copy',side_effect=native),patch.object(store,'register_snapshot') as register:
            with self.assertRaisesRegex(ValueError,'unregistered copy retained'):
                worker.change_dimensions_on_copy(saved['parameters'],project_id=self.project,layout_revision=1)
            register.assert_not_called()
        report=json.loads((copy_path.parent/'report.json').read_text(encoding='utf-8'))
        self.assertTrue(report['device_source_outdated']);self.assertEqual(report['layout_binding']['device_binding'],self.binding)
        self.assertTrue(copy_path.is_file())

    def test_catalog_pages_current_variants_without_merging_versions(self):
        other=fixture();other['variant']='other';catalog.save_device_record(other,0);self.change_device()
        first=worker.dispatch('list_device_records',{'limit':1});second=catalog.list_device_records(limit=1,after_catalog_id=first['next_cursor'])
        self.assertTrue(first['has_more']);self.assertFalse(second['has_more'])
        records=first['devices']+second['devices'];self.assertEqual(len({r['catalog_id'] for r in records}),2)
        self.assertEqual([r['revision'] for r in records if r['catalog_id']==self.device['catalog_id']],[2])

    def test_catalog_preview_does_not_silently_replace_the_selected_source_revision(self):
        request=dict(catalog_id=self.device['catalog_id'],spec=self.base,
                     constraints=self.constraints,expected_device_revision=1)
        result=worker.dispatch('preview_catalog_layouts',request)
        self.assertEqual(result['device_binding']['device_revision'],1)
        self.change_device()
        with self.assertRaisesRegex(ValueError,'DEVICE_REVISION_CONFLICT'):
            worker.dispatch('preview_catalog_layouts',request)
        self.assertFalse(layout.get_layout(self.project)['saved'])
        request['expected_device_revision']=2
        updated=worker.dispatch('preview_catalog_layouts',request)
        self.assertEqual(updated['device_binding']['device_revision'],2)
        self.assertNotEqual(updated['device_binding']['record_sha256'],result['device_binding']['record_sha256'])


if __name__=='__main__':unittest.main()
