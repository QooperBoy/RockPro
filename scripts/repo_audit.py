"""Read-only repository structure checks. No CAD/DB imports or network access."""
import argparse
import ast
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'AGENTS.md', 'docs/DEVELOPMENT.md', 'docs/AI_SOURCES.md',
    '.github/copilot-instructions.md',
    '.github/instructions/winforms.instructions.md',
    '.github/instructions/backend.instructions.md', '.github/instructions/cad.instructions.md',
    '.github/prompts/rockpro-next-slice.prompt.md',
    '.github/prompts/rockpro-return-to-quality.prompt.md', '.github/prompts/rockpro-review.prompt.md',
    '.agents/skills/rockpro-scope-check/SKILL.md',
    '.agents/skills/rockpro-verification/SKILL.md',
    '.agents/skills/bug-reproduction-brief/SKILL.md',
]


def audit(root=ROOT):
    run = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                         cwd=root, check=True, capture_output=True)
    names = sorted(set(run.stdout.decode('utf-8').rstrip('\0').split('\0')))
    errors, inventory, notes = [], [], []
    for name in REQUIRED:
        if not (root/name).is_file(): errors.append('Missing instruction/workflow file: '+name)
    for name in names:
        path = root/name
        if not path.is_file():
            errors.append('Missing tracked file: '+name)
            continue
        data = path.read_bytes()
        row = dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        if path.suffix.lower() in ('.dll', '.exe', '.sqlite', '.sqlite3', '.db') or any(
                p in ('.venv', 'data', 'logs', 'revisions', 'session_backups') for p in Path(name).parts):
            errors.append('Generated/runtime data included in Git candidates: '+name)
        if path.name in ('mcp-config.local.json', 'skeleton_state.json', '.env'):
            errors.append('Local configuration included in Git candidates: '+name)
        if path.suffix.lower() in ('.md', '.py', '.cs', '.ps1', '.json', '.txt', '.yml', '.yaml'):
            try: text=data.decode('utf-8-sig')
            except UnicodeDecodeError:
                errors.append('Expected UTF-8 text: '+name);inventory.append(row);continue
            row['lines']=len(text.splitlines())
            if path.suffix=='.py':
                try: ast.parse(text, filename=name)
                except SyntaxError as exc: errors.append(f'Python syntax: {name}:{exc.lineno}')
            if path.suffix=='.md':
                for target in re.findall(r'(?<!!)\[[^\]\n]+\]\(([^)]+)\)', text):
                    target=target.strip().strip('<>')
                    if not target or target.startswith(('#','http:','https:','mailto:')): continue
                    target=unquote(target.split('#',1)[0])
                    if not (path.parent/target).exists(): errors.append(f'Broken relative link: {name} -> {target}')
                if path.name=='SKILL.md':
                    match=re.match(r'^---\s*\n(.*?)\n---',text,re.S)
                    if not match or not all(re.search(r'^'+k+r':\s*\S',match[1],re.M) for k in ('name','description')):
                        errors.append('Missing skill metadata: '+name)
                if path.name.endswith('.instructions.md') and not re.search(r'^applyTo:\s*\S',text,re.M):
                    errors.append('Missing applyTo: '+name)
            if path.suffix=='.cs' and any(len(line)>500 for line in text.splitlines()):
                notes.append('Long C# lines; consider a separate readability increment: '+name)
        inventory.append(row)
    return dict(time=datetime.now(timezone.utc).isoformat(),
                policy_passed=not errors, errors=errors, notes=notes, files=inventory,
                scope='Repository structure, relative links, Python syntax and generated-file exclusions; not a security or native CAD audit')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    report=audit()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(policy_passed=report['policy_passed'],files=len(report['files']),
                          errors=report['errors'],notes=report['notes']),ensure_ascii=True))
    raise SystemExit(0 if report['policy_passed'] else 1)
