"""Generic complete Studio examples, authored recipes rather than customer models."""
from . import configurator
from .studio_structure import REQUIRED


def catalog():
    examples=[]
    for key,name,dimensions,lid,wheels,handles,closures,description in [
        ('t1-transport','T1 · skrzynia transportowa',[600,500,800],115,True,2,2,
         'Cztery koła, gniazda do piętrowania i po dwa uchwyty na przeciwległych bokach.'),
        ('t1-large','T1 · duża skrzynia transportowa',[900,700,900],125,True,3,3,
         'Większy korpus, sześć uchwytów oraz po trzy zatrzaski i zawiasy.'),
        ('t1-carry','T1 · skrzynia bez kół',[600,450,800],110,False,1,2,
         'Wariant bez podwozia: po jednym wyśrodkowanym uchwycie na przeciwległych bokach.'),
    ]:
        hardware=['H7159','17251S','270836',*REQUIRED]+(['source-caster-epson','W0968Z'] if wheels else [])
        d=dict(schema='rockpro.configurator/3',name=name,type='case',internal_mm=dimensions,thickness_mm=9.8,
               cooperation='independent',covers=[dict(id='top',label='Wieko górne',face='top',depth_mm=lid,
               kind='hinged',hinge_edge='high',requires=[],height_override=False)],
               hardware=[dict(part_id=p,revision=1) for p in hardware],
               construction=dict(enabled=True,wheels=wheels,stacking=wheels),placements=[
                 dict(id='handles-sides',part_id='H7159',revision=1,section_id='body',face='left',u=.5,v=.46,
                      rotation_deg=0,pattern='single' if handles==1 else 'symmetric',count_per_wall=handles,
                      opposite_wall=True,spread=.6 if handles==3 else .5,handles_per_wall=handles),
                 *[dict(id='row-'+face,part_id=part,revision=1,pattern='closure_line',seam_id='seam-top-'+face,
                       count=closures,edge_inset_mm=150,clearance_mm=5,avoid_handles=True)
                   for face,part in [('front','17251S'),('rear','270836')]]])
        preview=configurator.preview(d)
        if preview['placement']['unresolved_groups'] or any(w['code']!='closure_reference' for w in preview['placement']['warnings']):
            raise ValueError('Example has unresolved mounting: '+key)
        examples.append(dict(id=key,name=name,description=description,internal_mm=dimensions,lid_mm=lid,
            total_count=preview['project_summary']['total_count'],handles=handles*2,closures=closures,
            wheels=4 if wheels else 0,image='examples/'+key+'.png',draft=d))
    return dict(schema='rockpro.studio-examples/1',items=examples)
