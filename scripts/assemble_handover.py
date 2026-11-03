"""Assemble unpacked RockPro delivery without installing software or touching CAD."""
from pathlib import Path
import argparse, shutil

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--code',type=Path,required=True)
    p.add_argument('--parts',type=Path,required=True)
    p.add_argument('--models',type=Path,required=True)
    p.add_argument('--dest',type=Path,required=True)
    a=p.parse_args()
    if a.dest.exists():p.error('Destination must not exist; existing work is never overwritten.')
    for src in [a.code/'01_KOD_GLOWNY',a.parts/'DO_WGRANIA_DO_KODU',a.models/'DO_WGRANIA_DO_KODU']:
        if not src.is_dir():p.error('Missing input: '+str(src))
    source=a.dest/'Transfer_RockPro_20261024/RockPro/rockpro-cad'
    shutil.copytree(a.code/'01_KOD_GLOWNY',source)
    for package in (a.parts,a.models):
        shutil.copytree(package/'DO_WGRANIA_DO_KODU',source,dirs_exist_ok=True)
    launch='''from pathlib import Path
import sys
root=Path(__file__).resolve().parent
source=root/'Transfer_RockPro_20261024/RockPro/rockpro-cad'
sys.path.insert(0,str(source/'Integracja'))
sys.argv=[sys.argv[0],'--bundle',str(source/'artifacts/model-library-20261026'),'--previews',str(source/'artifacts/family-3d-20261027/index.json'),'--database',str(root/'studio-local.sqlite'),*sys.argv[1:]]
from rockpro_cad.reference_studio import main
main()
'''
    (a.dest/'uruchom_studio.py').write_text(launch,encoding='utf-8')
    print(source)

if __name__=='__main__':main()
