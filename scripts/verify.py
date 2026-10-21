"""Local verification runner; subprocess exit status is authoritative, not log wording."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from repo_audit import ROOT


def run_check(name,command,folder,steps,cwd=ROOT):
    try:
        run=subprocess.run([str(a) for a in command],cwd=cwd,capture_output=True,
                           text=True,encoding='utf-8',errors='replace',timeout=240)
        code=run.returncode;log=run.stdout+'\n'+run.stderr
    except (OSError,subprocess.TimeoutExpired) as exc:
        code=1;log=str(exc)
    (folder/(name+'.log')).write_text(log,encoding='utf-8')
    steps.append(dict(name=name,status='PASS' if code==0 else 'FAIL',exit_code=code))
    print(name,steps[-1]['status'],flush=True)
    return code==0


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build',action='store_true');parser.add_argument('--ui',action='store_true');args=parser.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=ROOT/'artifacts'/'verification'/stamp;folder.mkdir(parents=True)
    steps=[];py=sys.executable;source=ROOT/'Integracja'/'rockpro_cad'
    jobs=[('repository',[py,ROOT/'scripts/repo_audit.py','--output',folder/'repository.json']),
          ('backend',[py,'-m','unittest','discover','-s',source/'mcp','-p','test_*.py','-v']),
          ('qa',[py,'-m','unittest','discover','-s',source/'qa','-p','test_acceptance.py','-v']),
          ('harness',[py,'-m','unittest','discover','-s',ROOT/'scripts','-p','test_verification.py','-v'])]
    if args.build or args.ui:
        binary='bin-verify-'+stamp
        jobs.append(('addin-build',['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',source/'addin/Build.ps1','-OutputFolder',binary]))
        if args.ui:
            exe=source/'addin'/binary/'LayoutUiChecks.exe'
            jobs.extend([
                ('ui-check-build',[r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
                 '/nologo','/target:exe','/platform:x64','/out:'+str(exe),
                 r'/reference:C:\Program Files\IronCAD\2027\ICAPI\Samples\C#\References\interop.ICApiIronCAD.dll',
                 r'/reference:C:\Program Files (x86)\Microsoft.NET\Primary Interop Assemblies\stdole.dll',
                 '/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll','/reference:System.Web.Extensions.dll',
                 source/'addin/RockProAddin.cs',source/'addin/RockProPanel.cs',source/'addin/LayoutForm.cs',source/'qa/LayoutUiChecks.cs']),
                ('ui-checks',[exe])])
    passed=True
    for name,command in jobs:
        if not run_check(name,command,folder,steps):
            passed=False;break
    done={s['name'] for s in steps}
    steps.extend(dict(name=n,status='NOT RUN',reason='Earlier check failed') for n,_ in jobs if n not in done)
    steps.append(dict(name='native-ironcad',status='NOT RUN',reason='Harness does not operate the host or change CAD.'))
    (folder/'results.json').write_text(json.dumps(dict(passed=passed,steps=steps),indent=2),encoding='utf-8')
    print('Evidence:',str(folder).encode('ascii','backslashreplace').decode('ascii'))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
