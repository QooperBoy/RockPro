"""Table-driven parameter edit on isolated copies; verify geometry after reopening."""
import argparse
import hashlib
import json
import math
import traceback
import sys
import msvcrt
from datetime import datetime, timezone
from pathlib import Path
from ironcad_adapter import connect, find, parameter_data, ICAPI

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate(config):
    if not config['variants']:
        raise ValueError('No variants')
    for v in config['variants']:
        value = v['value_mm']
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Finite numeric dimension required')
        if not config['minimum_mm'] <= value <= config['maximum_mm']:
            raise ValueError('Dimension outside prototype test range')
        if not v['name'].isascii() or not all(c.isalnum() or c in '_-' for c in v['name']):
            raise ValueError('Unsafe variant name')
    if len({v['name'] for v in config['variants']}) != len(config['variants']):
        raise ValueError('Duplicate variant names')

def state(scene, config):
    owner = find(scene, config['parameter_path'])
    param = owner.QueryInterface(ICAPI.IZSceneElement).ParameterMgr.GetParameterByName(config['parameter_name'])
    feature = find(scene, config['geometry_path'])
    box = list(feature.QueryInterface(ICAPI.IZFeature).GetBoundingBox())
    derived = feature.QueryInterface(ICAPI.IZSceneElement).ParameterMgr.GetParameterByName(config['geometry_parameter'])
    return {'parameter': parameter_data(param), 'derived': parameter_data(derived),
            'bounding_box_m': box, 'extents_mm': [(box[i+3]-box[i])*1000 for i in range(3)]}

def check(result, value, axis, before):
    for actual in (result['parameter']['value']*1000, result['derived']['value']*1000, result['extents_mm'][axis]):
        if not math.isclose(actual, value, rel_tol=0, abs_tol=0.001):
            raise RuntimeError(f'Geometry/parameter mismatch: expected {value} mm, got {actual}')
    for i in range(3):
        if i != axis and not math.isclose(result['extents_mm'][i], before['extents_mm'][i], rel_tol=0, abs_tol=0.001):
            raise RuntimeError(f'Unexpected change of geometry axis {i}')

def _run_locked(config_path):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    validate(config)
    source = (config_path.parent / config['source']).resolve()
    legacy, base, source_doc = connect(source)
    source_scene = source_doc.QueryInterface(ICAPI.IZSceneDoc)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    folder = Path(__file__).resolve().parent / 'runs' / stamp
    folder.mkdir(parents=True, exist_ok=False)
    report = {'scope': config['scope'], 'source': str(source), 'source_sha256_before': sha256(source),
              'source_saved_before': bool(legacy.Saved), 'source_state_before': state(source_scene, config),
              'variants': [], 'success': False}
    (folder / 'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    copy_doc = None
    copy_path = None
    try:
        for variant in config['variants']:
            output = folder / (variant['name'] + '.ics')
            item = {'name': variant['name'], 'requested_mm': variant['value_mm'], 'output': str(output)}
            report['variants'].append(item)
            print('Snapshot:', output.name, flush=True)
            source_scene.SaveAsCopy(str(output), ICAPI.Z_LINKS_COPY_ALL, False)
            if not output.is_file():
                raise RuntimeError('Snapshot file missing')
            copy_doc = base.OpenFile(str(output), False)
            copy_path = str(output)
            if Path(copy_doc.Name).name != output.name:
                raise RuntimeError('Unexpected document opened')
            scene = copy_doc.QueryInterface(ICAPI.IZSceneDoc)
            item['before'] = state(scene, config)
            owner = find(scene, config['parameter_path'])
            param = owner.QueryInterface(ICAPI.IZSceneElement).ParameterMgr.GetParameterByName(config['parameter_name'])
            param.Expression = f"{variant['value_mm']:.12g} mm"
            owner.QueryInterface(ICAPI.IZAssembly).RegenerateParts(True)
            scene.Update()
            item['after'] = state(scene, config)
            check(item['after'], variant['value_mm'], config['geometry_axis'], item['before'])
            copy_doc.Save()
            copy_doc.Close()
            copy_doc = None
            reopened = base.OpenFile(str(output), False)
            copy_doc = reopened
            item['reopened'] = state(reopened.QueryInterface(ICAPI.IZSceneDoc), config)
            check(item['reopened'], variant['value_mm'], config['geometry_axis'], item['before'])
            item['sha256'] = sha256(output)
            item['verified'] = True
            reopened.Close()
            copy_doc = None
            print('Verified save/reopen:', variant['name'], flush=True)
        report['success'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        print(ascii(report['error']), flush=True)
    finally:
        if copy_doc is not None:
            report['failed_copy_left_open'] = copy_path
        report['source_unchanged'] = False
        try:
            report['source_sha256_after'] = sha256(source)
            report['source_saved_after'] = bool(legacy.Saved)
            report['source_state_after'] = state(source_scene, config)
            report['source_unchanged'] = (report['source_sha256_before'] == report['source_sha256_after'] and
                report['source_saved_before'] == report['source_saved_after'] and
                report['source_state_before'] == report['source_state_after'])
        except Exception:
            report['source_verification_error'] = traceback.format_exc()
        try:
            base.ActiveDoc = source_doc
        except Exception:
            report['restore_active_document_error'] = traceback.format_exc()
        report['success'] = report['success'] and report['source_unchanged']
        (folder / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'success': report['success'], 'source_unchanged': report['source_unchanged'], 'report': str(folder/'report.json')}, ensure_ascii=True), flush=True)
    return report['success']

def run(config_path):
    lock_path = Path(__file__).with_name('.cad-worker.lock')
    with lock_path.open('a+b') as lock:
        if lock_path.stat().st_size == 0:
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError('Another CAD job is running') from exc
        try:
            return _run_locked(config_path)
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=str(Path(__file__).with_name('mvp_config.json')))
    args = parser.parse_args()
    raise SystemExit(0 if run(args.config) else 1)
