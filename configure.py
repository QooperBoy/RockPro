"""Rebase the demo and MCP configuration after extraction. Does not change CAD."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
base=root/'Integracja'
folder=base/'skeleton/demo'
manifest=json.loads((folder/'skeleton_manifest.template.json').read_text(encoding='utf-8'))
manifest['file']=str(folder/'RockPro_Epson_szkielet_MVP.ics')
(folder/'skeleton_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(base/'skeleton_state.json').write_text(json.dumps({'folder':str(folder)},ensure_ascii=False,indent=2),encoding='utf-8')
config={'mcpServers':{'rockpro-cad':{'command':str(base/'.venv/Scripts/python.exe'),'args':[str(base/'rockpro_cad/mcp/server.py')]}}}
(root/'mcp-config.local.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print('Local paths configured.')
