"""Build a private read-only review packet from explicitly pinned family drafts.

This does not open CAD, infer roles, approve manufacturing or create a BOM.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Integracja'))
from rockpro_cad.core_case.working_mounts import build_working_standard

LIMIT = 32 * 1024 * 1024
KEY = re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
QUESTION = re.compile(r'Q[0-9]{2}\Z')


def read_bytes(path):
    with Path(path).open('rb') as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('Review input exceeds 32 MiB limit')
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def question_ids(value):
    if (not isinstance(value, list) or len(value) > 99
            or any(not isinstance(v, str) or not QUESTION.fullmatch(v) for v in value)
            or len(set(value)) != len(value)):
        raise ValueError('Distinct explicit question IDs required')
    return value


def parse_questions(data):
    questions = {}
    for line in data.decode('utf-8-sig').splitlines():
        match = re.fullmatch(r'\s*(?:-\s*)?\[(?: |x|X)\]\s*(Q[0-9]{2})[.)]\s*(.+)', line)
        if match:
            key, text = match.groups()
            if key in questions or not text.strip() or len(text) > 10000:
                raise ValueError('Duplicate or invalid question')
            questions[key] = text.strip()
    if not questions:
        raise ValueError('No numbered questions found')
    return questions


def indexed(rows, key):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 200:
        raise ValueError('A bounded nonempty model list is required')
    result = {}
    for row in rows:
        identity = row.get(key) if isinstance(row, dict) else None
        if not isinstance(identity, str) or not KEY.fullmatch(identity) or identity in result:
            raise ValueError('Distinct bounded model keys required')
        result[identity] = row
    return result


def render(packet):
    esc = lambda value: html.escape(str(value), quote=True)
    cards = []
    for model in packet['models']:
        candidates = ''.join(
            '<tr><td>'+esc(c['source_node_id'])+'</td><td>'+esc(c['source_path'])+'</td><td>'
            +esc(c['name_raw'])+'</td><td>'+esc(c['proposed_role'])
            +' <strong>— propozycja do potwierdzenia</strong></td><td>'
            +esc(c['subtree_node_count'])+' / '+esc(c['subtree_cad_part_count'])+'</td></tr>'
            for c in model['component_candidates'])
        if not candidates:
            candidates = '<tr><td colspan="5">Brak kandydatów. Role pozostają nieznane.</td></tr>'
        questions = ''.join('<li><b>'+esc(q['id'])+'</b> '+esc(q['text'])
                            +' <em>— oczekuje na odpowiedź</em></li>' for q in model['questions'])
        cards.append('<article><h2>'+esc(model['key']+' — '+model['name'])+'</h2><p>'
            +esc(model['family_candidate'])+' — kandydat rodziny, nie zatwierdzony szablon.</p>'
            +'<p>Integralność źródła/inwentarza: <b>PASS</b>. Odczyt obrysów brył: <b>'
            +esc(model['body_bounds_read_status'])+'</b> ('+esc(model['valid_body_bounds_count'])
            +'/'+esc(model['cad_physical_part_count'])+'). Braki historii cech: '
            +esc(model['feature_metadata_error_count'])+'. Inne błędy odczytu: '
            +esc(model['other_read_error_count'])+'.</p><p>Montaż: standard roboczy ze źródła. '
            +'Parametryzacja W/D/H: <b>NOT RUN</b>. Role, SKU, wycięcia, pasowanie, nośność '
            +'i produkcja: <b>NIEZNANE / DO POTWIERDZENIA</b>.</p><p>Źródło SHA256: <code>'
            +esc(model['source_sha256'])+'</code><br>Inwentarz SHA256: <code>'
            +esc(model['inventory_sha256'])+'</code></p><table><thead><tr><th>ID CAD</th><th>Ścieżka</th>'
            +'<th>Nazwa źródłowa</th><th>Proponowana rola</th><th>Węzły / części w poddrzewie</th>'
            +'</tr></thead><tbody>'+candidates+'</tbody></table><details open><summary>Pytania do modelu</summary>'
            +'<ol>'+questions+'</ol></details></article>')
    return '''<!doctype html><html lang="pl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>RockPro — karty mapowania rodzin</title><style>
body{font:16px system-ui;background:#f4f7f6;color:#193331;margin:0}main{max-width:1300px;margin:auto;padding:24px}
article{background:white;border:1px solid #bfcfca;border-left:5px solid #e88629;margin:24px 0;padding:20px}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #cbd7d2;padding:8px;text-align:left;overflow-wrap:anywhere}
code{overflow-wrap:anywhere}li{margin:10px 0}summary{cursor:pointer;font-weight:bold;margin-top:18px}
</style><main><h1>Karty mapowania rodzin RockPro</h1><p>Odczytowy pakiet do rozmowy z konstruktorem.
Liczba fizycznych części CAD nie jest zakupowym BOM. Poddrzewa kandydatów mogą się nakładać:
nie sumować ich liczników. Brak informacji o wycięciu nie oznacza braku wycięcia.
PASS dotyczy wyłącznie wskazanego sprawdzenia danych, nie gotowości produkcyjnej.</p>'''+''.join(cards)+'</main></html>'


def prepare(manifest_path, drafts_path, inventory_dir, questions_path, config_path, output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Output already exists; use a new review revision')
    inputs = {name: Path(path).resolve(strict=True) for name, path in (
        ('manifest', manifest_path), ('drafts', drafts_path), ('questions', questions_path), ('config', config_path))}
    raw = {name: read_bytes(path) for name, path in inputs.items()}
    manifest, drafts, config = (json.loads(raw[k].decode('utf-8-sig')) for k in ('manifest', 'drafts', 'config'))
    if not isinstance(manifest, dict) or manifest.get('contract') != 'rockpro-model-survey-v1':
        raise ValueError('Expected a model survey manifest')
    if not isinstance(manifest.get('files'), dict) or not manifest['files']:
        raise ValueError('Expected the archive file inventory')
    models = indexed(manifest.get('models'), 'key')
    drafts = indexed(drafts, 'model')
    if (not isinstance(config, dict) or set(config) != {'schema_version', 'common_questions', 'models'}
            or type(config['schema_version']) is not int or config['schema_version'] != 1):
        raise ValueError('Exact review configuration version 1 required')
    selected = indexed(config['models'], 'key')
    if set(models) != set(drafts) or set(models) != set(selected):
        raise ValueError('Manifest, drafts and explicit review configuration must cover the same models')
    questions = parse_questions(raw['questions'])
    common = question_ids(config['common_questions'])
    cards = []
    checksums = {str(path): digest(raw[name]) for name, path in inputs.items()}
    for key, selection in selected.items():
        if set(selection) != {'key', 'questions'}:
            raise ValueError('Exact model review configuration fields required')
        own = question_ids(selection['questions'])
        if set(common) & set(own) or any(q not in questions for q in common + own):
            raise ValueError('Unknown or repeated model question')
        source = models[key]
        draft = drafts[key]
        source_path = Path(source['source']).resolve(strict=True)
        source_sha = file_sha(source_path)
        if (source_sha != source['sha256'] or source_sha != draft.get('source_sha256')
                or not isinstance(source.get('name'), str) or source_path.name != source['name']):
            raise ValueError('Source revision mismatch: '+key)
        if not any(isinstance(row, dict) and row.get('sha256') == source_sha
                   and row.get('bytes') == source_path.stat().st_size
                   for row in manifest.get('files', {}).values()):
            raise ValueError('Source absent from archive file inventory: '+key)
        if (draft.get('status') != 'reference_draft' or draft.get('executable_template') is not False
                or draft.get('production_approved') is not False):
            raise ValueError('Only unapproved reference drafts belong in this packet')
        inv_path = Path(inventory_dir).resolve(strict=True) / (key+'-inventory.json')
        inv_bytes = read_bytes(inv_path)
        standard = build_working_standard(inv_bytes, source_sha, draft.get('inventory_sha256'))
        nodes = standard['nodes']
        by_id = {n['source_node_id']: n for n in nodes}
        candidates = draft.get('component_candidates')
        if not isinstance(candidates, list) or len(candidates) > 200:
            raise ValueError('Bounded candidate list required')
        mapped = []; used = set()
        for candidate in candidates:
            ident = candidate.get('id') if isinstance(candidate, dict) else None
            if type(ident) is not int or ident not in by_id or ident in used:
                raise ValueError('Unknown or repeated candidate component ID: '+key)
            if (candidate.get('confirmed') is not False or not isinstance(candidate.get('role'), str)
                    or not candidate['role'].strip() or len(candidate['role']) > 1000):
                raise ValueError('Explicit unconfirmed role proposal required')
            node = by_id[ident]; used.add(ident)
            if node['type'] not in ('Z_ELEMENT_ASSEMBLY', 'Z_ELEMENT_PART'):
                raise ValueError('Candidate must identify a physical hierarchy component')
            subtree = [n for n in nodes if n['source_path'] == node['source_path']
                       or n['source_path'].startswith(node['source_path']+'/')]
            mapped.append(dict(source_node_id=ident, source_path=node['source_path'], name_raw=node['name_raw'],
                proposed_role=candidate['role'], role_status='proposal_to_confirm', confirmed=False,
                subtree_node_count=len(subtree), subtree_cad_part_count=sum(n['type']=='Z_ELEMENT_PART' for n in subtree)))
        parts = [n for n in nodes if n['type']=='Z_ELEMENT_PART']
        valid = sum(n['body_bounds_local_m'] is not None for n in parts)
        errors = standard['read_errors']
        if not isinstance(errors, list) or any(not isinstance(e, dict) for e in errors):
            raise ValueError('Explicit inventory read errors required')
        feature_errors = sum(e.get('field') == 'feature_metadata' for e in errors)
        cards.append(dict(key=key, name=source['name'], source_sha256=source_sha,
            inventory_sha256=digest(inv_bytes), native_api_version=standard['native_api_version'],
            family_candidate=draft.get('family_candidate', 'Nieznana rodzina'), source_integrity_status='PASS',
            inventory_integrity_status='PASS', body_bounds_read_status='PASS' if parts and valid==len(parts) else 'PARTIAL',
            cad_node_count=len(nodes), cad_physical_part_count=len(parts), valid_body_bounds_count=valid,
            feature_metadata_error_count=feature_errors, other_read_error_count=len(errors)-feature_errors,
            mounting_status='provisional_source_standard', component_candidates=mapped,
            confirmed_component_role_count=0, proposed_component_role_count=len(mapped),
            semantic_mapping_status='unconfirmed' if mapped else 'no_candidates',
            dimensions_parametric_status='NOT RUN', machining_knowledge='unknown', sku_knowledge='unknown',
            fit_knowledge='unknown', load_capacity_knowledge='unknown', production_knowledge='unknown',
            executable_template=False, production_approved=False, purchasing_bom=False,
            questions=[dict(id=q, text=questions[q], answer_status='pending') for q in common+own]))
        checksums[str(source_path)] = source_sha
        checksums[str(inv_path)] = digest(inv_bytes)
    packet = dict(schema='rockpro.family-review-packet/1', models=cards,
                  input_sha256=checksums, production_approved=False, executable_template=False,
                  status='constructor_review_pending', native_execution='NOT RUN by this reader')
    page = render(packet)
    # Detect a revision changed during the read. Outputs are a separate new packet.
    if any(file_sha(path) != expected for path, expected in checksums.items()):
        raise ValueError('Input revision changed during review preparation')
    output.mkdir(parents=True, exist_ok=False)
    (output/'index.html').write_text(page, encoding='utf-8')
    (output/'packet.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return packet


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'drafts', 'inventory-dir', 'questions', 'config', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.manifest, args.drafts, args.inventory_dir, args.questions, args.config, args.output)
    print(json.dumps({'models': len(result['models']), 'status': result['status'], 'output': str(args.output)}))
