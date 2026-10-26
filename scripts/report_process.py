"""Export an immutable local timing report; never starts CAD or replays a job."""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Integracja'))
from rockpro_cad.process_observer import LIMIT,read_trace,summarize_events


def source_receipts(trace):
    folder=trace.parent.parent if trace.parent.name=='trace' else trace.parent
    paths={trace,folder/'process_preview.json',folder/'native_progress.jsonl'}
    receipts=[]
    for path in sorted(paths):
        if not path.exists():continue
        with path.open('rb') as stream:data=stream.read(LIMIT+1)
        if len(data)>LIMIT:raise ValueError('Trace input exceeds 8 MB')
        receipts.append(dict(path=str(path),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    return receipts


def html_report(summary):
    def text(value):return escape(str(value))
    def ms(value):return 'brak danych' if value is None else f'{value:.2f}'
    stage_rows=''.join('<tr>'+''.join(f'<td>{text(value)}</td>' for value in (
        row['label'],row['state'],row['finished_count'],row['measured_count'],
        ms(row['recorded_work_ms']),ms(row['median_ms']),ms(row['max_ms'])))+'</tr>'
        for row in summary['stages'])
    slow_rows=''.join('<tr>'+''.join(f'<td>{text(value)}</td>' for value in (
        row['operation'],row['occurrence_id'] or '—',row['status'],ms(row['duration_ms']),
        'niepowiązany' if row['evidence_bound'] is False else 'patrz ślad'))+'</tr>'
        for row in summary['slowest_recorded_operations'])
    warnings=''.join(f'<li>{text(w)}</li>' for w in summary['warnings']) or '<li>Brak ostrzeżeń czytnika.</li>'
    return '''<!doctype html><html lang="pl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>RockPro — pomiary procesu</title>
<style>body{font:16px system-ui;background:#f3f6f7;color:#19363c;margin:0}main{max-width:1200px;margin:auto;padding:32px}
h1{color:#24585b}header{border-left:6px solid #e58a3b;padding-left:20px}section{background:white;padding:20px;margin:22px 0;border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border-bottom:1px solid #dce6e8;text-align:left}th{background:#e5efef}
.table{overflow:auto}p{line-height:1.6}.badge{padding:5px 10px;background:#ffe7c9;border-radius:5px}a{color:#24585b}</style><main>
<header><p>ROCKPRO / ANALIZA PROGRAMISTYCZNA</p><h1>Pomiary zarejestrowanego przebiegu</h1>
<span class="badge">Tylko odczyt · bez sterowania CAD</span></header>
<section><p>Okno od pierwszego do ostatniego poprawnego znacznika czasu: <strong>'''+text(ms(summary['observed_window_ms']))+''' ms</strong>.
To zakres zarejestrowanych zdarzeń, nie gwarancja czasu całej operacji.</p>
<p>Wywołania zakończone według wykonawcy: '''+text(json.dumps(summary['finished_by_executor'],ensure_ascii=False))+'''.
Wykonawca skryptu nie identyfikuje autora decyzji. Udział automatyzacji, liczba interwencji, tokeny i koszt modelu: <strong>brak danych</strong>.</p></section>
<section><h2>Etapy</h2><p>Sumy czasów w wierszach mogą się nakładać. W szczególności B · SDK obejmuje podetapy.
Nie dodawaj tych wierszy do czasu łącznego. BŁĄD pozostaje widoczny również po późniejszym sukcesie innego wywołania.</p>
<div class="table"><table><tr><th>Etap</th><th>Stan</th><th>Zakończone</th><th>Z pomiarem</th><th>Suma odcinków [ms]</th><th>Mediana [ms]</th><th>Maks. [ms]</th></tr>'''+stage_rows+'''</table></div></section>
<section><h2>10 najdłuższych zarejestrowanych wywołań</h2><p>Fazy nadrzędne i operacje części to różne poziomy pomiaru.</p>
<div class="table"><table><tr><th>Operacja</th><th>Wystąpienie</th><th>Wynik</th><th>Czas [ms]</th><th>Powiązanie natywne</th></tr>'''+slow_rows+'''</table></div></section>
<section><h2>Jakość danych</h2><ul>'''+warnings+'''</ul><p>Brakujące/błędne znaczniki czasu: '''+text(summary['invalid_timestamp_count'])+'''.
Zakończone wywołania bez poprawnego czasu trwania: '''+text(summary['missing_or_invalid_duration_count'])+'''.
Niepowiązane zdarzenia natywne: '''+text(summary['unbound_native_events'])+'''.</p>
<p>Raport nie zatwierdza geometrii, montażu, nośności ani produkcji. <a href="summary.json">Dane i SHA plików wejściowych</a>.</p></section></main></html>'''


def export_report(trace,destination):
    trace=Path(trace).resolve(strict=True);destination=Path(destination)
    if trace.suffix.lower()!='.jsonl':raise ValueError('A recorded JSONL trace is required')
    before=source_receipts(trace)
    rows,_,warnings=read_trace(trace)
    summary=summarize_events(rows,warnings)
    if source_receipts(trace)!=before:raise ValueError('Trace changed during export; no report was created')
    summary['inputs']=before
    destination.mkdir(parents=True,exist_ok=False)
    (destination/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    (destination/'index.html').write_text(html_report(summary),encoding='utf-8')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();summary=export_report(args.trace,args.destination)
    print(json.dumps(dict(status='PASS',events=summary['event_count'],report=str(args.destination/'index.html'))))


if __name__=='__main__':main()
