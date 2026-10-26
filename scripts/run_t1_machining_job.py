"""Private development runner: pinned local bridge, existing host, one CAD writer."""
import sys,json,shutil,hashlib,re,subprocess,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.icapi_runtime import selected_year, installation_dir
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(folder,source,request):
    request=dict(request)
    request["expected_api_major"]=selected_year()-1998
    if request.get('mode')=='build':
        from rockpro_cad.core_case.machining_rules import validate_layout,validate_steps
        validate_layout(request['parameters'])
        validate_steps(request['cuts'],{m['key'] for m in request['mounts']}|{'stacking_sockets/'+side+'/'+end for side in ('left','right') for end in ('front','rear')})
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    loader=ROOT/'artifacts/latch17251-inprocess-native-20261022-09/LatchApiProbe.dll'
    if sha(loader)!='0b83e25991b23a94ef723ad2fc58ac1e7e08e815913751c779cad891797d79cb':raise ValueError('Unrecognized native bridge')
    names=re.findall(r'LatchInProcess[^\x00]{0,90}\.dll',loader.read_bytes().decode('utf-16-le',errors='ignore'))
    if len(names)!=1:raise ValueError('Ambiguous fixed managed loader name')
    vendor=installation_dir()/'ICAPI/Samples/C#/References/interop.ICApiIronCAD.dll'
    src=Path(source).resolve();built=folder/('Machining_'+sha(src)[:20]+'.dll')
    cmd=['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/target:library','/platform:x64','/out:'+str(built),'/reference:'+str(vendor),'/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll',str(src)]
    c=subprocess.run(cmd+['/utf8output'],capture_output=True,text=True,encoding='utf-8',errors='replace')
    (folder/'compile.json').write_text(json.dumps({'returncode':c.returncode,'stdout':c.stdout,'stderr':c.stderr,'source_sha256':sha(src),'loader_sha256':sha(loader)}),encoding='utf-8')
    if c.returncode:raise RuntimeError(c.stdout+c.stderr)
    shutil.copyfile(built,folder/names[0]);shutil.copyfile(vendor,folder/vendor.name);shutil.copyfile(loader,folder/loader.name)
    (folder/'request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
    import comtypes.client
    IronCAD=comtypes.client.GetModule(str(installation_dir()/"bin/IronCad.tlb"))
    app=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True)
    collection=app.AddOns;raw=collection._comobj
    def disp(x):return x._comobj if hasattr(x,'_comobj') else x
    owner='RockProMachining_'+uuid.uuid4().hex
    a=None
    cleanup={}
    with cad_writer_lock():
        count=int(collection.Count)
        try:
            a=disp(raw._invoke(3,1,0))
            a._invoke(7,4,0,int(IronCAD.triFunction));a._invoke(3,4,0,owner)
            a._invoke(13,4,0,str(folder/loader.name));a._invoke(12,4,0,'RockProLatchManaged')
            (folder/'ownership.json').write_text(json.dumps({'owner':owner,'dll':str(folder/loader.name),'index':a._invoke(10,2,0),'count_before':count}),encoding='utf-8')
            print('INVOKE',folder.name,flush=True)
            a._invoke(11,1,0)
        finally:
            # Only remove when this is the sole entry, so no index can touch another addon.
            if a is not None and int(collection.Count)==1 and count==0:
                sole=disp(raw._invoke(5,1,0,0))
                if sole._invoke(3,2,0)==owner:
                    index=int(sole._invoke(10,2,0))
                    try:raw._invoke(4,1,0,index)
                    except Exception as e:cleanup['index_error']=str(e)
                    if int(collection.Count)==1 and disp(raw._invoke(5,1,0,0))._invoke(3,2,0)==owner:
                        try:raw._invoke(4,1,0,0)
                        except Exception as e:cleanup['zero_error']=str(e)
            cleanup['remaining_count']=int(collection.Count)
            cleanup['owner']=owner
            (folder/'addon_cleanup.json').write_text(json.dumps(cleanup),encoding='utf-8')
    p=folder/'result.json'
    if not p.exists():raise RuntimeError('Missing managed result: '+(folder/'clr_result.json').read_text())
    result=json.loads(p.read_text(encoding='utf-8-sig'))
    print(json.dumps({k:v for k,v in result.items() if k!='data'},ensure_ascii=False,indent=2))
    if not result['passed']:raise RuntimeError('Native job failed')
    return result
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    run(sys.argv[1],sys.argv[2],json.loads(Path(sys.argv[3]).read_text(encoding='utf-8-sig')))
