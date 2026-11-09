from pathlib import Path
p=Path('Integracja/rockpro_cad/core_case/native.py')
s=p.read_text(encoding='utf-8')
a=s.index('    def create(self, parts):',s.index('class IronCADPrototypeDriver'))
b=s.index('\n\ndef execute_plan',a)
s=s[:a]+'''    def create(self, parts):
        # The SDK's primitive CreateBlockPart is E_NOTIMPL in IronCAD 2027.
        # Use the installed official .NET interop and its documented profile /
        # CreateExtrudeFeature path, rather than modifying COM registration.
        import shutil
        import subprocess
        import os
        from python_ironcad.core import install_dir
        from contextlib import redirect_stdout
        folder = self.workdir / "sdk_bridge"
        folder.mkdir(exist_ok=False)
        vendor = Path(install_dir) / "ICAPI" / "Samples" / "C#" / "References" / "interop.ICApiIronCAD.dll"
        compiler = Path(os.environ.get("WINDIR", r"C:\\Windows")) / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe"
        if not vendor.is_file() or not compiler.is_file():
            raise NativeExecutionError("IronCAD 2027 official SDK interop or .NET Framework x64 compiler unavailable")
        executable = folder / "NativeSceneBridge.exe"
        bridge_source = Path(__file__).with_name("NativeSceneBridge.cs")
        build = subprocess.run([str(compiler), "/nologo", "/target:exe", "/platform:x64",
            "/out:"+str(executable), "/reference:"+str(vendor), "/reference:System.Web.Extensions.dll",
            "/reference:Microsoft.CSharp.dll", str(bridge_source)], capture_output=True, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if build.returncode:
            raise NativeExecutionError("Official SDK bridge compilation failed: "+(build.stdout+build.stderr)[-2000:])
        shutil.copyfile(vendor, folder / vendor.name)
        self.bridge_output = self.workdir / "case_prototype.ics"
        request = folder / "request.json"
        result = folder / "result.json"
        request.write_text(json.dumps({"source":str(self.source), "output":str(self.bridge_output),
                                       "parts":parts}, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        run = subprocess.run([str(executable),str(request),str(result)], capture_output=True, text=True,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        (folder / "bridge.log").write_text(run.stdout+run.stderr, encoding="utf-8")
        if run.returncode or not result.is_file():
            raise NativeExecutionError("Official SDK bridge failed: "+(run.stdout+run.stderr)[-2000:])
        self.bridge_result = json.loads(result.read_text(encoding="utf-8-sig"))
        if self.bridge_result.get("passed") is not True:
            raise NativeExecutionError("Official SDK bridge returned failure")
        self._reopened = False

    def measure(self):
        return self.bridge_result["reopened" if self._reopened else "before"]

    def save_reopen(self, path):
        # The fixed bridge performs save/close/reopen and separate measurements
        # inside one STA process; these observations are checked independently.
        if path != self.bridge_output or not path.is_file():
            raise NativeExecutionError("SDK output path mismatch")
        self._reopened = True
''' + s[b:]
s=s.replace('    def capture(self, path):\n        self.assert_source_unchanged()', '    def capture(self, path):\n        self.workdir = path.parent\n        self.assert_source_unchanged()')
s=s.replace('        from contextlib import redirect_stdout\n','')
p.write_text(s,encoding='utf-8')
