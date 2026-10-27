"""Repeatable private Studio review series; never promotes concepts to production."""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Integracja'))
from rockpro_cad import configurator


def examples():
    specs = [
        ('01-skrzynia-zawiasowa', 'Skrzynia transportowa', 'case', [600, 500, 800], 115, 'hinged'),
        ('02-skrzynia-zdejmowana', 'Skrzynia ze zdejmowaną górą', 'case', [750, 500, 900], 110, 'removable'),
        ('03-szafa-serwisowa', 'Szafa serwisowa', 'cabinet', [700, 500, 900], 110, 'hinged'),
        ('04-skrzynia-trzyczesciowa', 'Skrzynia trzyczęściowa', 'three_piece', [800, 500, 800], 115, 'removable'),
        ('05-waska-wysoka-szafa', 'Nietypowa · wąska wysoka szafa', 'cabinet', [400, 450, 1400], 110, 'hinged'),
        ('06-gleboka-skrzynia', 'Nietypowa · głęboka skrzynia trzyczęściowa', 'three_piece', [420, 950, 1000], 130, 'removable'),
        ('07-szeroka-skrzynia', 'Nietypowa · szeroka skrzynia panoramiczna', 'three_piece', [1500, 450, 800], 115, 'removable'),
        ('08-plytka-szafa', 'Nietypowa · płytka szafa ze zdejmowanym frontem', 'cabinet', [900, 300, 1100], 110, 'removable'),
    ]
    for slug, name, kind, size, depth, opening in specs:
        covers = []
        for face in (['top', 'front'] if kind == 'three_piece' else ['front' if kind == 'cabinet' else 'top']):
            covers.append(dict(id=face, label='Wieko górne' if face == 'top' else 'Pokrywa przednia',
                face=face, depth_mm=depth if face == 'top' else 110, kind=opening,
                hinge_edge='high', requires=[], height_override=False))
        d = dict(schema='rockpro.configurator/3', name='Przegląd 27.10 · '+name, type=kind,
                 internal_mm=size, thickness_mm=9.8, cooperation='sequence' if kind == 'three_piece' else 'independent',
                 covers=covers, hardware=[dict(part_id=p, revision=1) for p in ['H7159', '17251S', '27095']], placements=[])
        d['placements'].append(dict(id='uchwyty-boczne', part_id='H7159', revision=1,
            section_id='body', face='left', u=.5, v=.46, rotation_deg=0,
            pattern='symmetric', count_per_wall=2, handles_per_wall=2, opposite_wall=True, spread=.55))
        if slug == '08-plytka-szafa':
            # Explicit review variant: a centred handle on each shallow side.
            d['name'] += ' · po jednym uchwycie na bok'
            d['placements'][0].update(pattern='single',count_per_wall=1,handles_per_wall=1)
        model = configurator.preview(d)
        from rockpro_cad.studio_closures import lines
        from rockpro_cad.studio_placement import faces
        seams = lines(d, model['sections'], faces(model['sections'], model['panels']))
        # Complete hardware only. Latches on opposite side edges of a removable
        # front; otherwise one retaining row per face of the relevant cover.
        for seam in seams:
            if seam['roles'] == ['hinges']:
                part, count = '27095', 3 if kind == 'cabinet' else 2
            else:
                keep = (seam['face'] == 'front' if kind == 'case' else
                        seam['face'] == 'left' if kind == 'cabinet' and opening == 'hinged' else
                        seam['face'] in ('left', 'right') if seam['cover_id'] == 'front' else
                        seam['face'] == 'rear')
                if not keep:
                    continue
                part, count = '17251S', 2
            d['placements'].append(dict(id='rzad-'+seam['id'], part_id=part, revision=1,
                pattern='closure_line', seam_id=seam['id'], count=count,
                edge_inset_mm=100, clearance_mm=5, avoid_handles=True))
        yield slug, d


