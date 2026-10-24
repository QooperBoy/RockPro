import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

import excel_input as excel
import layout
import project_store as store
import server
import worker

EXAMPLES=Path(__file__).resolve().parents[3]/'examples/excel-input'
MAIN='http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def mutate(data,updates=None,formula=None,style=False):
    source=zipfile.ZipFile(io.BytesIO(data));out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            raw=source.read(item.filename)
            if item.filename=='xl/worksheets/sheet1.xml':
                root=ET.fromstring(raw)
                for cell in root.findall('.//{'+MAIN+'}c'):
                    address=cell.get('r')
                    if address in (updates or {}):
                        for child in list(cell):cell.remove(child)
                        v=updates[address]
                        if isinstance(v,str):
                            cell.set('t','inlineStr');node=ET.SubElement(cell,'{'+MAIN+'}is');ET.SubElement(node,'{'+MAIN+'}t').text=v
                        else:
                            cell.set('t','n');ET.SubElement(cell,'{'+MAIN+'}v').text=str(v)
                    if address==formula:ET.SubElement(cell,'{'+MAIN+'}f').text='1+1'
                    if address=='B9' and style:cell.set('s','0')
                raw=ET.tostring(root,encoding='utf-8',xml_declaration=True)
            target.writestr(item.filename,raw)
    return out.getvalue()


class ExcelInputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patches=[patch.object(store,'DB_PATH',self.root/'projects.sqlite3'),patch.object(worker,'ROOT',self.root)]
        for p in self.patches:p.start()
        source=self.root/'source.ics';source.write_bytes(b'test input only')
        self.project=store.save_project('Excel test',source=str(source))['project']['id']
        self.data=mutate((EXAMPLES/'RockPro_poprawny.xlsx').read_bytes(),{'B6':self.project})
        (self.root/'imports').mkdir();self.path=self.root/'imports/config.xlsx';self.path.write_bytes(self.data)

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def import_data(self,data=None,revision=0):
        data=self.data if data is None else data;self.path.write_bytes(data)
        preview=worker.dispatch('preview_excel_configuration',{'path':str(self.path)})
        return worker.dispatch('import_excel_configuration',dict(project_id=self.project,path=str(self.path),expected_revision=revision,expected_source_sha256=preview['source_sha256']))

    def test_examples_good_bad_and_boundary(self):
        for name,valid in [('poprawny',True),('bledny',False),('graniczny',True)]:
            result=excel.parse_workbook((EXAMPLES/f'RockPro_{name}.xlsx').read_bytes())
            self.assertEqual(result['valid'],valid,(name,result))
        result=excel.parse_workbook(mutate(self.data,{'B9':5000.01}))
        self.assertFalse(result['valid']);self.assertEqual(result['errors'][0]['code'],'LAYOUT_INVALID')

    def test_units_are_explicit_and_cell_style_does_not_change_semantics(self):
        base=excel.parse_workbook(self.data)
        for data in [mutate(self.data,style=True),mutate(self.data,{'B9':44,'C9':'cm'}),mutate(self.data,{'B9':.44,'C9':'m'})]:
            result=excel.parse_workbook(data)
            self.assertTrue(result['valid'],result)
            self.assertEqual(result['configuration_sha256'],base['configuration_sha256'])
        bad=excel.parse_workbook(mutate(self.data,{'C9':'in'}))
        self.assertEqual(bad['errors'][0]['cell'],'C9');self.assertEqual(bad['errors'][0]['code'],'UNIT_INVALID')

    def test_invalid_does_not_create_import_or_layout(self):
        result=self.import_data(mutate(self.data,{'B12':0}))
        self.assertFalse(result['imported']);self.assertFalse(layout.get_layout(self.project)['saved'])
        with store.db() as conn:
            self.assertNotIn('excel_import_sources',{r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")})

    def test_source_and_normalized_configuration_are_versioned_without_duplicates(self):
        result=self.import_data();self.assertEqual(result['layout_revision'],1)
        self.assertFalse(result['reused']);self.assertFalse(result['production_approved'])
        repeated=self.import_data();self.assertTrue(repeated['reused'])
        variant=mutate(self.data,{'B7':1},style=True)
        same=self.import_data(variant,1);self.assertTrue(same['reused']);self.assertEqual(same['layout_revision'],1)
        with store.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM layout_versions').fetchone()[0],1)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM excel_import_sources').fetchone()[0],2)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM excel_configurations').fetchone()[0],1)
            blob=conn.execute('SELECT source_xlsx FROM excel_import_sources WHERE source_sha256=?',(result['source_sha256'],)).fetchone()[0]
            self.assertEqual(bytes(blob),self.data)

    def test_cas_conflict_does_not_overwrite_concurrent_layout(self):
        self.import_data();layout.save_layout(self.project,dict(x=900),1)
        with self.assertRaisesRegex(ValueError,'LAYOUT_CONFLICT'):
            self.import_data(mutate(self.data,{'B7':1,'B9':450}),1)
        self.assertEqual(layout.get_layout(self.project)['spec']['x'],900)
        replay=self.import_data();self.assertTrue(replay['historical']);self.assertEqual(replay['current_layout_revision'],2)

    def test_changed_file_and_wrong_project_are_refused(self):
        preview=excel.preview_excel_configuration(self.path)
        self.path.write_bytes(mutate(self.data,{'B9':450}))
        with self.assertRaisesRegex(ValueError,'EXCEL_SOURCE_CHANGED'):
            excel.import_excel_configuration(self.project,self.path,0,preview['source_sha256'])
        with self.assertRaisesRegex(ValueError,'EXCEL_PROJECT_MISMATCH'):
            excel.import_excel_configuration('different',self.path,0,excel.preview_excel_configuration(self.path)['source_sha256'])

    def test_formulas_external_paths_and_xml_entities_are_refused(self):
        bad=excel.parse_workbook(mutate(self.data,formula='B9'))
        self.assertFalse(bad['valid']);self.assertIn('B9',bad['errors'][0]['message'])
        outside=self.root/'outside.xlsx';outside.write_bytes(self.data)
        with self.assertRaisesRegex(ValueError,'imports'):excel.preview_excel_configuration(outside)
        with self.assertRaises(ValueError):excel._xml(b'<!DOCTYPE a [<!ENTITY x "evil">]><a>&x;</a>')

    def test_single_transaction_rolls_back_layout_when_evidence_write_fails(self):
        import sqlite3
        original=layout.save_layout_in_transaction
        def fail(*args,**kwargs):
            original(*args,**kwargs);raise sqlite3.OperationalError('injected disk failure')
        with patch.object(layout,'save_layout_in_transaction',side_effect=fail):
            with self.assertRaisesRegex(sqlite3.OperationalError,'disk failure'):self.import_data()
        self.assertFalse(layout.get_layout(self.project)['saved'])

    def test_mcp_contract_exposes_bounded_operations(self):
        schemas={r['name']:r for r in server.SCHEMAS}
        self.assertTrue(schemas['preview_excel_configuration']['annotations']['readOnlyHint'])
        self.assertIn('expected_source_sha256',schemas['import_excel_configuration']['inputSchema']['required'])
        with self.assertRaisesRegex(ValueError,'argument'):worker.dispatch('import_excel_configuration',{'shell':'anything'})
