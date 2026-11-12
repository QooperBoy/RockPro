"""Native 2023 expression proof on a copy of the fixed diagnostic cuboid.

Not a general case adapter. Run after IronCad2023Probe; no user model accepted.
Use one CAD writer, preserve every modified owned document and all source bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Integracja'))
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.icapi_runtime import selected_year


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(source, expected_sha256, output, target_mm=40):
    if selected_year() != 2023:
        raise ValueError('This diagnostic targets IronCAD 2023 only')
    if not (type(target_mm) in (int, float) and 5 <= target_mm <= 500 and target_mm != 60):
        raise ValueError('target_mm must be 5..500 mm and differ from the 60 mm re-check')
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    if sha(source) != expected_sha256:
        raise ValueError('Source revision mismatch')
    output.mkdir(parents=True, exist_ok=False)
    working = output / 'working.ics'
    shutil.copyfile(source, working)
    import comtypes.client
    from rockpro_cad.icapi_runtime import ICAPI as api, assert_host, installation_dir
    from ironcad_adapter import connect
    legacy_api = comtypes.client.GetModule(str(installation_dir() / 'bin/IronCad.tlb'))
    result = dict(passed=False, source_sha256=expected_sha256, checks=[],
                  binding_mode='native_legacy_sizebox_expression', target_mm=target_mm)
    owned = None
    base = None

    def state():
        active = base.ActiveDoc
        return (active.Name, active.FileGUID, bool(active.Modified)) if active else None

    def objects(path):
        legacy, _, document = connect(path)
        scene = document.QueryInterface(api.IZSceneDoc)
        root = scene.GetTopElement()
        if root.GetChildrenCount() != 1:
            raise ValueError('Only the single-part compatibility diagnostic is supported')
        element = root.GetChildrenZArray().Get(0).QueryInterface(api.IZElement)
        if element.Name != 'RockPro compatibility probe':
            raise ValueError('Not the fixed diagnostic part')
        part = element.QueryInterface(api.IZPart)
        shapes = legacy.Shape.Components(legacy_api.triGroup).Item(1).Shapes
        if shapes.Count != 1:
            raise ValueError('Legacy/native diagnostic hierarchy differs')
        box = shapes.Item(1).Components(legacy_api.triSizeBox)
        if box.Count != 1:
            raise ValueError('Ambiguous legacy sizebox')
        # Vendor TLB: DISPID 65540, indexed property Variable(Type, Index).
        variable = box.Item(1)._comobj._invoke(65540, 2, 0, legacy_api.triHeight, 0)
        return scene, part, variable

    def measure(scene, part, label, millimetres):
        scene.GetTopElement().QueryInterface(api.IZAssembly).RegenerateParts(True)
        scene.Update()
        bounds = list(part.GetBody(True).GetBoundingBox())
        expected = (100, 50, millimetres)
        actual = [(bounds[i + 3] - bounds[i]) * 1000 for i in range(3)]
        if any(abs(a - b) > .001 for a, b in zip(actual, expected)):
            raise ValueError(f'{label}: geometry differs: {actual}')
        result['checks'].append(dict(name=label, dimensions_mm=actual, passed=True))

    with cad_writer_lock():
        try:
            base = comtypes.client.GetActiveObject('IronCAD.Application', dynamic=True).ZIronCADApp.QueryInterface(api.IZBaseApp)
            assert_host(base)
            result['api_version'] = base.ApiVersion
            result['context_before'] = state()
            already, candidate = base.OpenFile2(str(working), False, False)
            if already:
                raise ValueError('Ownership refused')
            owned = candidate
            scene, part, variable = objects(working)
            measure(scene, part, 'input', 20)
            part.QueryInterface(api.IZSizeBox).Reset(False)
            expression = r'Parent\Params\RP_ProbeThickness'
            variable.Expression = expression
            parameter = scene.ParameterMgr.GetParameterByName('RP_ProbeThickness')
            parameter.Expression = f'{target_mm} mm'
            measure(scene, part, 'native_expression_resize', target_mm)
            saved = output / 'bound.ics'
            scene.SaveAs(str(saved), api.Z_LINKS_COPY_ALL, False)
            if owned.Modified:
                raise ValueError('Save did not clear Modified')
            owned.Close(); owned = None
            already, candidate = base.OpenFile2(str(saved), False, False)
            if already:
                raise ValueError('Reopen ownership refused')
            owned = candidate
            scene, part, variable = objects(saved)
            if variable.Expression != expression:
                raise ValueError('Native expression did not survive reopening')
            measure(scene, part, 'reopened', target_mm)
            parameter = scene.ParameterMgr.GetParameterByName('RP_ProbeThickness')
            parameter.Expression = '60 mm'
            measure(scene, part, 'post_reopen_parameter_only_resize', 60)
            parameter.Expression = '20 mm'
            measure(scene, part, 'return_to_input_dimensions', 20)
            scene.SaveAs(str(output / 'bound_restored.ics'), api.Z_LINKS_COPY_ALL, False)
            result['passed'] = True
        except Exception as exc:
            result['error'] = repr(exc)
        finally:
            if owned is not None:
                try:
                    if owned.Modified:
                        owned.QueryInterface(api.IZSceneDoc).SaveAsCopy(str(output / 'recovery.ics'), api.Z_LINKS_COPY_ALL, False)
                    owned.Close()
                except Exception as exc:
                    result['cleanup_error'] = repr(exc); result['passed'] = False
            if base is not None:
                result['context_after'] = state()
                if result['context_after'] != result.get('context_before'):
                    result['passed'] = False; result['context_changed'] = True
            result['source_unchanged'] = sha(source) == expected_sha256
            if not result['source_unchanged']:
                result['passed'] = False
            (output / 'result.json').write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--target-mm', type=float, default=40)
    args = parser.parse_args()
    report = run(args.source, args.expected_sha256, args.output, args.target_mm)
    print(json.dumps(report, ensure_ascii=True))
    raise SystemExit(0 if report['passed'] else 1)
