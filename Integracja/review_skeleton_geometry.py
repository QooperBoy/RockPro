"""Independent offline audit of ten solid rectangular skeleton plates.

Input JSON schema, dimensions in mm and aligned local coordinates per half:
{"halves": {
  "base": {"length_mm": 914, "depth_mm": 602, "height_mm": 239.24,
           "thickness_mm": 9.8, "closure": "bottom", "panels": [
             {"role": "front", "bbox_mm": [xmin,ymin,zmin,xmax,ymax,zmax]}, ...]},
  "lid": {..., "closure": "top", ...}
}}
Roles: front (y minimum), back (y maximum), left (x minimum), right
(x maximum), closure. Bboxes must be measured geometry, not input formulas.
Front/back span full X, left/right fit between them in Y. Closure spans XY.
This checks plain plates only; no guarantee about fasteners or machining.
"""
import argparse
import itertools
import json
import math
from pathlib import Path


def validate(data, tolerance_mm=0.002):
    errors, checks = [], []

    def check(label, ok, actual=None, expected=None):
        checks.append({'check': label, 'passed': bool(ok), 'actual': actual, 'expected': expected})
        if not ok:
            errors.append(label)

    halves = data.get('halves', {})
    check('exactly base and lid', set(halves) == {'base', 'lid'})
    for name, half in halves.items():
        values = [half.get(k) for k in ('length_mm', 'depth_mm', 'height_mm', 'thickness_mm')]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
            check(name+' valid dimensions', False)
            continue
        length, depth, height, t = values
        check(name+' physical dimensions', t > 0 and length > 2*t and depth > 2*t and height > t)
        closure = half.get('closure')
        check(name+' closure direction', closure in ('bottom', 'top'))
        panels = half.get('panels', [])
        roles = [p.get('role') for p in panels]
        check(name+' five unique roles', len(roles) == 5 and set(roles) == {'front','back','left','right','closure'})
        boxes = {}
        for panel in panels:
            role, b = panel.get('role'), panel.get('bbox_mm', [])
            if len(b) != 6 or not all(isinstance(v, (float,int)) and math.isfinite(v) for v in b):
                check(f'{name}/{role} finite measured bbox', False)
                continue
            check(f'{name}/{role} positive extents', all(b[j+3] > b[j] for j in range(3)))
            boxes[role] = b
        if len(boxes) != 5:
            continue
        origin = [min(b[j] for b in boxes.values()) for j in range(3)]
        local = {role: [b[j]-origin[j%3] for j in range(6)] for role,b in boxes.items()}
        low, high = (t,height) if closure == 'bottom' else (0,height-t)
        expected = {
            'front': [0,0,low,length,t,high],
            'back': [0,depth-t,low,length,depth,high],
            'left': [0,t,low,t,depth-t,high],
            'right': [length-t,t,low,length,depth-t,high],
            'closure': [0,0,0,length,depth,t] if closure == 'bottom' else [0,0,height-t,length,depth,height],
        }
        for role, b in local.items():
            target = expected[role]
            check(f'{name}/{role} measured location and dimensions',
                  all(abs(a-e) <= tolerance_mm for a,e in zip(b,target)), b, target)
            thin_axis = 1 if role in ('front','back') else (0 if role in ('left','right') else 2)
            thickness = b[thin_axis+3]-b[thin_axis]
            check(f'{name}/{role} thickness', abs(thickness-t) <= tolerance_mm, thickness,t)
        for (ra,a),(rb,b) in itertools.combinations(local.items(),2):
            overlap = [min(a[j+3],b[j+3])-max(a[j],b[j]) for j in range(3)]
            check(f'{name}/{ra}-{rb} no volumetric overlap', not all(v > tolerance_mm for v in overlap), overlap)
        for ra,rb in [('closure','front'),('closure','back'),('closure','left'),('closure','right'),
                      ('front','left'),('front','right'),('back','left'),('back','right')]:
            a,b = local[ra],local[rb]
            overlap = [min(a[j+3],b[j+3])-max(a[j],b[j]) for j in range(3)]
            face_contact = sum(v > tolerance_mm for v in overlap) == 2 and any(abs(v)<=tolerance_mm for v in overlap)
            check(f'{name}/{ra}-{rb} face contact',face_contact,overlap)
    return {'passed': not errors, 'scope':'ten rectangular panels in two independent local frames',
            'tolerance_mm': tolerance_mm, 'checks': checks, 'errors':errors}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    args=parser.parse_args()
    report=validate(json.loads(args.input.read_text(encoding='utf-8')))
    output=args.output or args.input.with_name(args.input.stem+'_review.json')
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'errors':report['errors'],'report':str(output)},ensure_ascii=True))
    raise SystemExit(0 if report['passed'] else 1)
