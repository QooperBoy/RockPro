"""Explicit concept definitions for the requested Penn/Adam Hall trial case.

These are dimensioned display approximations, never vendor CAD or machining
templates. The workbook IDs remain separate from the manufacturer's aliases.
"""
import copy
from .part_registry import metadata

CORNER='company-88ca29c4ec2022f584744289'
LATCH='company-b8d4a19822bee54dd25fb45c'
VENT='company-571e67a4f8e9612075691fec'
FEET='company-50307bd783fc65c13932ee12'
ANGLE='concept-angle-30'
KIT='penn-30-rubber-feet-v1'
PDF='https://media.penn-elcom.com/pdf/Penn%20Elcom%20-%20European%20Catalogue%202019.pdf'
SPECS=[
 (CORNER,'PN - C1339/30Z','Narożnik kulowy C1339/30Z · offset 30 mm','corners',[67,67],PDF+'#page=42'),
 (LATCH,'PN - 944/537/10MOL3K','Zamek wpuszczany MOL3 · czarny · miska 10 mm','latches',[127,174],
  'https://www.penn-elcom.com/pl/duzy-czarny-wpuszczany-mol3-zatrzask-w-plytkiej-misce-z-przesunieciem-27mm-l944-537-10mol3k'),
 (VENT,'PM - D0536/07K','Wentylacja D0536/07K · czarna · pionowa','vents',[178,127],PDF+'#page=99'),
 (FEET,'AH - 4903M8AH','Nóżka gumowa Ø20 × 9 mm · opakowanie 8 szt.','feet',[20,20],
  'https://www.adamhall.com/shop/pl/marki/4903-m8-ah-4903m8ah'),
 (ANGLE,None,'Kątownik 30 × 30 mm · profil do doboru','profiles',[30,30],PDF+'#page=41'),
]

def definitions():
    rows=[]
    for key,sku,name,family,envelope,url in SPECS:
        row=dict(id=key,revision=1,sku=sku,name=name,manufacturer='Adam Hall' if key==FEET else 'Penn Elcom' if sku else None,
          aliases=['L944/537/10MOL3K'] if key==LATCH else [],description=name,
          note='Uproszczona bryła koncepcyjna, nie CAD producenta. Dokładny montaż i wycięcia wymagają potwierdzenia.'+
               (' Wymiary 178 × 127 mm według rysunku wariantu /07Z; wariant /07K wymaga potwierdzenia.' if key==VENT else '')+
               (' Przekrój nominalny, brak zatwierdzonego SKU i detali złącza.' if key==ANGLE else ''),
          source_url=url,source_document='Karta producenta / katalog Penn 2019',source_checked_on='2026-10-28',
          selectable=True,selection_blocker=None,cutout_status='required' if key in (LATCH,VENT) else 'unknown',
          mounting_status='unconfirmed',geometry_status='dimensioned_concept_not_vendor_cad',
          purchase_unit='opakowanie 8 szt.' if key==FEET else None,pack_size=8 if key==FEET else 1,
          automatic_placement_approved=False,production_approved=False,concept_envelope_mm=envelope,**metadata(family))
        if key!=ANGLE:row['pricing_company_id']=key
        rows.append(row)
    return copy.deepcopy(rows)

def draft():
    """A separate review project. Dimensions are internal; lid is additional."""
    placements=[dict(id='corner-handles',part_id='H2026',revision=1,section_id='top',face='left',u=.5,
        v=(115-36.1)/115,rotation_deg=0,pattern='symmetric',count_per_wall=2,
        opposite_wall=True,spread=.40,handles_per_wall=2),
        dict(id='ventilation',part_id=VENT,revision=1,section_id='body',face='left',u=.5,v=.48,
        rotation_deg=0,pattern='single',count_per_wall=1,opposite_wall=True,spread=0),
        *[dict(id='locks-'+face,part_id=LATCH,revision=1,pattern='closure_line',seam_id='seam-top-'+face,
          count=2,edge_inset_mm=205,clearance_mm=5,avoid_handles=True) for face in ('front','rear')]]
    return dict(schema='rockpro.configurator/3',name='RockPro · zestaw Penn / Adam Hall · 800 × 650 × 800',
      type='case',internal_mm=[800,650,800],thickness_mm=9.8,cooperation='independent',
      covers=[dict(id='top',label='Wieko zdejmowane',face='top',depth_mm=115,kind='removable',hinge_edge='high',requires=[],height_override=False)],
      hardware=[dict(part_id=p,revision=1) for p in ['H2026',CORNER,LATCH,VENT,FEET,ANGLE]],
      placements=placements,construction=dict(enabled=True,wheels=False,stacking=False,kit=KIT))