def native_spec(d):
    """Derive and independently check affine panel formulas from the Studio model."""
    names = ['RP_Szerokosc_wnetrza', 'RP_Glebokosc_wnetrza', 'RP_Wysokosc_wnetrza', 'RP_Grubosc_sklejki']
    names += ['RP_Wysokosc_wieka_gornego' if c['face']=='top' else 'RP_Glebokosc_pokrywy_przedniej' for c in d['covers']]
    def values(x):
        return x['internal_mm']+[x['thickness_mm']]+[c['depth_mm'] for c in x['covers']]
    def altered(x, i, delta):
        x = copy.deepcopy(x)
        if i < 3: x['internal_mm'][i] += delta
        elif i == 3: x['thickness_mm'] += delta
        else: x['covers'][i-4]['depth_mm'] += delta
        return x
    model = configurator.preview(d);base = model['panels']; v = values(d)
    sections={s['id']:s for s in model['sections']}
    derivatives = [configurator.preview(altered(d, i, .1))['panels'] for i in range(len(v))]
    panels = []
    for k, panel in enumerate(base):
        section=sections[panel['section']];axis=panel['size_mm'].index(min(panel['size_mm']))
        sign=panel['center_mm'][axis] > section['position_mm'][axis]+section['size_mm'][axis]/2
        face=[['Lewa','Prawa'],['Przód','Tył'],['Dno','Płyta górna']][axis][int(sign)]
        spec = dict(id='panel-'+str(k+1), section=panel['section'],label='RockPro | '+section['label']+' | '+face)
        for field in ['size_mm', 'center_mm']:
            formulas = []
            for axis in range(3):
                coefficients = [round((p[k][field][axis]-panel[field][axis])/.1, 6) for p in derivatives]
                const = round(panel[field][axis]-sum(a*b for a,b in zip(coefficients, v)), 6)
                formulas.append(dict(constant=const, coefficients=coefficients))
            spec[field] = panel[field]; spec[field+'_formulas'] = formulas
        panels.append(spec)
    changed = copy.deepcopy(d)
    changed['internal_mm'] = [n+37+11*i for i,n in enumerate(d['internal_mm'])]
    changed['thickness_mm'] += .4
    for c in changed['covers']: c['depth_mm'] += 3
    actual = configurator.preview(changed)['panels']; changed_values = values(changed)
    for k,p in enumerate(panels):
        for field in ['size_mm','center_mm']:
            for axis,f in enumerate(p[field+'_formulas']):
                calculated = f['constant']+sum(a*b for a,b in zip(f['coefficients'], changed_values))
                assert abs(calculated-actual[k][field][axis]) < 1e-5, (k,field,axis)
    return dict(name=d['name'], parameters=dict(zip(names, v)), panels=panels,
                changed_parameters=dict(zip(names,changed_values)), changed_panels=actual,
                status='concept_panels_only_not_manufacturing', formula_check='PASS')


def prepare(folder):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    index_path = folder/'index.json'
    index = json.loads(index_path.read_text(encoding='utf-8')) if index_path.exists() else []
    by_slug = {r['slug']:r for r in index}
    def fingerprint(d):
        return hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    for slug, draft in examples():
        preview = configurator.preview(draft)
        if preview['placement']['unresolved_groups']:
            raise ValueError((slug, preview['placement']))
        if slug not in by_slug:
            saved = configurator.save_draft(draft)
            by_slug[slug] = dict(slug=slug, id=saved['id'], revision=saved['revision'], name=draft['name'],payload_sha256=fingerprint(draft))
            # Persist each ID immediately, so restart cannot create duplicate drafts.
            index_path.write_text(json.dumps(list(by_slug.values()),ensure_ascii=False,indent=2),encoding='utf-8')
        else:
            saved = configurator.read_draft(by_slug[slug]['id'])
            if saved['draft'] != draft:
                # Only update IDs owned by this explicit series and preserve history.
                if (fingerprint(saved['draft']) != by_slug[slug].get('payload_sha256')
                        or saved['revision'] != by_slug[slug]['revision']):
                    raise ValueError('Draft ownership changed')
                saved = configurator.save_draft(draft,saved['id'],saved['revision'])
                by_slug[slug].update(revision=saved['revision'],name=draft['name'],payload_sha256=fingerprint(draft))
                index_path.write_text(json.dumps(list(by_slug.values()),ensure_ascii=False,indent=2),encoding='utf-8')
        item = folder/slug;item.mkdir(exist_ok=True)
        for name,data in [('draft',draft),('preview',preview),('native-spec',native_spec(draft))]:
            (item/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        by_slug[slug]['payload_sha256']=fingerprint(draft)
    index_path.write_text(json.dumps(list(by_slug.values()),ensure_ascii=False,indent=2),encoding='utf-8')
    return list(by_slug.values())


if __name__ == '__main__':
    print(json.dumps(prepare(sys.argv[1]), ensure_ascii=True, indent=2))
