"""Independent read-only audit after a native IronCAD parameter-table edit.

Never sets parameters, regenerates, saves, closes, or opens CAD documents.
"""
import argparse
import json
import math
import traceback
from datetime import datetime, timezone
from pathlib import Path
from wholecase_common import get_doc, ICAPI, bbox, matrix, transformed_bbox


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expectedLength', type=float, default=934)
    parser.add_argument('--expectedDepth', type=float, default=602)
    parser.add_argument('--expectedBaseHeight', type=float, default=239.24)
    parser.add_argument('--expectedLidHeight', type=float, default=104.13)
    args = parser.parse_args()
    cfg, legacy, base, doc, scene = get_doc()
    folder = Path(cfg['copy']).parent
    baseline = json.loads((folder / 'verification.json').read_text(encoding='utf-8'))['baseline']
    manifest = json.loads((folder / 'installed_manifest.json').read_text(encoding='utf-8'))
    expected = dict(RP_Length=args.expectedLength, RP_Depth=args.expectedDepth,
                    RP_BaseHeight=args.expectedBaseHeight, RP_LidHeight=args.expectedLidHeight)
    report = {'timestamp': datetime.now(timezone.utc).isoformat(), 'mode': 'read_only_no_regeneration',
              'source': cfg['copy'], 'expected_mm': expected, 'checks': [], 'errors': [], 'passed': False}

    def check(label, actual, expected_value, tolerance=0.002):
        ok = math.isfinite(actual) and abs(actual-expected_value) <= tolerance
        report['checks'].append({'check': label, 'actual_mm': actual, 'expected_mm': expected_value, 'passed': ok})
        if not ok:
            report['errors'].append(label)

    try:
        report['saved_before'] = bool(legacy.Saved)
        report['parameters'] = {}
        for name, target in expected.items():
            p = scene.ParameterMgr.GetParameterByName(name)
            report['parameters'][name] = {'value_mm': p.Value*1000, 'expression': p.Expression,
                                          'visible': bool(p.ParamTableVisibility)}
            check('master '+name, p.Value*1000, target)
            if not p.ParamTableVisibility:
                report['errors'].append('master hidden '+name)

        u = scene.QueryInterface(ICAPI.IZSceneDocUtility)
        report['geometry'] = {}
        for id in (174, 198, 9090, 9078, 594, 13236):
            e = u.GetElementById(id)
            local = bbox(e, True)
            transform = matrix(e)
            report['geometry'][str(id)] = {'local': local, 'world': transformed_bbox(local, transform), 'matrix': transform}
        current = report['geometry']
        for id, dimensions in [('174', (args.expectedLength-18.5, args.expectedLidHeight, args.expectedDepth)),
                               ('198', (args.expectedLength, args.expectedBaseHeight, args.expectedDepth))]:
            b = current[id]['local']
            for axis, target in enumerate(dimensions):
                check(f'construction {id} axis {axis}', (b[axis+3]-b[axis])*1000, target)

        for corner, half in [('9090', '174'), ('9078', '198')]:
            for axis in range(3):
                center = lambda data: (data[corner]['world'][axis]+data[corner]['world'][axis+3])/2
                face = min((axis, axis+3), key=lambda j: abs(center(baseline)-baseline[half]['world'][j]))
                check(f'corner {corner} face {axis}', (center(current)-current[half]['world'][face])*1000,
                      (center(baseline)-baseline[half]['world'][face])*1000)

        for axis in range(2):
            centers_delta = lambda data: ((data['594']['world'][axis]+data['594']['world'][axis+3])-
                                          (data['13236']['world'][axis]+data['13236']['world'][axis+3]))/2
            check(f'wheel cup offset {axis}', centers_delta(current)*1000, centers_delta(baseline)*1000)
        for id in ('9090', '9078', '594', '13236'):
            for axis in range(3):
                check(f'rigid local extent {id} {axis}',
                      (current[id]['local'][axis+3]-current[id]['local'][axis])*1000,
                      (baseline[id]['local'][axis+3]-baseline[id]['local'][axis])*1000)

        check('lid base seam', (current['174']['world'][2]-current['198']['world'][5])*1000,
              (baseline['174']['world'][2]-baseline['198']['world'][5])*1000)
        report['panels'] = {}
        for id in (180, 184, 188, 192, 196, 201, 205, 209, 213, 217):
            e = u.GetElementById(id)
            b = list(e.QueryInterface(ICAPI.IZFeature).GetBoundingBox())
            extents = [(b[i+3]-b[i])*1000 for i in range(3)]
            report['panels'][str(id)] = {'extents_mm': extents}
            check(f'panel thickness {id}', min(extents), 9.8)
        report['cutouts'] = {}
        for cut in manifest.get('cutouts', []):
            id = str(cut['id'])
            e = u.GetElementById(cut['id'])
            local = list(e.QueryInterface(ICAPI.IZFeature).GetBoundingBox())
            transform = matrix(e)
            world = transformed_bbox(local, transform)
            report['cutouts'][id] = {'local': local, 'world': world, 'matrix': transform,
                                     'status': cut['binding_status']}
            ref = baseline[id]
            for j in range(6):
                check(f'cutout {id} localshape {j}', local[j]*1000, ref['local'][j]*1000)
            if cut['binding_status'] == 'bound_to_hardware':
                fid = str(cut['fixture_id'])
                if fid not in current:
                    fixture = u.GetElementById(cut['fixture_id'])
                    fbox = bbox(fixture, True)
                    fmat = matrix(fixture)
                    current[fid] = {'local': fbox, 'world': transformed_bbox(fbox, fmat), 'matrix': fmat}
                for j in range(3):
                    actual = (world[j]+world[j+3]-current[fid]['world'][j]-current[fid]['world'][j+3])/2
                    target = (ref['world'][j]+ref['world'][j+3]-baseline[fid]['world'][j]-baseline[fid]['world'][j+3])/2
                    check(f'cutout {id} to fixture {fid} offset {j}', actual*1000, target*1000)
                for i in range(3):
                    for j in range(3):
                        if abs(transform[i][j]-ref['matrix'][i][j]) > 1e-8:
                            report['errors'].append(f'cutout {id} changed orientation')
            elif cut['binding_status'] == 'inactive_outside_wood':
                wood = current[str(cut['construction'])]['world']
                if not any(world[j+3] < wood[j] or world[j] > wood[j+3] for j in range(3)):
                    report['errors'].append(f'inactive cutout {id} intersects wood')
            else:
                report['errors'].append(f'cutout {id} has no coverage classification')
        report['saved_after'] = bool(legacy.Saved)
        if report['saved_before'] != report['saved_after']:
            report['errors'].append('document saved status changed during read-only audit')
        report['passed'] = not report['errors']
    except Exception:
        report['exception'] = traceback.format_exc()
    finally:
        target = folder / 'native_table_ui_verification.json'
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'passed': report['passed'], 'errors': report['errors'], 'report': str(target)}, ensure_ascii=True))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
