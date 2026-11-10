"""Read official public product pages and inventory available CAD links.

No credentials, login replay, download endpoint guessing or CAD host access.
Raw product pages and resumable per-record evidence remain local under artifacts.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

HOSTS = {'www.penn-elcom.com', 'www.adamhall.com'}

def normalized(code):
    return re.sub('[^A-Z0-9]', '', re.sub(r'^(?:AH|PN|PM)\s*[-–]\s*', '', (code or '').strip().upper()))

class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.skus=[];self.primary_sku=None;self.image=None;self.h1=[];self.in_h1=False;self.in_json=False;self.json_text=[];self.sku_tag=None;self.sku_text=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='a' and attrs.get('href'):self.links.append(unescape(attrs['href']))
        if attrs.get('data-product-sku'):self.skus.append(attrs['data-product-sku'])
        if attrs.get('id')=='product_addtocart_form':self.primary_sku=attrs.get('data-product-sku')
        if attrs.get('itemprop')=='sku' and attrs.get('content'):self.skus.append(attrs['content'])
        if attrs.get('itemprop')=='sku' and not attrs.get('content'):self.sku_tag=tag;self.sku_text=[]
        if tag=='meta' and attrs.get('property')=='og:image':self.image=attrs.get('content')
        if tag=='h1':self.in_h1=True
        if tag=='script' and attrs.get('type')=='application/ld+json':self.in_json=True;self.json_text=[]
    def handle_data(self,data):
        if self.in_h1:self.h1.append(data)
        if self.in_json:self.json_text.append(data)
        if self.sku_tag:self.sku_text.append(data)
    def handle_endtag(self,tag):
        if tag=='h1':self.in_h1=False
        if self.sku_tag==tag:
            sku=''.join(self.sku_text).strip();self.skus.append(sku)
            if not self.primary_sku:self.primary_sku=sku
            self.sku_tag=None
        if tag=='script' and self.in_json:
            self.in_json=False
            try:self.product(json.loads(''.join(self.json_text)))
            except ValueError:pass
    def product(self,x):
        if isinstance(x,list):
            for y in x:self.product(y)
        elif isinstance(x,dict):
            if x.get('@type')=='Product' and x.get('sku') and not self.primary_sku:self.primary_sku=x['sku']
            if '@graph' in x:self.product(x['@graph'])

def download_metadata(html):
    """Published Nuxt hydration data contains the same visible download table."""
    m=re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>',html,re.S)
    if not m:return []
    a=json.loads(m[1]);result=[]
    if not isinstance(a,list):return result
    for v in a:
        if isinstance(v,dict) and all(k in v for k in ('format','file','id','categoryId')):
            row={}
            for k,x in v.items():row[k]=a[x] if type(x) is int and 0<=x<len(a) else x
            result.append(row)
    return result

def scan(row,root):
    result={k:row.get(k) for k in ('id','code','name','manufacturer','category','source_url')}
    result.update(checked_at=datetime.now(timezone.utc).isoformat(),production_approved=False)
    url=row.get('source_url')
    if not url:
        result['status']='supplier_or_product_url_missing';return result
    if urlsplit(url).scheme!='https' or urlsplit(url).hostname not in HOSTS:
        result['status']='other_supplier_requires_lookup';return result
    cache=root/'pages'/(row['id']+'.json');html_path=cache.with_suffix('.html')
    try:
        if cache.exists() and html_path.exists():
            cached=json.loads(cache.read_text(encoding='utf-8'));raw=html_path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=cached['sha256']:raise ValueError('Cached page hash mismatch')
            final=cached['url']
        else:
            with urlopen(Request(url,headers={'User-Agent':'RockPro-CAD-Catalog/1.0'}),timeout=25) as response:
                final=response.url
                if urlsplit(final).hostname not in HOSTS:raise ValueError('Unexpected redirect host')
                raw=response.read(6*1024*1024+1)
            if len(raw)>6*1024*1024:raise ValueError('Page exceeds limit')
            html_path.write_bytes(raw);cache.write_text(json.dumps(dict(url=final,sha256=hashlib.sha256(raw).hexdigest())),encoding='utf-8')
        text=raw.decode('utf-8');page=Page();page.feed(text)
        if not page.primary_sku and urlsplit(final).hostname=='www.adamhall.com':page.primary_sku=''.join(page.h1).strip()
        expected=normalized(row['code']);explicit={normalized(page.primary_sku)} if page.primary_sku else set()
        if explicit:identity='exact' if explicit=={expected} else 'different_product_or_variant'
        elif page.image and urlsplit(final).hostname=='www.adamhall.com':
            identity='exact' if any(normalized(p)==expected for p in urlsplit(page.image).path.split('/')) else 'unconfirmed'
        else:identity='unconfirmed'
        links=sorted(set(urljoin(final,x) for x in page.links))
        cad=[u for u in links if '3dcontentcentral.com/' in u.lower() or re.search(r'\.(?:step|stp|igs|iges|stl|x_t|sat|sldprt|zip)(?:[?#]|$)',u,re.I)]
        docs=download_metadata(text)
        three=[d for d in docs if re.search(r'3d|step|stp|iges|solid|parasolid',str(d.get('file',''))+' '+str(d.get('typ',''))+' '+str(d.get('format','')),re.I)]
        result.update(final_url=final,page_file=str(html_path.resolve()),page_sha256=hashlib.sha256(raw).hexdigest(),identity=identity,primary_manufacturer_sku=page.primary_sku,manufacturer_skus=sorted(page.skus),cad_links=cad,downloads=docs,cad_download_metadata=three)
        result['status']='cad_link_found' if cad or three else 'no_3d_link_in_official_product_downloads'
        if identity=='different_product_or_variant':result['status']='source_product_mismatch'
    except Exception as e:result.update(status='page_unavailable',error=type(e).__name__+': '+str(e)[:250])
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('output',type=Path);p.add_argument('--workers',type=int,default=3);args=p.parse_args()
    if args.workers not in range(1,5):raise ValueError('Use at most four public-page workers')
    (args.output/'pages').mkdir(parents=True,exist_ok=True)
    items=json.loads(args.catalog.read_text(encoding='utf-8'))['items'];results=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(lambda x:scan(x,args.output),items):
            results.append(row)
            (args.output/'progress.json').write_text(json.dumps(dict(done=len(results),total=len(items),last_code=row['code'])),encoding='utf-8')
    from collections import Counter
    report=dict(schema='rockpro.company-cad-discovery/1',catalog_sha256=hashlib.sha256(args.catalog.read_bytes()).hexdigest(),items=results,summary=dict(Counter(r['status'] for r in results)))
    (args.output/'discovery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report['summary']))
if __name__=='__main__':main()
