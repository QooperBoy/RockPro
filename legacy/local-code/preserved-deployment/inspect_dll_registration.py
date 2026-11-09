import re
from pathlib import Path
p=Path('C:/Program Files/IronCAD/2027/bin/3iICApiIronCADApp.dll').read_bytes()
for s in re.findall(rb'[\x20-\x7e]{8,}',p):
 if any(x in s for x in [b'TypeLib',b'Version',b'ForceRemove',b'NoRemove']):print(s.decode()[:1400])
