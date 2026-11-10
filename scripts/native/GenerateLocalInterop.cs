// Generate a local interop from the installed TLB without registering or changing it.
using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using TYPELIBATTR = System.Runtime.InteropServices.ComTypes.TYPELIBATTR;

class GenerateLocalInterop : ITypeLibImporterNotifySink {
    [DllImport("oleaut32.dll", CharSet=CharSet.Unicode, PreserveSig=false)]
    static extern void LoadTypeLibEx(string path, int registrationKind,
        [MarshalAs(UnmanagedType.Interface)] out object library);

    public void ReportEvent(ImporterEventKind kind, int code, string message) {
        if (kind != ImporterEventKind.NOTIF_TYPECONVERTED)
            Console.WriteLine(kind + " " + code + ": " + message);
    }
    public Assembly ResolveRef(object library) {
        IntPtr pointer;
        var tlb=(ITypeLib)library;
        tlb.GetLibAttr(out pointer);
        try {
            var attr=(TYPELIBATTR)Marshal.PtrToStructure(pointer,typeof(TYPELIBATTR));
            if(attr.guid != new Guid("00020430-0000-0000-C000-000000000046"))
                throw new InvalidOperationException("Unrecognized typelib dependency: "+attr.guid);
            return Assembly.LoadFrom(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                @"Microsoft.NET\Primary Interop Assemblies\stdole.dll"));
        } finally { tlb.ReleaseTLibAttr(pointer); }
    }
    [STAThread] static int Main(string[] args) {
        if(args.Length!=2) return 2;
        string source=Path.GetFullPath(args[0]), target=Path.GetFullPath(args[1]);
        if(!File.Exists(source)||File.Exists(target)) throw new IOException("Missing source or existing output");
        Directory.CreateDirectory(Path.GetDirectoryName(target));
        object library;
        LoadTypeLibEx(source,2,out library); // REGKIND_NONE: no registry writes.
        var assembly=new TypeLibConverter().ConvertTypeLibToAssembly(library,target,
            TypeLibImporterFlags.ImportAsX64,new GenerateLocalInterop(),null,null,
            "interop.ICApiIronCAD",null);
        assembly.Save(Path.GetFileName(target));
        Console.WriteLine(target);
        return 0;
    }
}
