"""OOXML reader fixtures are XML fragments, not authored Excel workbooks."""
import io
import unittest
import zipfile
from import_company_workbook import first_rows,cell_images,column_number


class WorkbookReaderTests(unittest.TestCase):
    def archive(self,files):
        memory=io.BytesIO()
        with zipfile.ZipFile(memory,'w') as z:
            for name,text in files.items():z.writestr(name,text)
        memory.seek(0);self.addCleanup(memory.close);z=zipfile.ZipFile(memory);self.addCleanup(z.close);return z
    def test_blank_zero_fraction_and_shared_formula_are_distinct(self):
        xml='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="5"><c r="B5" t="s"><v>0</v></c><c r="C5" t="inlineStr"><is><t>0175</t></is></c></row><row r="10"><c r="B10"><f>1-1</f><v>0</v></c><c r="C10"><f t="shared" si="1"/><v>1.25</v></c><c r="D10"/></row><row r="13"><c r="B13"><v>999</v></c></row></sheetData></worksheet>'
        rows=first_rows(self.archive({'sheet.xml':xml}),'sheet.xml',12,['PN - 0001'])
        self.assertEqual(rows['B5']['value'],'PN - 0001');self.assertEqual(rows['C5']['value'],'0175')
        self.assertEqual(rows['B10']['value'],'0');self.assertEqual(rows['C10']['value'],'1.25')
        self.assertTrue(rows['C10']['formula_present']);self.assertIsNone(rows['D10']['value'])
        self.assertNotIn('B13',rows)
    def test_missing_rich_images_does_not_invent_thumbnails(self):
        self.assertEqual(cell_images(self.archive({})),{})
    def test_column_numbers_are_numeric_not_lexical(self):
        self.assertLess(column_number('Z'),column_number('AA'))
        self.assertLess(column_number('JE'),column_number('JF'))


if __name__=='__main__':unittest.main()
