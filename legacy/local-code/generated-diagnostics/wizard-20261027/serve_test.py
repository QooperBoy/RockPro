import pathlib,sys
root=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'Integracja'))
from rockpro_cad.mcp import project_store
from rockpro_cad.reference_studio import make_handler
from http.server import ThreadingHTTPServer
project_store.DB_PATH=pathlib.Path(__file__).with_name('browser-test.sqlite3')
server=ThreadingHTTPServer(('127.0.0.1',51343),make_handler({}, {}, 'wizard_test_session_20261027'))
print('http://127.0.0.1:51343/wizard_test_session_20261027/wizard.html',flush=True)
server.serve_forever()
