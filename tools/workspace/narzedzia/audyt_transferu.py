"""Read-only validation of the imported RockPro transfer."""
import csv
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSFER = ROOT / 'Transfer_RockPro_20261024'
REPORTS = ROOT / 'raporty'
REPORTS.mkdir(exist_ok=True)

verified = 0
failures = []
with (TRANSFER / 'PLIKI.csv').open(encoding='utf-8-sig', newline='') as stream:
    for row in csv.DictReader(stream):
        path = (TRANSFER / row['sciezka'].replace('\\', '/')).resolve()
        if not path.is_relative_to(TRANSFER.resolve()):
            failures.append({'file': row['sciezka'], 'error': 'outside transfer'})
            continue
        if not path.is_file():
            failures.append({'file': row['sciezka'], 'error': 'missing'})
            continue
        with path.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        if path.stat().st_size != int(row['bajty']) or digest.lower() != row['sha256'].lower():
            failures.append({'file': row['sciezka'], 'error': 'size or hash mismatch'})
        else:
            verified += 1

databases = []
for name in (TRANSFER / 'BAZY_SQLITE.txt').read_text(encoding='utf-8-sig').splitlines():
    if not name.strip():
        continue
    path = TRANSFER / name.replace('\\', '/')
    item = {'file': name, 'exists': path.is_file()}
    if path.is_file():
        try:
            connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
            try:
                item['quick_check'] = [r[0] for r in connection.execute('PRAGMA quick_check')]
                item['tables'] = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                stale = []
                for table in item['tables']:
                    quoted = '"' + table.replace('"', '""') + '"'
                    count = 0
                    for record in connection.execute('SELECT * FROM ' + quoted):
                        if any(isinstance(v, str) and ('C:\\Ai\\' in v or 'C:/Ai/' in v or 'C:\\Users\\Qoope' in v) for v in record):
                            count += 1
                    if count:
                        stale.append({'table': table, 'rows_with_old_paths': count})
                item['old_path_references'] = stale
            finally:
                connection.close()
        except sqlite3.Error as exc:
            item['error'] = str(exc)
    databases.append(item)

sqlite_ok = all(d.get('quick_check') == ['ok'] for d in databases)
result = {'status': 'PASS' if not failures and sqlite_ok else 'FAIL', 'verified_files': verified,
          'failures': failures, 'databases': databases,
          'note': 'Read-only SQLite checks. Historical paths were not migrated. CAD was not started.'}
(REPORTS / 'transfer_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': result['status'], 'verified_files': verified, 'failures': len(failures),
                  'databases': len(databases), 'sqlite_ok': sum(d.get('quick_check') == ['ok'] for d in databases)}, ensure_ascii=True))
raise SystemExit(0 if result['status'] == 'PASS' else 1)
