import pathlib,re,urllib.request,json,hashlib
out=pathlib.Path('artifacts/studio-part-images');s=pathlib.Path('artifacts/part-images-20261027/27095.html').read_text(encoding='utf-8');urls=list(dict.fromkeys(re.findall(r'https[^\s<>"\x27]+27095[^\s<>"\x27]*\.jpg[^\s<>"\x27]*',s)))
for u in urls:
 try:
  raw=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=12).read()
  if not raw.startswith(b'\xff\xd8\xff'):continue
  (out/'27095.jpg').write_bytes(raw);data=json.loads((out/'index.json').read_text(encoding='utf-8'));data['images']['27095']=dict(file='27095.jpg',sha256=hashlib.sha256(raw).hexdigest(),kind='manufacturer_photo',label='Zdjęcie producenta · Adam Hall',source=dict(url=u,page_url='https://www.adamhall.com/shop/en/recessed-lid-stays/27095-27095',description='Zdjęcie katalogowe producenta, nie render lokalnego modelu.'));(out/'index.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');print('27095 downloaded',len(raw));break
 except Exception as e: print(str(e),u[:95])
