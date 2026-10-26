import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from report_process import export_report,html_report


class ProcessReportTests(unittest.TestCase):
    def test_export_preserves_sources_and_existing_report_and_escapes_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);trace=root/'run.jsonl';target=root/'report'
            row=dict(event='operation_finished',operation='<script>bad()</script>',
                     timestamp_utc='2026-10-26T10:00:01Z',actor='script',duration_ms=12,result={'status':'passed'})
            trace.write_text(json.dumps(row)+'\n',encoding='utf-8')
            before=trace.read_bytes();result=export_report(trace,target)
            self.assertEqual(result['inputs'][0]['sha256'],hashlib.sha256(before).hexdigest())
            self.assertEqual(trace.read_bytes(),before)
            html=(target/'index.html').read_text(encoding='utf-8')
            self.assertNotIn('<script>bad()',html);self.assertIn('&lt;script&gt;',html)
            self.assertEqual(result['event_count'],1);self.assertIsNone(result['automation_percent'])
            with self.assertRaises(FileExistsError):export_report(trace,target)
            self.assertEqual((target/'index.html').read_text(encoding='utf-8'),html)

    def test_changed_input_during_export_does_not_create_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);trace=root/'run.jsonl';trace.write_bytes(b'{}\n')
            with patch('report_process.source_receipts',side_effect=[[{'sha256':'a'}],[{'sha256':'b'}]]):
                with self.assertRaisesRegex(ValueError,'changed'):export_report(trace,root/'report')
            self.assertFalse((root/'report').exists())


if __name__=='__main__':unittest.main()
