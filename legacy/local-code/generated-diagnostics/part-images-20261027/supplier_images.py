import json,pathlib,urllib.request,hashlib
out=pathlib.Path('artifacts/studio-part-images');data=json.loads((out/'index.json').read_text())
urls={key:f'https://cdn.adamhall.com/media/600x600/article/productbrand_ahhardware/{key}/{key}_1.jpg?c=179487b7749ec348c0a0bb710e0c13c2'for key in ('27095','270836')}
urls['H2026']='https://www.penn-elcom.com/media/catalog/product/cache/6964484727c91d8a7ee1545fdc866f01/H/2/H2026Series_H2026-00.jpg'
for key,url in urls.items():
 try:
  raw=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.adamhall.com/' if key!='H2026' else 'https://www.penn-elcom.com/'}),timeout=25).read();assert raw.startswith(b'\xff\xd8\xff');name=key+'.jpg';(out/name).write_bytes(raw)
  brand='Penn Elcom' if key=='H2026' else 'Adam Hall'
  page='https://www.penn-elcom.com/us/corner-handle-with-tight-radius-h2026-series' if key=='H2026' else f'https://www.adamhall.com/shop/en/recessed-lid-stays/{key}-{key}'
  data['images'][key]=dict(file=name,sha256=hashlib.sha256(raw).hexdigest(),kind='manufacturer_photo',label='Zdjęcie producenta · '+brand,source=dict(url=url,page_url=page,description='Zdjęcie katalogowe producenta, nie render lokalnego modelu.'))
  print(key,'downloaded',len(raw))
 except Exception as e: print(key,e)
(out/'index.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
