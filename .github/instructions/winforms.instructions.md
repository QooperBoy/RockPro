---
description: RockPro native IronCAD add-in and Windows build constraints
applyTo: "Integracja/rockpro_cad/addin/**/*.cs,Integracja/rockpro_cad/addin/**/*.ps1,Integracja/rockpro_cad/qa/*.cs"
---

- Use Build.ps1's .NET Framework x64 compiler, WinForms and installed ICAPI interop. C# 14, file-scoped namespaces and ASP.NET conventions do not apply.
- Preserve COM GUID, ProgID and registration compatibility unless changing that contract. AssemblyVersion is a COM identity, separate from the product version.
- UI updates after awaits and modal forms stay on the owning thread. Preserve busy state, errors and selected project/source.
- Polish labels, light background, orange accents. Wheel input scrolls without changing numeric or orientation values. Colours have textual/numeric equivalents. Sorting choices preserves stable keys.
- Geometry and persistence belong to Python; frontend calls MCP rather than duplicating SQLite or formulas.
- Inspect affected UI flows at useful window sizes. See docs/DEVELOPMENT.md for build/UI checks and deployment verification.
