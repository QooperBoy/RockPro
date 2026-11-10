"""Photo identity/integrity and independent mesh retention, without network."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Integracja'))
from rockpro_cad import manufacturer_images
from fetch_manufacturer_images import identify


class Photos(unittest.TestCase):
    def test_reject_wrong_sku_and_finish(self):
        page='<meta property="og:image" content="https://cdn.adamhall.com/media/1200x1200/article/productbrand_ahhardware/4053/4053_1.jpg">'
        with self.assertRaises(ValueError):identify(page,'AH - 4054','https://www.adamhall.com/shop/pl/4053')
        with self.assertRaises(ValueError):identify(page,'AH - 4053BLK','https://www.adamhall.com/shop/pl/4053')
        self.assertIn('/4053/',identify(page,'AH - 4053','https://www.adamhall.com/shop/pl/4053'))

    def test_unrelated_product_structured_data_and_external_host(self):
        with self.assertRaises(ValueError):identify('<script type="application/ld+json">{"@type":"Product","sku":"4053","image":"https://cdn.adamhall.com/a.jpg"}</script>','4054','https://www.adamhall.com/')
        with self.assertRaises(ValueError):identify('<script type="application/ld+json">{"@type":"Product","sku":"4054","image":"https://other.invalid/a.jpg"}</script>','4054','https://www.adamhall.com/')

    def test_penn_html_product_sku_without_json_sku(self):
        page='<script type="application/ld+json">{"@type":"Product","name":"Brace"}</script><div itemprop="sku">B1930</div><meta property="og:image" content="https://www.penn-elcom.com/media/B1930.jpeg">'
        self.assertTrue(identify(page,'PN - B1930','https://www.penn-elcom.com/brace').endswith('B1930.jpeg'))
        with self.assertRaises(ValueError):identify(page,'PN - B1930K','https://www.penn-elcom.com/brace')
        # Related-product forms must never identify the main product photograph.
        related='<form data-product-sku="D0941/5Z"></form><form data-product-sku="W0968Z"></form><meta property="og:image" content="https://www.penn-elcom.com/media/main.jpg">'
        with self.assertRaises(ValueError):identify(related,'W0968Z','https://www.penn-elcom.com/dish')

    def test_verified_overlay_preserves_mesh_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name);raw=b'\xff\xd8\xffphoto';(folder/'part.jpg').write_bytes(raw)
            index=dict(schema='rockpro.manufacturer-images/1',images={'handle':dict(file='part.jpg',sha256=hashlib.sha256(raw).hexdigest(),manufacturer='Adam Hall',image_url='https://cdn.adamhall.com/photo.jpg',page_url='https://www.adamhall.com/part',checked_at='2026-10-28')})
            (folder/'index.json').write_text(json.dumps(index),encoding='utf-8')
            with patch.dict(os.environ,{'ROCKPRO_MANUFACTURER_IMAGES':name}):
                original={'items':[{'id':'handle','image':{'mesh_url':'part-models/handle.mesh.json','mesh_sha256':'abc','kind':'cad_render'}}]}
                result=manufacturer_images.decorate(original)['items'][0]['image']
                self.assertEqual(result['kind'],'manufacturer_photo');self.assertEqual(result['mesh_sha256'],'abc')
                manufacturer_images._load.cache_clear();(folder/'part.jpg').write_bytes(b'\xff\xd8\xffchanged')
                with self.assertRaises(ValueError):manufacturer_images.routes()


if __name__=='__main__':unittest.main()
