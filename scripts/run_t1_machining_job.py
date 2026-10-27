"""Private development runner: pinned local bridge, existing host, one CAD writer."""
import sys,json,shutil,hashlib,re,subprocess,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.icapi_runtime import selected_year, installation_dir
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def existing_legacy_app(context):
    """Attach through one exact open document when the generic ROT entry is absent."""
    import ctypes as ct
    import comtypes.client
    from comtypes import HRESULT
    from comtypes.automation import IDispatch
    from rockpro_cad.icapi_runtime import ICAPI
    from rockpro_cad.parts.native import same_document_path
    source=Path(context).resolve(strict=True)
    ole=ct.OleDLL('ole32')
    rot=ct.POINTER(ICAPI.IRunningObjectTable)();bind=ct.POINTER(ICAPI.IBindCtx)()
    ole.GetRunningObjectTable.argtypes=[ct.c_ulong,ct.POINTER(type(rot))]
    ole.GetRunningObjectTable.restype=HRESULT
    ole.CreateBindCtx.argtypes=[ct.c_ulong,ct.POINTER(type(bind))]
    ole.CreateBindCtx.restype=HRESULT
    ole.GetRunningObjectTable(0,ct.byref(rot));ole.CreateBindCtx(0,ct.byref(bind))
    iterator=rot.EnumRunning()
    while True:
        moniker,count=iterator.RemoteNext(1)
        if not count:break
        try:name=moniker.GetDisplayName(bind,None)
        except Exception:continue
        if same_document_path(name,source):
            document=comtypes.client.GetBestInterface(rot.GetObject(moniker).QueryInterface(IDispatch))
            return document.Application
    raise RuntimeError('Exact existing ROT document required; no launch or activation')

def cleanup_owned_addon(collection,owner,count_before):
    """Remove only the sole owned entry, using its observed collection position.

    IronCAD 2023 reports AddOn.Index=1 for Item(0); Remove expects zero-based
    collection indices. Checking Count after removal prevents false success.
    """
    if int(collection.Count)!=1 or count_before!=0:
        return {'removed':False,'reason':'Collection ownership is not exclusive'}
    raw=collection._comobj
    sole=raw._invoke(5,1,0,0)
    sole=sole._comobj if hasattr(sole,'_comobj') else sole
    if sole._invoke(3,2,0)!=owner:
        return {'removed':False,'reason':'Sole entry is not owned'}
    raw._invoke(4,1,0,0)
    after=int(collection.Count)
    if after!=0:raise RuntimeError('Owned AddOn removal did not empty the collection')
    return {'removed':True,'count_after':after}

def current_interop(folder):
    """2023 samples ship a stale 2018 wrapper; import the installed TLB locally."""
    install=installation_dir()
    if selected_year()!=2023:
        return install/'ICAPI/Samples/C#/References/interop.ICApiIronCAD.dll'
    helper=ROOT/'scripts/native/GenerateLocalInterop.cs'
    exe=folder/'GenerateLocalInterop.exe'
    compiler='C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    built=subprocess.run([compiler,'/nologo','/platform:x64','/out:'+str(exe),str(helper)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if built.returncode:raise RuntimeError(built.stdout+built.stderr)
    tlb=install/'bin/ICApiIronCAD.tlb'
    vendor=folder/'interop.ICApiIronCAD.dll'
    result=subprocess.run([str(exe),str(tlb),str(vendor)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    evidence={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
              'tlb_sha256':sha(tlb),'helper_sha256':sha(helper),'host_year':selected_year()}
    if result.returncode==0:evidence['interop_sha256']=sha(vendor)
    (folder/'interop-generation.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    if result.returncode:raise RuntimeError('Local interop generation failed; see interop-generation.json')
    return vendor
def run(folder,source,request):
    request=dict(request)
    if request.get('contract') in ('rockpro-t1-mounting-repair-v1','rockpro-t1-structure-v1'):
        from rockpro_cad.core_case.scene_structure import validate_t1_machining
        validate_t1_machining([p['key'] for p in request['parts']],request.get('operations',[]))
        if request['contract']=='rockpro-t1-structure-v1' and sha(request['source'])!=request['source_sha256']:
            raise ValueError('Constructor template source changed')
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
    vendor=current_interop(folder)
    src=Path(source).resolve();built=folder/('Machining_'+sha(src)[:20]+'.dll')
    cmd=['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/target:library','/platform:x64','/out:'+str(built),'/reference:'+str(vendor),'/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll',str(src)]
    c=subprocess.run(cmd+['/utf8output'],capture_output=True,text=True,encoding='utf-8',errors='replace')
    (folder/'compile.json').write_text(json.dumps({'returncode':c.returncode,'stdout':c.stdout,'stderr':c.stderr,'source_sha256':sha(src),'loader_sha256':sha(loader)}),encoding='utf-8')
    if c.returncode:raise RuntimeError(c.stdout+c.stderr)
    shutil.copyfile(built,folder/names[0])
    if vendor.resolve()!=(folder/vendor.name).resolve():shutil.copyfile(vendor,folder/vendor.name)
    shutil.copyfile(loader,folder/loader.name)
    (folder/'request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
    import comtypes.client
    IronCAD=comtypes.client.GetModule(str(installation_dir()/"bin/IronCad.tlb"))
    app=existing_legacy_app(request['context_path']) if request.get('context_path') else comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True)
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
            if a is not None:
                try:cleanup.update(cleanup_owned_addon(collection,owner,count))
                except Exception as e:cleanup['error']=str(e)
            cleanup['remaining_count']=int(collection.Count)
            cleanup['owner']=owner
            (folder/'addon_cleanup.json').write_text(json.dumps(cleanup),encoding='utf-8')
    if cleanup.get('remaining_count')!=count:
        raise RuntimeError('Temporary AddOn cleanup incomplete; reconcile addon_cleanup.json before another job')
    p=folder/'result.json'
    if not p.exists():raise RuntimeError('Missing managed result: '+(folder/'clr_result.json').read_text())
    result=json.loads(p.read_text(encoding='utf-8-sig'))
    print(json.dumps({k:v for k,v in result.items() if k!='data'},ensure_ascii=False,indent=2))
    if not result['passed']:raise RuntimeError('Native job failed')
    return result
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    run(sys.argv[1],sys.argv[2],json.loads(Path(sys.argv[3]).read_text(encoding='utf-8-sig')))
