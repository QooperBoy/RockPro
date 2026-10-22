// Fixed legacy AddOn/triFunction exports: getter probe, private session ROT
// publication, and a bounded CLR latch A/B executor. No arbitrary execution
// endpoint, application launch, UI activation or installed SDK modifications.
// Minimal ABI declarations match Windows x64 COM and pinned ICAPI29 metadata.
typedef long HRESULT; typedef unsigned long ULONG; typedef unsigned long DWORD;
typedef unsigned short WORD; typedef unsigned int UINT; typedef unsigned long long U64;
struct GUID { DWORD a; WORD b,c; unsigned char d[8]; };
struct Unknown { virtual HRESULT __stdcall QueryInterface(const GUID&,void**)=0;
    virtual ULONG __stdcall AddRef()=0; virtual ULONG __stdcall Release()=0; };
struct Variant { WORD vt,r1,r2,r3; void* value; void* extra; };
struct Params { Variant* values; long* ids; UINT count,named; };
struct Dispatch: Unknown {
    virtual HRESULT __stdcall GetTypeInfoCount(UINT*)=0;
    virtual HRESULT __stdcall GetTypeInfo(UINT,DWORD,void**)=0;
    virtual HRESULT __stdcall GetIDsOfNames(const GUID&,wchar_t**,UINT,DWORD,long*)=0;
    virtual HRESULT __stdcall Invoke(long,const GUID&,DWORD,WORD,Params*,Variant*,void*,UINT*)=0;
};
extern "C" {
__declspec(dllimport) HRESULT __stdcall GetActiveObject(const GUID&,void*,Unknown**);
__declspec(dllimport) HRESULT __stdcall RegisterActiveObject(Unknown*,const GUID&,DWORD,DWORD*);
__declspec(dllimport) HRESULT __stdcall RevokeActiveObject(DWORD,void*);
__declspec(dllimport) void* __stdcall LoadLibraryW(const wchar_t*);
__declspec(dllimport) void* __stdcall GetProcAddress(void*,const char*);
__declspec(dllimport) HRESULT __stdcall LoadRegTypeLib(const GUID&,WORD,WORD,DWORD,Unknown**);
__declspec(dllimport) HRESULT __stdcall QueryPathOfRegTypeLib(const GUID&,WORD,WORD,DWORD,wchar_t**);
__declspec(dllimport) void __stdcall SysFreeString(wchar_t*);
__declspec(dllimport) int __stdcall GetModuleHandleExW(DWORD,const wchar_t*,void**);
__declspec(dllimport) DWORD __stdcall GetModuleFileNameW(void*,wchar_t*,DWORD);
__declspec(dllimport) DWORD __stdcall GetCurrentProcessId();
__declspec(dllimport) void* __stdcall GetForegroundWindow();
__declspec(dllimport) DWORD __stdcall GetWindowThreadProcessId(void*,DWORD*);
__declspec(dllimport) void* __stdcall CreateFileW(const wchar_t*,DWORD,DWORD,void*,DWORD,DWORD,void*);
__declspec(dllimport) int __stdcall WriteFile(void*,const void*,DWORD,DWORD*,void*);
__declspec(dllimport) int __stdcall FlushFileBuffers(void*);
__declspec(dllimport) int __stdcall CloseHandle(void*);
}
static const GUID AppClass={0x0002c522,0,0,{0xc0,0,0,0,0,0,0,0x46}};
static const GUID DispatchIID={0x00020400,0,0,{0xc0,0,0,0,0,0,0,0x46}};
static const GUID NullGUID={0,0,0,{0,0,0,0,0,0,0,0}};
static const GUID BaseIID={0xa5b9af7d,0x228b,0x4ed1,{0xba,0x42,0xd5,0x13,0x18,0xf7,0xea,0x20}};
static const GUID BridgeClass={0x6bcbab61,0x4399,0x4fd1,{0x86,0xd1,0x53,0x61,0xb8,0x39,0x5c,0x52}};
static const GUID BaseLib={0x6ee9ed93,0x0c2b,0x4808,{0xb1,0x38,0xf2,0x94,0xd9,0xa7,0x1b,0x0a}};
static const GUID AppLib={0xd8e3895d,0x8ca1,0x46cf,{0x85,0xf9,0x80,0x0b,0x9a,0x64,0x9f,0x82}};
struct Json {
    char data[32768]; UINT size;
    void text(const char* s){while(*s && size<32760)data[size++]=*s++;}
    void number(U64 value){char b[24];UINT n=0;do{b[n++]=char('0'+value%10);value/=10;}while(value);while(n)data[size++]=b[--n];}
    void hex(HRESULT value){text("\"0x");for(int i=7;i>=0;--i)data[size++]="0123456789ABCDEF"[(DWORD(value)>>(i*4))&15];text("\"");}
    void wide(const wchar_t* s){text("\"");if(s)while(*s && size<32750){WORD ch=WORD(*s++);if(ch==34||ch==92){data[size++]='\\';data[size++]=char(ch);}else if(ch>=32&&ch<127)data[size++]=char(ch);else{text("\\u");for(int i=3;i>=0;--i)data[size++]="0123456789ABCDEF"[(ch>>(i*4))&15];}}text("\"");}
};
static void library(Json& out,const char* name,const GUID& guid){
    Unknown* lib=0;wchar_t* path=0;
    HRESULT load=LoadRegTypeLib(guid,12,0,0,&lib);
    HRESULT query=QueryPathOfRegTypeLib(guid,12,0,0,&path);
    out.text(name);out.text(":{\"load_hr\":");out.hex(load);
    out.text(",\"query_hr\":");out.hex(query);out.text(",\"path\":");out.wide(path);out.text("}");
    if(lib)lib->Release();if(path)SysFreeString(path);
}
static int RunProbe(bool publish){
    // AddOn.Execute is synchronous on the host thread; static POD buffers keep
    // this tiny no-CRT diagnostic independent of the CRT stack-probe helper.
    void* fg=GetForegroundWindow();static Json out;out.size=0;
    out.text("{\"process_id\":");out.number(GetCurrentProcessId());
    out.text(",\"foreground_before\":");out.number(reinterpret_cast<U64>(fg));
    out.text(",");library(out,"\"base12\"",BaseLib);out.text(",");library(out,"\"app12\"",AppLib);
    Unknown* raw=0;Dispatch* app=0;Unknown* base=0;wchar_t* version=0;
    Variant z;z.vt=z.r1=z.r2=z.r3=0;z.value=z.extra=0;
    HRESULT active=GetActiveObject(AppClass,0,&raw),appQI=HRESULT(0x80004005),getZ=appQI,baseQI=appQI,api=appQI;
    U64 appHwnd=0;DWORD appPid=0;
    if(active>=0 && raw)appQI=raw->QueryInterface(DispatchIID,reinterpret_cast<void**>(&app));
    if(appQI>=0 && app){
        Params p;p.values=0;p.ids=0;p.count=p.named=0;
        Variant window;window.vt=window.r1=window.r2=window.r3=0;window.value=window.extra=0;
        HRESULT h=app->Invoke(28,NullGUID,0,2,&p,&window,0,0);
        if(h>=0 && (window.vt==3||window.vt==20||window.vt==21)){
            appHwnd=reinterpret_cast<U64>(window.value);GetWindowThreadProcessId(reinterpret_cast<void*>(appHwnd),&appPid);
        }
        // Never query the API of some other global application instance.
        if(appPid==GetCurrentProcessId())getZ=app->Invoke(42,NullGUID,0,2,&p,&z,0,0);
    }
    if(getZ>=0 && z.vt==9 && z.value)baseQI=static_cast<Unknown*>(z.value)->QueryInterface(BaseIID,reinterpret_cast<void**>(&base));
    // Official ICAPI29 IZBaseApp.ApiVersion has oVft=136, slot17 (x64).
    // The Python launcher verifies this against the pinned SDK before loading.
    if(baseQI>=0 && base){typedef HRESULT(__stdcall* GetVersion)(Unknown*,wchar_t**);
        GetVersion method=reinterpret_cast<GetVersion>((*reinterpret_cast<void***>(base))[17]);api=method(base,&version);}
    out.text(",\"get_active_hr\":");out.hex(active);out.text(",\"app_qi_hr\":");out.hex(appQI);
    out.text(",\"legacy_app_hwnd\":");out.number(appHwnd);out.text(",\"legacy_app_pid\":");out.number(appPid);
    out.text(",\"get_z_hr\":");out.hex(getZ);out.text(",\"base_qi_hr\":");out.hex(baseQI);
    out.text(",\"api_version_hr\":");out.hex(api);out.text(",\"api_version\":");out.wide(version);
    out.text(",\"foreground_after\":");out.number(reinterpret_cast<U64>(GetForegroundWindow()));
    DWORD cookie=0;HRESULT registered=HRESULT(0x80004005);
    if(publish && api>=0 && base)registered=RegisterActiveObject(base,BridgeClass,0,&cookie);
    out.text(",\"published\":");out.text(publish?"true":"false");
    out.text(",\"register_hr\":");out.hex(registered);
    out.text(",\"rot_cookie\":");out.number(cookie);out.text(",\"getter_only\":true}");
    if(version)SysFreeString(version);if(base)base->Release();
    if(z.vt==9 && z.value)static_cast<Unknown*>(z.value)->Release();
    if(app)app->Release();if(raw)raw->Release();
    void* module=0;static wchar_t path[2048];
    if(GetModuleHandleExW(6,reinterpret_cast<const wchar_t*>(&RunProbe),&module)){
        DWORD length=GetModuleFileNameW(module,path,2000);if(length && length<1900){
            DWORD n=length;while(n && path[n-1]!='\\')--n;
            const wchar_t* suffix=L"inprocess_probe.json";while(*suffix)path[n++]=*suffix++;path[n]=0;
            void* file=CreateFileW(path,0x40000000,1,0,1,0x80,0);
            if(file!=reinterpret_cast<void*>(-1)){DWORD written=0;WriteFile(file,out.data,out.size,&written,0);FlushFileBuffers(file);CloseHandle(file);}
        }
    }
    // Return success for executing the diagnostic. JSON carries API outcomes;
    // a failure HRESULT must never trigger an addon-error dialog.
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl RockProLatchProbe(){return RunProbe(false);}
extern "C" __declspec(dllexport) int __cdecl RockProLatchPublish(){return RunProbe(true);}

// Normal documented CLR hosting from our legacy triFunction DLL. The target
// assembly, type and method are fixed; no arbitrary entrypoint/path endpoint.
struct RuntimeHost: Unknown {
    virtual HRESULT __stdcall Start()=0;
    virtual HRESULT __stdcall Stop()=0;
    virtual HRESULT __stdcall SetHostControl(void*)=0;
    virtual HRESULT __stdcall GetCLRControl(void**)=0;
    virtual HRESULT __stdcall UnloadAppDomain(DWORD,int)=0;
    virtual HRESULT __stdcall ExecuteInAppDomain(DWORD,void*,void*)=0;
    virtual HRESULT __stdcall GetCurrentAppDomainId(DWORD*)=0;
    virtual HRESULT __stdcall ExecuteApplication(const wchar_t*,DWORD,const wchar_t**,DWORD,const wchar_t**,int*)=0;
    virtual HRESULT __stdcall ExecuteInDefaultAppDomain(const wchar_t*,const wchar_t*,const wchar_t*,const wchar_t*,DWORD*)=0;
};
static const GUID RuntimeClass={0x90f1a06e,0x7712,0x4762,{0x86,0xb5,0x7a,0x5e,0xba,0x6b,0xdb,0x02}};
static const GUID RuntimeIID={0x90f1a06c,0x7712,0x4762,{0x86,0xb5,0x7a,0x5e,0xba,0x6b,0xdb,0x02}};
extern "C" __declspec(dllexport) int __cdecl RockProLatchManaged(){
    static wchar_t folder[2048],assembly[2048],report[2048];void* module=0;
    if(!GetModuleHandleExW(6,reinterpret_cast<const wchar_t*>(&RockProLatchManaged),&module))return 1;
    DWORD n=GetModuleFileNameW(module,folder,2000);if(n==0||n>=2000)return 1;while(n && folder[n-1]!='\\')--n;folder[n]=0;
    for(DWORD j=0;j<=n;j++){assembly[j]=folder[j];report[j]=folder[j];}
#ifndef ROCKPRO_MANAGED_ASSEMBLY
#define ROCKPRO_MANAGED_ASSEMBLY L"LatchInProcess.dll"
#endif
    const wchar_t* a=ROCKPRO_MANAGED_ASSEMBLY;DWORD k=n;while(*a)assembly[k++]=*a++;assembly[k]=0;
    const wchar_t* r=L"clr_result.json";k=n;while(*r)report[k++]=*r++;report[k]=0;
    // Prior session ROT publication is handled separately; no cookie guessed here.
    void* library=LoadLibraryW(L"mscoree.dll");RuntimeHost* host=0;
    HRESULT bound=HRESULT(0x80004005),started=bound,executed=bound;DWORD result=999;
    if(library){typedef HRESULT(__stdcall* Bind)(const wchar_t*,const wchar_t*,DWORD,const GUID&,const GUID&,void**);
        Bind bind=reinterpret_cast<Bind>(GetProcAddress(library,"CorBindToRuntimeEx"));
        if(bind)bound=bind(L"v4.0.30319",L"wks",0,RuntimeClass,RuntimeIID,reinterpret_cast<void**>(&host));}
    if(bound>=0 && host){started=host->Start();if(started>=0)executed=host->ExecuteInDefaultAppDomain(assembly,L"RockPro.LatchInProcess",L"Run",folder,&result);host->Release();}
    static Json out;out.size=0;out.text("{\"process_id\":");out.number(GetCurrentProcessId());
    out.text(",\"bind_hr\":");out.hex(bound);
    out.text(",\"start_hr\":");out.hex(started);out.text(",\"execute_hr\":");out.hex(executed);
    out.text(",\"managed_result\":");out.number(result);out.text("}");
    void* file=CreateFileW(report,0x40000000,1,0,1,0x80,0);
    if(file!=reinterpret_cast<void*>(-1)){DWORD written=0;WriteFile(file,out.data,out.size,&written,0);FlushFileBuffers(file);CloseHandle(file);}
    return 1;
}