def construction(d,sections,placement):
    """Positive corner orientations and eight feet below the floor, no scaled hardware."""
    body,lid=sections;w,depth,h=body['size_mm'];height=h+lid['size_mm'][2];rows=[]
    def add(key,part,family,section,pos,axes,**extra):
        rows.append(dict(id=key,part_id=part,section_id=section,position_mm=pos,rotation=axes,**metadata(family),**extra))
    # Canonical corner occupies the positive octant. Rotations (not reflections)
    # select each of the eight corners; permutation preserves determinant +1.
    for top in (False,True):
      for right in (False,True):
       for rear in (False,True):
        sx=-1 if right else 1;sy=-1 if rear else 1;sz=-1 if top else 1
        axes=[[sx,0,0],[0,sy,0],[0,0,sz]]
        if sx*sy*sz<0:axes[0],axes[1]=axes[1],axes[0]
        add('ball/'+str(int(top))+str(int(right))+str(int(rear)),CORNER,'corners','top' if top else 'body',
            [w if right else 0,depth if rear else 0,height if top else 0],axes)
    # Eight distributed supports = one purchase pack, not eight packs.
    for i,x in enumerate([70,w/2,w-70]):
      for j,y in enumerate([70,depth-70]):
        add(f'foot/{i}/{j}',FEET,'feet','body',[x,y,0],[[1,0,0],[0,-1,0],[0,0,-1]])
    for j,y in enumerate([depth/3,depth*2/3]):
        add(f'foot/middle/{j}',FEET,'feet','body',[w/2,y,0],[[1,0,0],[0,-1,0],[0,0,-1]])
    # Straight 30 mm visual angles, terminated before 67 mm corner envelopes.
    for top,z,section in [(False,0,'body'),(True,height,'top')]:
      s=-1 if top else 1
      for rear in (False,True):
        segments=[(70,w-70)]
        if top:
          face='rear' if rear else 'front'
          for item in placement['items']:
            if item.get('seam_id') and item['face']==face:
              lo=item['position_mm'][0]-item['footprint_mm'][0]/2-5;hi=item['position_mm'][0]+item['footprint_mm'][0]/2+5
              segments=[(a,b) for start,end in segments for a,b in [(start,min(end,lo)),(max(start,hi),end)] if b-a>2]
        for i,(a,b) in enumerate(segments):
          add(f'edge/x/{top}/{rear}/{i}',ANGLE,'profiles',section,[a if s*(-1 if rear else 1)>0 else b,depth if rear else 0,z],
            [[0,-1 if rear else 1,0],[0,0,s],[s*(-1 if rear else 1),0,0]],length_mm=b-a,seed_length_mm=1)
      for right in (False,True):
        add(f'edge/y/{top}/{right}',ANGLE,'profiles',section,[w if right else 0,70 if -s*(-1 if right else 1)>0 else depth-70,z],
          [[-1 if right else 1,0,0],[0,0,s],[0,-s*(-1 if right else 1),0]],length_mm=depth-140,seed_length_mm=1)
    for right in (False,True):
      for rear in (False,True):
        sx=-1 if right else 1;sy=-1 if rear else 1
        axes=[[sx,0,0],[0,sy,0],[0,0,sx*sy]]
        add(f'edge/z/{right}/{rear}',ANGLE,'profiles','body',[w if right else 0,depth if rear else 0,70 if sx*sy>0 else h-35],
          axes,length_mm=h-105,seed_length_mm=1)
    from collections import Counter
    return dict(items=rows,counts=dict(Counter(r['part_id'] for r in rows)),status='dimensioned_concept_not_manufacturing',
      notes=['Uproszczone bryły; profil 30 mm do doboru. Brak produkcyjnych konturów i zatwierdzonego pasowania.'])
