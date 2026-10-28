"""Fetch explicit manufacturer product photos; reject unrelated SKU pages.

No search-engine guessing, login, access-control bypass, or workbook edits.
Outputs an optional, local presentation overlay and a per-item result report.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, urljoin, unquote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Integracja'))
from rockpro_cad import studio_parts


def code(value):
    return re.sub(r'[^A-Z0-9]', '', re.sub(r'^(AH|PN)\s*[-–]\s*', '', value.upper()))


class ProductMeta(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta = {}; self.products = []
        self.in_json = False; self.script = []; self.skus = []; self.sku_tag = None; self.form_sku = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta': self.meta[attrs.get('property',attrs.get('name',''))] = attrs.get('content','')
        if attrs.get('data-product-sku') and self.form_sku is None: self.form_sku = attrs['data-product-sku']
        if attrs.get('itemprop') == 'sku':
            if attrs.get('content'): self.skus.append(attrs['content'])
            else: self.sku_tag = tag
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.in_json = True; self.script = []
    def handle_data(self, data):
        if self.in_json: self.script.append(data)
        if self.sku_tag: self.skus.append(data.strip())
    def handle_endtag(self, tag):
        if tag == self.sku_tag: self.sku_tag = None
        if tag == 'script' and self.in_json:
            self.in_json = False
            try: self.walk(json.loads(''.join(self.script)))
            except ValueError: pass
    def walk(self, item):
        if isinstance(item,list):
            for x in item: self.walk(x)
        elif isinstance(item,dict):
            if item.get('@type') == 'Product': self.products.append(item)
            if '@graph' in item: self.walk(item['@graph'])


def allowed(url, photo=False):
    parsed = urlsplit(url)
    return parsed.scheme == 'https' and parsed.hostname in (
        ('www.adamhall.com','cdn.adamhall.com','www.penn-elcom.com','media.penn-elcom.com') if photo
        else ('www.adamhall.com','www.penn-elcom.com'))


def fetch(url, limit):
    with urlopen(Request(url, headers={'User-Agent':'RockPro-Product-Catalog/1.0'}), timeout=18) as response:
        if not allowed(response.url, True): raise ValueError('Unexpected redirect host')
        data = response.read(limit+1)
        if len(data)>limit: raise ValueError('Response too large')
        return data, response.url


def identify(page, expected, page_url):
    parser=ProductMeta(); parser.feed(page)
    explicit_skus = [s for s in parser.skus if s] or [str(p['sku']) for p in parser.products if p.get('sku')] or ([parser.form_sku] if parser.form_sku else [])
    exact = [p for p in parser.products if p.get('sku') and code(str(p['sku'])) == code(expected)]
    identity = bool(explicit_skus) and {code(s) for s in explicit_skus} == {code(expected)}
    if explicit_skus and not identity: raise ValueError('Product SKU differs from catalogue code')
    image=parser.meta.get('og:image')
    if not identity:
        # Adam Hall image path carries the exact full SKU, including finish suffix.
        path = unquote(urlsplit(image or '').path).split('/')
        if urlsplit(page_url).hostname != 'www.adamhall.com' or not any(code(x)==code(expected) for x in path):
            raise ValueError('No exact product identity in structured data or manufacturer image path')
    if not image and exact:
        image=exact[0].get('image')
        if isinstance(image,list): image=image[0] if image else None
        if isinstance(image,dict): image=image.get('url')
    if not image: raise ValueError('No product image')
    image=urljoin(page_url,image)
    if not allowed(image,True): raise ValueError('Unapproved image host')
    return image


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,default=ROOT/'artifacts/manufacturer-images')
    ap.add_argument('--company',type=Path,default=ROOT/'artifacts/erp-company-parts/catalog.json'); args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    targets=[dict(id=r['id'],code=r.get('sku') or '',manufacturer=r.get('manufacturer'),url=r.get('source_url')) for r in studio_parts.catalog()['items'] if not r.get('source_project')]
    if args.company.exists():
        targets += [dict(id=r['id'],code=r['code'],manufacturer=r['manufacturer'],url=r.get('source_url')) for r in json.loads(args.company.read_text(encoding='utf-8'))['items']]
    index_path=args.output/'index.json'
    images=json.loads(index_path.read_text(encoding='utf-8'))['images'] if index_path.exists() else {}
    def run(row):
        if row['id'] in images: return row['id'],dict(status='cached'),images[row['id']]
        if not row['url'] or not allowed(row['url']): return row['id'],dict(status='no_manufacturer_product_url'),None
        try:
            page,page_url=fetch(row['url'],3*1024*1024)
            image_url=identify(page.decode('utf-8'),row['code'],page_url)
            raw,image_url=fetch(image_url,2*1024*1024)
            suffix='.png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if raw.startswith(b'\xff\xd8\xff') else None
            if not suffix: raise ValueError('Not a supported raster photo')
            digest=hashlib.sha256(raw).hexdigest(); filename=digest[:24]+suffix
            (args.output/filename).write_bytes(raw)
            photo=dict(file=filename,sha256=digest,manufacturer=row['manufacturer'],code=row['code'],
                       page_url=page_url,image_url=image_url,checked_at=datetime.now(timezone.utc).isoformat())
            return row['id'],dict(status='downloaded',code=row['code']),photo
        except Exception as exc:
            return row['id'],dict(status='unavailable',code=row['code'],reason=str(exc)[:220],url=row['url']),None
    report={}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for key,result,photo in pool.map(run,targets):
            report[key]=result
            if photo: images[key]=photo
    index_path.write_text(json.dumps(dict(schema='rockpro.manufacturer-images/1',images=images),ensure_ascii=False,indent=2),encoding='utf-8')
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    from collections import Counter
    print(json.dumps(dict(photos=len(images),results=dict(Counter(r['status'] for r in report.values())))))


if __name__=='__main__': main()
