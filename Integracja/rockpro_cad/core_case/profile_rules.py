"""Full-case v2 prototype: fixed-section edge profiles and rigid seam braces.

Independent of the six-parameter skeleton worker. Expressions are native mm.
Catalog geometry is never mirrored or scaled in its transverse directions.
"""
import math
import ast
import operator

PARAMETERS=('RP_Length','RP_Depth','RP_BaseHeight','RP_LidHeight',
            'RP_Thickness','RP_DisplayGap','RP_JointGap')

def value(text,values):
    """Evaluate the authored arithmetic grammar, without exec/eval."""
    ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
    def walk(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):return node.value
        if isinstance(node,ast.Name) and node.id in values:return values[node.id]
        if isinstance(node,ast.BinOp) and type(node.op) in ops:return ops[type(node.op)](walk(node.left),walk(node.right))
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub):return -walk(node.operand)
        raise ValueError('Unsupported dimension expression')
    result=walk(ast.parse(text.replace(' mm',''),mode='eval').body)
    if not math.isfinite(result):raise ValueError('Nonfinite dimension')
    return result

def validate_values(values):
    if set(values)!=set(PARAMETERS):raise ValueError('Full-case v2 requires seven explicit parameters')
    if any(type(v) not in (float,int) or not math.isfinite(v) for v in values.values()):
        raise ValueError('Finite numeric dimensions required')
    L,D,B,H,T,G,J=(values[n] for n in PARAMETERS)
    if not (400<=L<=5000 and 400<=D<=5000 and 120<=B<=5000 and 60<=H<=1000
            and 6<=T<=12 and 0<=G<=1000 and 0<=J<=20 and H-J>60):
        raise ValueError('Dimensions outside the prototype profile envelope')
    return dict(values)

def expression(text,depth=1):
    for n in sorted(PARAMETERS,key=len,reverse=True):
        text=text.replace(n,'Parent\\'*depth+'Params\\'+n)
    return text

def rules():
    L='RP_Length';D='RP_Depth';B='RP_BaseHeight';H='RP_LidHeight'
    G='RP_DisplayGap';J='RP_JointGap';T='RP_Thickness'
    rows=[]
    def add(id,sku,r,center,length=None):
        # All frames are proper rotations; no implicit left/right mirror.
        determinant=sum(r[0][i]*(r[1][(i+1)%3]*r[2][(i+2)%3]-r[1][(i+2)%3]*r[2][(i+1)%3]) for i in range(3))
        if determinant!=1:raise ValueError('Improper profile orientation')
        rows.append(dict(id=id,sku=sku,rotation=r,center=center,cut_length=length,
                         geometry_policy='fixed_cross_section' if length else 'rigid'))
    # Local X/Y are the two equal legs of EG-0113; local Z is cut length.
    top={'front':[[0,-1,0],[0,0,1],[-1,0,0]],'rear':[[0,1,0],[0,0,1],[1,0,0]],
         'left':[[-1,0,0],[0,0,1],[0,1,0]],'right':[[1,0,0],[0,0,1],[0,-1,0]]}
    bottom={'front':[[0,-1,0],[0,0,-1],[1,0,0]],'rear':[[0,1,0],[0,0,-1],[-1,0,0]],
            'left':[[-1,0,0],[0,0,-1],[0,-1,0]],'right':[[1,0,0],[0,0,-1],[0,1,0]]}
    for level,rotations,z in [('bottom',bottom,'15.5 mm'),('top',top,f'{B} + {H} + {G} - 15.5 mm')]:
        centers={'front':[f'{L}/2','15.5 mm',z],'rear':[f'{L}/2',f'{D} - 15.5 mm',z],
                 'left':['15.5 mm',f'{D}/2',z],'right':[f'{L} - 15.5 mm',f'{D}/2',z]}
        for wall in rotations:add(level+'/'+wall,'EG-0113',rotations[wall],centers[wall],f'{L if wall in ("front","rear") else D} - 60 mm')
    vertical={'front-left':[[-1,0,0],[0,-1,0],[0,0,1]],
              'front-right':[[0,-1,0],[1,0,0],[0,0,1]],
              'rear-left':[[0,1,0],[-1,0,0],[0,0,1]],
              'rear-right':[[1,0,0],[0,1,0],[0,0,1]]}
    for half,z,length in [('base',f'{B}/2',f'{B} - 60 mm'),
                          ('lid',f'{B} + {G} + {J} + ({H} - {J})/2',f'{H} - {J} - 60 mm')]:
        for corner,r in vertical.items():
            x=f'{L} - 15.5 mm' if 'right' in corner else '15.5 mm'
            y=f'{D} - 15.5 mm' if 'rear' in corner else '15.5 mm'
            add(half+'/'+corner,'EG-0113',r,[x,y,z],length)
    male={'front':[[0,0,1],[0,-1,0],[1,0,0]],'rear':[[0,0,1],[0,1,0],[-1,0,0]],
          'left':[[0,0,1],[1,0,0],[0,1,0]],'right':[[0,0,1],[-1,0,0],[0,-1,0]]}
    female={'front':[[0,0,-1],[0,1,0],[1,0,0]],'rear':[[0,0,-1],[0,-1,0],[-1,0,0]],
            'left':[[0,0,-1],[-1,0,0],[0,1,0]],'right':[[0,0,-1],[1,0,0],[0,-1,0]]}
    # Z offsets and the 1 mm transverse male/female offset preserve the measured
    # source closure section. JointGap=8.63 mm reproduces source board separation.
    for sku,rotations,inset,z in [('EG-0500_1',male,f'{T}/2 - 1 mm',f'{B} - 6.1004 mm'),
                                  ('EG-0500_2',female,f'{T}/2',f'{B} + {J} + {G} + 4.52154 mm')]:
        centers={'front':[f'{L}/2',inset,z],'rear':[f'{L}/2',f'{D} - ({inset})',z],
                 'left':[inset,f'{D}/2',z],'right':[f'{L} - ({inset})',f'{D}/2',z]}
        for wall,r in rotations.items():add(sku+'/'+wall,sku,r,centers[wall],L if wall in ('front','rear') else f'{D} - 6 mm')
    for half,z in [('base',f'{B} - 20 mm'),('lid',f'{B} + {J} + {G} + 20 mm')]:
        add(half+'/brace-front-right','B1930',[[0,0,1],[0,1,0],[-1,0,0]],
            [f'{L} - 13.55 mm','13.55 mm',z])
        add(half+'/brace-front-left','B1930',[[0,0,1],[1,0,0],[0,1,0]],['13.55 mm','13.55 mm',z])
        add(half+'/brace-rear-right','B1121',[[0,1,0],[0,0,1],[1,0,0]],
            [f'{L} - 10.3 mm',f'{D} - 12.85 mm',z])
        add(half+'/brace-rear-left','B1121',[[-1,0,0],[0,0,1],[0,1,0]],
            ['10.3 mm',f'{D} - 12.85 mm',z])
    return rows
