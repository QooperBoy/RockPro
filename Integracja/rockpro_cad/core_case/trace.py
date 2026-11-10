"""Sequential phase evidence using the existing bounded metadata logger.

Geometry is an explicit separate local preview contract, never logger metadata.
The observer cannot invoke CAD. Executor identity is not decision authorship.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import time
from ..parts.operation_log import OperationLogger


class PhaseTrace:
    def __init__(self, directory, parts, operation_id):
        directory=Path(directory)
        preview=dict(schema_version=1, kind='rockpro_process_preview', units='mm',
                     operation_id=operation_id, decision_origin=None,
                     scope='planned synthetic bounds; not validated CAD',
                     elements=[dict(id=p['id'], family=p['family'], bounds=p['expected_bbox_world_mm']) for p in parts])
        data=json.dumps(preview,ensure_ascii=False,allow_nan=False).encode('utf-8')
        with (directory/'process_preview.json').open('xb') as f: f.write(data)
        self.digest=hashlib.sha256(data).hexdigest()
        self.logger=OperationLogger(directory/'trace',actor='script')

    @contextmanager
    def phase(self, stage):
        operation='case.'+stage
        self.logger.record('operation_started',operation=operation,refs={'inventory_sha256':self.digest})
        start=time.perf_counter()
        try:
            yield
        except BaseException as exc:
            self.logger.record('operation_finished',operation=operation,
                               result={'status':'failed'},error=exc,
                               duration_ms=(time.perf_counter()-start)*1000)
            raise
        else:
            self.logger.record('operation_finished',operation=operation,
                               result={'status':'passed'},duration_ms=(time.perf_counter()-start)*1000)
