import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import device_catalog as catalog
import project_store as store
import worker


def fixture():
    return dict(schema_version=1,manufacturer='Epson',model='EB-L630U',variant='V11HA26040',
        axes={'X':'width','Y':'depth','Z':'height'},
        sources=[dict(id='page',kind='manufacturer_page',reference='https://example.test/device',locator='Specifications',content_sha256='a'*64)],
        observations=[dict(id=axis,field=axis,value=value,unit='kg' if axis=='mass' else 'mm',source_id='page',confirmation='source_checked')
                      for axis,value in [('X',440),('Y',339),('Z',136),('mass',8.4)]])


class DeviceCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patch=patch.object(store,'DB_PATH',self.root/'projects.sqlite3');self.patch.start()
    def tearDown(self):self.patch.stop();self.temp.cleanup()

    def test_units_sources_and_explicit_axis_identity(self):
        record=fixture();record['observations'][0].update(value=44,unit='cm')
        result=worker.dispatch('preview_device_record',{'record':record})
        self.assertEqual(result['fields']['X']['value'],440)
        self.assertEqual(result['fields']['X']['observations'][0]['source_id'],'page')
        self.assertEqual(result['fields']['mass']['unit'],'kg');self.assertTrue(result['dimensions_ready'])
        self.assertFalse(result['production_approved'])
        record['axes']['Y']='height'
        with self.assertRaisesRegex(ValueError,'mapping'):catalog.preview_device_record(record)

    def test_variant_names_are_never_fuzzily_merged(self):
        one=catalog.save_device_record(fixture(),0)
        other=fixture();other['variant']='V11HA26041'
        two=catalog.save_device_record(other,0)
        self.assertNotEqual(one['catalog_id'],two['catalog_id']);self.assertEqual(two['revision'],1)

    def test_missing_and_conflicting_dimensions_never_become_facts(self):
        record=fixture();record['observations']=[r for r in record['observations'] if r['field']!='Z']
        record['observations'].append(dict(id='X-mail',field='X',value=450,unit='mm',source_id='page',confirmation='unconfirmed'))
        result=catalog.preview_device_record(record)
        self.assertIsNone(result['fields']['Z']['value']);self.assertEqual(result['missing_fields'],['Z'])
        self.assertIsNone(result['fields']['X']['value']);self.assertEqual(result['conflicting_fields'],['X'])
        self.assertFalse(result['dimensions_ready'])
        draft=catalog.draft_device_inquiry(record)
        self.assertIn('Z',draft['draft']);self.assertIn('X',draft['draft']);self.assertFalse(draft['sent'])

    def test_versioning_cas_and_old_source_observations_are_preserved(self):
        first=catalog.save_device_record(fixture(),0)
        self.assertTrue(catalog.save_device_record(fixture(),0)['reused'])
        changed=fixture();changed['observations'][-1]['confirmation']='constructor_confirmed'
        with self.assertRaisesRegex(ValueError,'DEVICE_REVISION_CONFLICT'):catalog.save_device_record(changed,0)
        second=catalog.save_device_record(changed,1);self.assertEqual(second['revision'],2)
        old=catalog.get_device_record(first['catalog_id'],1)
        self.assertEqual(old['record']['observations'][-1]['confirmation'],'source_checked')
        self.assertEqual(catalog.get_device_record(first['catalog_id'])['revision'],2)
        reverted=catalog.save_device_record(fixture(),2);self.assertEqual(reverted['revision'],3)

    def test_wrong_units_duplicate_ids_and_confirmed_missing_values_refuse(self):
        cases=[]
        one=fixture();one['observations'][0]['unit']='inch';cases.append(one)
        one=fixture();one['observations'].append(copy.deepcopy(one['observations'][0]));cases.append(one)
        one=fixture();one['observations'][0]['value']=None;cases.append(one)
        one=fixture();one['observations'][0]['value']=True;cases.append(one)
        one=fixture();one['observations'][0]['source_id']='missing';cases.append(one)
        for case in cases:
            with self.assertRaises(ValueError):catalog.preview_device_record(case)
