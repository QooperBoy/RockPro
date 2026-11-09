import json
from pathlib import Path
root=Path('artifacts/core-native').resolve()
(root/'sdk/lifecycle-audit-request.json').write_text(json.dumps({'action':'audit','source':str(root/'native-A-20261021-02/case_prototype.ics'),'directory':str(root/'user-save-all-20261021')}),encoding='utf-8')
