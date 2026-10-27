"""Trusted local Studio adapter; HTTP supplies draft identities, never code or paths.

Only the explicitly mapped T1 kit is executable. Catalogue geometry stays opaque.
The child process owns COM and the existing global CAD writer mutex.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
_configured = None


def running_2027_pid():
    """Select one existing 2027 host without launching or activating CAD."""
    from .icapi_runtime import installation_dir
    expected=(installation_dir(2027)/'bin/IRONCAD.exe').resolve()
    powershell=Path(os.environ.get('SystemRoot', 'C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    command="Get-CimInstance Win32_Process -Filter \"Name='IronCAD.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"
    result=subprocess.run([str(powershell),'-NoProfile','-NonInteractive','-Command',command],
                          capture_output=True,text=True,check=True,timeout=15)
    rows=json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(rows,dict):rows=[rows]
    matches=[int(r['ProcessId']) for r in rows if r.get('ExecutablePath')
             and Path(r['ExecutablePath']).resolve()==expected]
    if len(matches)!=1:raise ValueError('Uruchom jedną instancję IronCAD 2027 przed włączeniem połączenia Studio')
    return matches[0]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Adapter:
    def __init__(self, assets, output, expected_pid):
        self.path = Path(assets).resolve(strict=True)
        raw = self.path.read_bytes()
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError('Manifest CAD jest zbyt duży')
        self.manifest = json.loads(raw)
        if self.manifest.get('schema') != 'rockpro.roc46.asset-discovery/1':
            raise ValueError('Nieobsługiwany manifest CAD')
        self.manifest_sha = hashlib.sha256(raw).hexdigest()
        self.output = Path(output).resolve()
        if expected_pid is None:expected_pid=running_2027_pid()
        if type(expected_pid) is not int or expected_pid <= 0:
            raise ValueError('Wymagany PID istniejącego IronCAD 2027')
        self.pid = expected_pid

    def compile(self, record):
        from .studio_native_t1 import compile_t1
        if sha(self.path) != self.manifest_sha:
            raise ValueError('Manifest CAD zmienił się; uruchom ponownie Studio')
        for source in self.manifest['sources'].values():
            if sha(source['path']) != source['sha256']:
                raise ValueError('Źródło CAD nie zgadza się z przypiętą wersją')
        spec = compile_t1(record, self.manifest)
        # Private absolute paths remain in the trusted local configuration.
        for source in spec['sources']:
            source.pop('path', None)
        spec['asset_manifest_sha256'] = self.manifest_sha
        spec['executor_sha256'] = sha(ROOT/'scripts/native/StudioCad2027.cs')
        spec['runner_sha256'] = sha(ROOT/'scripts/run_t1_machining_job.py')
        return spec

    def __call__(self, plan):
        from . import studio_cad
        studio_cad.verify_plan(plan)
        spec = copy.deepcopy(plan['native_spec'])
        for source in spec['sources']:
            trusted = self.manifest['sources'][source['key']]
            if source['sha256'] != trusted['sha256']:
                raise ValueError('Zmieniono źródło wykonawcy')
            source['path'] = trusted['path']
        self.output.mkdir(parents=True, exist_ok=True)
        folder = self.output/('studio-'+plan['plan_id']+'-'+uuid.uuid4().hex[:8])
        request = self.output/(folder.name+'-request.json')
        spec.update(mode='studio-build', expected_pid=self.pid,
                    plan_sha256=plan['plan_sha256'], save_output=True, show_final=True,
                    output_filename='RockPro_Studio_T1.ics')
        with request.open('x', encoding='utf-8') as stream:
            json.dump(spec, stream, ensure_ascii=False, allow_nan=False)
        env = dict(os.environ, ROCKPRO_IRONCAD_YEAR='2027', PYTHONPATH=str(ROOT/'Integracja'))
        # A timeout has unknown native effects. The durable queue blocks retries.
        with (self.output/(folder.name+'-worker.log')).open('x', encoding='utf-8') as log:
            result = subprocess.run([sys.executable, str(ROOT/'scripts/run_t1_machining_job.py'),
                    str(folder), str(ROOT/'scripts/native/StudioCad2027.cs'), str(request)],
                    env=env, cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, timeout=1200)
        receipt = json.loads((folder/'result.json').read_text(encoding='utf-8-sig'))
        if result.returncode or receipt.get('passed') is not True:
            raise RuntimeError('Natywna budowa nie została potwierdzona; raport lokalny: '+str(folder))
        output=Path(receipt['output_path']).resolve(strict=True)
        if (not output.is_relative_to(folder) or output.suffix.lower()!='.ics'
                or sha(output)!=receipt.get('output_sha256')
                or receipt.get('plan_sha256')!=plan['plan_sha256']
                or receipt.get('sources_unchanged') is not True
                or receipt.get('existing_documents_preserved') is not True
                or receipt.get('final_visible') is not True
                or receipt.get('resize',{}).get('status')!='PASS'
                or receipt.get('resize_after_reopen',{}).get('status')!='PASS'
                or len(receipt['baseline']['occurrences'])!=len(spec['panels'])+len(spec['parts'])
                or len(receipt['baseline']['machining'])!=len(spec['cuts'])):
            raise RuntimeError('Niepełny kwit wykonania CAD; wymagana kontrola przed ponowieniem')
        return dict(passed=True, plan_sha256=receipt['plan_sha256'],
                    output_path=receipt['output_path'], output_sha256=receipt['output_sha256'],
                    occurrence_count=len(receipt['baseline']['occurrences']),
                    machining_count=len(receipt['baseline']['machining']),
                    physical_parts=receipt['baseline']['physical_parts'],
                    source_preservation=receipt['sources_unchanged'],
                    existing_documents_preserved=receipt['existing_documents_preserved'],
                    native_report=str(folder/'result.json'))


def configure(assets, output, expected_pid):
    global _configured
    _configured = Adapter(assets, output, expected_pid)
    return _configured


def configured():
    return _configured
