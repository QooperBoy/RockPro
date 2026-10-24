"""Resize the pinned full-case v3 on a new copy; native prototype, not production."""
import argparse
import itertools
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Integracja'))
from rockpro_cad.core_case.profile_rules import expression, value
from rockpro_cad.core_case.transport_rules import validate_transport_values
from rockpro_cad.core_case.handle_rules import side_handle_rules
from rockpro_cad.mcp.lid_policy import PLYWOOD_COLORREF, validate_lid_height
from rockpro_cad.parts.native import file_sha256, same_document_path


def execute(source, receipt, output, handle_asset, handle_datum, handles_per_wall=2, depth_mm=500.):
    import comtypes.client
    comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
    from python_ironcad import ICAPI as A
    from rockpro_cad.cad_lock import cad_writer_lock
    from rockpro_cad.core_case.catalog_native import close_owned_documents

    source = source.resolve(strict=True)
    output = output.resolve()
    handle_asset = handle_asset.resolve(strict=True)
    datum = json.loads(handle_datum.read_text(encoding="utf-8"))
    if file_sha256(handle_asset) != datum["asset_sha256"]:
        raise ValueError("Pinned H7159 asset/datum mismatch")
    previous = json.loads(receipt.read_text(encoding='utf-8'))
    source_hash = file_sha256(source)
    if (previous.get('contract') != 'full_case_transport_v3'
            or previous.get('passed') is not True
            or previous.get('result_sha256') != source_hash):
        raise ValueError('Verified, hash-pinned full-case v3 receipt required')
    v = dict(RP_Length=650., RP_Depth=depth_mm, RP_BaseHeight=300., RP_LidHeight=81.,
             RP_Thickness=9.8, RP_DisplayGap=0., RP_JointGap=8.63)
    handle_definitions = side_handle_rules(v, handles_per_wall)
    hinge_heights = [80.]
    validate_transport_values(v)
    minimum = validate_lid_height(v['RP_LidHeight'], hinge_heights, v['RP_BaseHeight'], True)
    profile = previous['source_profile_report']
    report = dict(schema_version=1, contract='epson_full_case_prototype_v1',
                  source=str(source), source_sha256=source_hash, parameters_mm=v,
                  lid_policy=dict(hinge_required_heights_mm=hinge_heights, minimum_mm=minimum, constructor_override=True,
                                  reason="User requested inspiration from EB-L630U reference: 73 mm lid boards plus approximately 8 mm joint",
                                  H2026_installed=False),
                  plywood_colorref=PLYWOOD_COLORREF, checks=[], production_approved=False,
                  device_envelope_mm=[440., 339., 136.],
                  device_source='https://www.epson.eu/en_EU/products/projector/professional/eb-l630u-projector/p/31706',
                  interior_modelled=False, cutouts_modelled=False,
                  native_graphics_review='NOT RUN', handles_per_wall=handles_per_wall,
                  handle_asset=str(handle_asset),handle_asset_sha256=datum['asset_sha256'])

    def near(actual, expected, tolerance=.05):
        if len(actual) != len(expected) or any(abs(a-b) > tolerance for a, b in zip(actual, expected)):
            raise ValueError(('Native geometry differs', actual, expected))

    with cad_writer_lock():
        output.mkdir(parents=True, exist_ok=False)
        working = output / 'working_input.ics'
        with source.open('rb') as src, working.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        base = comtypes.client.GetActiveObject('IronCAD.Application', dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
        owned = []
        active = base.ActiveDoc
        context = (str(active.Name), bool(active.Modified)) if active else None

        def opened(path):
            already, doc = base.OpenFile2(str(path), False, False)
            if already:
                raise ValueError('Document already open; ownership refused')
            owned.append(doc)
            if not same_document_path(doc.Name, path):
                raise ValueError('Wrong document')
            return doc, doc.QueryInterface(A.IZSceneDoc)

        def close(doc):
            close_owned_documents([doc], A, output)
            owned.remove(doc)

        def children(e):
            n = e.GetChildrenCount()
            if not n:
                return []
            arr = e.GetChildrenZArray()
            return [arr.Get(i).QueryInterface(A.IZElement) for i in range(n)]

        def bounds(e):
            try:
                part = e.QueryInterface(A.IZPart)
            except comtypes.COMError:
                return list(e.QueryInterface(A.IZAssembly).GetBoundingBox(True))
            return list(part.GetBoundingBox(True))

        def point(p, e):
            m = e.QueryInterface(A.IZSceneElement).GetTransformToGlobal()
            return [sum(p[k]*m.GetValue(k, j) for k in range(3))+m.GetValue(3, j)*1000 for j in range(3)]

        def world_bounds(e):
            b = bounds(e)
            points = [point(p, e) for p in itertools.product(*[(b[j]*1000, b[j+3]*1000) for j in range(3)])]
            return [min(p[j] for p in points) for j in range(3)] + [max(p[j] for p in points) for j in range(3)]

        def dirty(e):
            try:
                assembly = e.QueryInterface(A.IZAssembly)
            except comtypes.COMError:
                e.QueryInterface(A.IZPart).Update()
            else:
                for c in children(e):
                    dirty(c)
                assembly.Update()
            e.SetDirtyFlag(A.Z_DIRTY_GRAPHICS)

        try:
            doc, scene = opened(working)
            utility = scene.QueryInterface(A.IZSceneDocUtility)
            roots = children(scene.GetTopElement())
            if len(roots) != 64:
                raise ValueError('Expected exactly 64 roots in the pinned v3')
            # Reuse the two existing rigid handles; add only the extra pair.
            top=scene.GetTopElement().QueryInterface(A.IZAssembly)
            handle_bounds=None
            existing={('left',1):682,('right',1):836}
            for row in handle_definitions:
                slot=int(row['id'].split('/')[-1])
                node_id=existing.get((row['side'],slot))
                e=(utility.GetElementById(node_id) if node_id is not None else
                   top.AddChildFromExternalFile(str(handle_asset),False).QueryInterface(A.IZElement))
                row['logical_id']=row['id'];row['id']=int(e.Id)
                e.Name='RockPro - H7159 - '+row['logical_id']
                if len(children(e))!=13:raise ValueError('Expected a complete thirteen-part H7159')
                local_bounds=bounds(e)
                if handle_bounds is None:handle_bounds=local_bounds
                else:near([x*1000 for x in local_bounds],[x*1000 for x in handle_bounds])
                se=e.QueryInterface(A.IZSceneElement);anchor=se.GetAnchorTransform()
                for i in range(4):
                    for j in range(4):anchor.SetValue(i,j,int(i==j))
                se.SetAnchorTransform(anchor)
                m=se.GetTransformToParent()
                for i in range(3):
                    for j in range(3):m.SetValue(i,j,row['rotation'][i][j])
                se.SetTransformToParent(m)
            profile['old_bindings']=[r for r in profile['old_bindings'] if r['kind']!='handles']+handle_definitions
            # Complete imports first, then rebind every inherited expression once.
            for row in profile['old_bindings']:
                e=utility.GetElementById(row['id']);se=e.QueryInterface(A.IZSceneElement)
                if row['kind']=='panel':
                    e.QueryInterface(A.IZPart).SurfaceFinish.Color=PLYWOOD_COLORREF
                    feature=utility.GetElementById(row['feature_id']);box=feature.QueryInterface(A.IZSizeBox)
                    for axis,formula in zip(('Length','Width','Height'),row['size']):setattr(box,axis+'Expression',expression(formula,2))
                    feature.QueryInterface(A.IZSceneElement).ForceSetupParameterExpression()
                for j,formula in enumerate(row['position']):se.PositionTransformComponentExpression[j]=expression(formula,2 if row['kind']=='corners' else 1)
                se.ForceSetupParameterExpression()
            for row in profile['bindings']:
                e=utility.GetElementById(row['node_id']);se=e.QueryInterface(A.IZSceneElement)
                if row['cut_length']:e.QueryInterface(A.IZSizeBox).HeightExpression=expression(row['cut_length'])
                for j,formula in enumerate(row['position']):se.PositionTransformComponentExpression[j]=expression(formula)
                se.ForceSetupParameterExpression()
            for row in previous['members']:
                e=utility.GetElementById(row['node_id']);se=e.QueryInterface(A.IZSceneElement)
                if row['kind']=='pad':
                    feature=utility.GetElementById(row['feature_id']);box=feature.QueryInterface(A.IZSizeBox)
                    for axis,formula in zip(('Length','Width','Height'),row['dimensions']):setattr(box,axis+'Expression',expression(formula,2))
                    feature.QueryInterface(A.IZSceneElement).ForceSetupParameterExpression()
                for j,formula in enumerate(row['position']):se.PositionTransformComponentExpression[j]=expression(formula)
                se.ForceSetupParameterExpression()
            report['handle_height_rule']='RP_BaseHeight/2'
            report['small_case_binding_changes']=handle_definitions
            report['handle_layout']=dict(walls=['left','right'],hinge_wall='rear',per_wall=handles_per_wall,
                                         total=2*handles_per_wall,rigid_hardware=True)
            for row in previous['members']:
                if row['kind'] == 'pad':
                    utility.GetElementById(row['node_id']).QueryInterface(A.IZPart).SurfaceFinish.Color = PLYWOOD_COLORREF
            scene.ParameterMgr.GetParameterByName('RP_LidHeight').Notes = (
                'Hinge minimum 80 mm including roof/clearance; lid 81 mm inspired by T_1. '
                'Explicit constructor exception to 15% proportion. H2026 not installed.')

            def update(values):
                validate_transport_values(values)
                side_handle_rules(values,handles_per_wall)
                validate_lid_height(values['RP_LidHeight'], hinge_heights, values['RP_BaseHeight'], True)
                for name, number in values.items():
                    scene.ParameterMgr.GetParameterByName(name).Expression = f'{number} mm'
                scene.GetTopElement().QueryInterface(A.IZAssembly).RegenerateParts(True)
                scene.Update()

            def measure(label, values, placement=False):
                for row in profile['old_bindings']:
                    e = utility.GetElementById(row['id'])
                    se = e.QueryInterface(A.IZSceneElement)
                    near([se.PositionTransformComponentValue[j]*1000 for j in range(3)],
                         [value(s, values) for s in row['position']])
                    if row['kind']=='handles':
                        near([x*1000 for x in bounds(e)],[x*1000 for x in handle_bounds])
                        matrix=se.GetTransformToGlobal()
                        near([matrix.GetValue(i,j) for i in range(3) for j in range(3)], [x for line in row['rotation'] for x in line],1e-7)
                        near(point([0,0,0],e),[value(formula,values) for formula in row['position']])
                    if row['kind'] == 'panel':
                        b = bounds(e)
                        near([(b[j+3]-b[j])*1000 for j in range(3)], [value(s, values) for s in row['size']])
                        if e.QueryInterface(A.IZPart).SurfaceFinish.Color != PLYWOOD_COLORREF:
                            raise ValueError('Plywood color not retained')
                for row in profile['bindings']:
                    e = utility.GetElementById(row['node_id'])
                    b = bounds(e)
                    wanted = list(row['section_mm'])
                    if row['cut_length']:
                        wanted[2] = value(row['cut_length'], values)
                    near([(b[j+3]-b[j])*1000 for j in range(3)], wanted)
                    near(point([(b[j]+b[j+3])*500 for j in range(3)], e),
                         [value(s, values) for s in row['center']])
                anchors = {}
                for row in previous['members']:
                    e = utility.GetElementById(row['node_id'])
                    anchors[row['id']] = point([0, 0, 0] if row['kind'] == 'pad' else row['local_anchor_mm'], e)
                    near(anchors[row['id']], [value(s, values) for s in row['anchor']])
                    if row['kind'] == 'pad':
                        b = bounds(e)
                        near([(b[j+3]-b[j])*1000 for j in range(3)], [value(s, values) for s in row['dimensions']])
                for side in ('left', 'right'):
                    lo = anchors[f'hinge/{side}/base']
                    near(anchors[f'hinge/{side}/lid'], [lo[0], lo[1], lo[2]+values['RP_DisplayGap']])
                check = dict(label=label, parameters_mm=values, passed=True, roots=64+2*(handles_per_wall-1),
                             panels=10, profiles_and_braces=32, transport_members=14)
                if len(children(scene.GetTopElement()))!=check['roots']:raise ValueError('Unexpected occurrence count')
                if placement:
                    fittings = []
                    for row in profile['old_bindings']:
                        if row['kind'] in ('handles', 'latches'):
                            fittings.append(dict(id=str(row['id']), kind=row['kind'],
                                                 bounds_mm=world_bounds(utility.GetElementById(row['id']))))
                    for row in previous['members']:
                        if row['kind'] in ('hinge', 'socket', 'wheel'):
                            fittings.append(dict(id=row['id'], kind=row['kind'],
                                                 bounds_mm=world_bounds(utility.GetElementById(row['node_id']))))
                    unexpected = []
                    for a, b in itertools.combinations(fittings, 2):
                        # The two halves of each joint intentionally mate.
                        if ({a['id'], b['id']} in ({'78', '192'}, {'380', '494'})
                                or (a['kind'] == b['kind'] == 'hinge'
                                    and a['id'].split('/')[1] == b['id'].split('/')[1])):
                            continue
                        overlap = [min(a['bounds_mm'][j+3], b['bounds_mm'][j+3])-max(a['bounds_mm'][j], b['bounds_mm'][j]) for j in range(3)]
                        if min(overlap) > .5:
                            unexpected.append(dict(a=a['id'], b=b['id'], overlap_mm=overlap))
                    check.update(fitting_bounds=fittings, unexpected_fitting_aabb_overlaps=unexpected,
                                 collision_scope='Conservative rigid fitting AABBs only; excludes mating halves, panels and profile joints')
                    if unexpected:
                        raise ValueError(('Fitting envelopes overlap', unexpected))
                    for slot in range(1,handles_per_wall+1):
                        pair=[next(row for row in handle_definitions if row['logical_id']==f'handles/{side}/{slot}') for side in ('left','right')]
                        centers=[point([0,0,0],utility.GetElementById(row['id'])) for row in pair]
                        near([centers[0][0],centers[1][0],centers[0][1]-centers[1][1],centers[0][2]-centers[1][2]], [0,values['RP_Length'],0,0])
                    check['handle_layout']=report['handle_layout']
                    internal = [values['RP_Length']-2*values['RP_Thickness'], values['RP_Depth']-2*values['RP_Thickness'], values['RP_BaseHeight']-values['RP_Thickness']]
                    required = [440+2*30, 339+2*30, 136+50+20]
                    if any(a < b for a, b in zip(internal, required)):
                        raise ValueError('Device and provisional padding allowance do not fit')
                    check.update(base_clear_envelope_mm=internal, provisional_device_padding_required_mm=required)
                report['checks'].append(check)
                print(label, 'PASS', flush=True)

            update(v)
            measure('target', v, True)
            alternate = dict(v, RP_Length=700., RP_Depth=550., RP_BaseHeight=330., RP_LidHeight=90., RP_DisplayGap=50.)
            update(alternate)
            measure('parameter_only_resize', alternate, True)
            update(v)
            measure('restored', v)
            dirty(scene.GetTopElement())
            scene.Update()
            result = output / f"RockPro_EB-L630U_650x{v['RP_Depth']:g}x381_uchwyty_{2*handles_per_wall}.ics"
            scene.SaveAs(str(result), A.Z_LINKS_COPY_ALL, False)
            close(doc)
            doc, scene = opened(result)
            utility = scene.QueryInterface(A.IZSceneDocUtility)
            measure('saved_reopened', v, True)
            update(alternate)
            measure('post_reopen_resize', alternate)
            update(v)
            dirty(scene.GetTopElement())
            scene.Update()
            measure('post_reopen_restored', v)
            doc.Save()
            close(doc)
            report.update(result=str(result), result_sha256=file_sha256(result), passed=True)
        finally:
            close_owned_documents(owned, A, output)
            if file_sha256(handle_asset)!=datum['asset_sha256']:raise ValueError('H7159 source asset changed')
            if file_sha256(source) != source_hash:
                raise ValueError('Original model changed')
            active = base.ActiveDoc
            after = (str(active.Name), bool(active.Modified)) if active else None
            if after != context:
                raise ValueError('Active user document context changed')
        report.update(source_unchanged=True, owned_documents_closed=True)
        with (output / 'prototype_report.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--handle-asset',type=Path,required=True)
    parser.add_argument('--handle-datum',type=Path,required=True)
    parser.add_argument('--handles-per-wall',type=int,choices=(1,2),default=2)
    parser.add_argument('--depth-mm',type=float,default=500.)
    args = parser.parse_args()
    if not args.native:
        print(f'PLAN ONLY: 650 x {args.depth_mm:g} mm; base 300 mm, lid 81 mm; {args.handles_per_wall} handles per opposing wall. Native NOT RUN.')
    else:
        result = execute(args.source, args.receipt, args.output_dir,args.handle_asset,args.handle_datum,args.handles_per_wall,args.depth_mm)
        print(json.dumps(dict(passed=result['passed'], result=result['result'])))
