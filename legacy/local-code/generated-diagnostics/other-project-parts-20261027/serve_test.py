import pathlib,sys
root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'Integracja'))
from rockpro_cad import part_images
from rockpro_cad.mcp import project_store
from rockpro_cad.reference_studio import make_handler
from http.server import ThreadingHTTPServer
project_store.DB_PATH=pathlib.Path(__file__).with_name('test.sqlite3')
images=part_images.load(root/'artifacts/studio-part-images');images.update(part_images.load(root/'artifacts/studio-project-parts/images'))
server=ThreadingHTTPServer(('127.0.0.1',51343),make_handler({}, {}, 'wizard_source_parts_20261027',hardware_images=images))
print('source test server ready',flush=True);server.serve_forever()
