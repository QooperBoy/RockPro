import json,pathlib,urllib.request,re
out=pathlib.Path('artifacts/part-images-20261027')
model=str(pathlib.Path('artifacts/registry-native-20261024-01/viewer/model.json').resolve())
roots={'H7159':[1726],'17251S':[192,380],'EG-0113':[1050],'EG-0500/1':[1146],'EG-0500/2':[1170],'410429':[42],'B1930':[1194],'B1121':[1202],'W0968Z':[1586],'source-caster-epson':[1552]}
items=[dict(id=k,filename=k.replace('/','-'),model=model,roots=v,direction=[-3,-2,1.5] if k=='H7159' else [1,-2,1.6],source='Wyodrębniony element z zapisanego eksportu prototypu T1; wyłącznie podgląd.')for k,v in roots.items()]
(out/'mapping.json').write_text(json.dumps(dict(items=items)),encoding='utf-8')
urls={'H2026':'https://www.penn-elcom.com/us/corner-handle-with-tight-radius-h2026-series','27095':'https://www.adamhall.com/shop/en/recessed-lid-stays/27095-27095','270836':'https://www.adamhall.com/shop/en/recessed-lid-stays/270836-270836'}
for key,url in urls.items():
 try:
  s=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25).read().decode()
  (out/(key+'.html')).write_text(s,encoding='utf-8')
  links=list(dict.fromkeys(re.findall(r'https[^\s<>"\x27]+(?:jpg|png|webp)[^\s<>"\x27]*',s)))
  print(key,[x for x in links if key.lower()in x.lower()][:12])
 except Exception as e: print(key,str(e))
