---
description: RockPro Python MCP and SQLite contracts
applyTo: "Integracja/rockpro_cad/mcp/**/*.py,Integracja/rockpro_cad/qa/**/*.py"
---

- Follow existing stdlib/unittest conventions. Import COM lazily so offline tests do not require IronCAD or a license.
- MCP stdout is JSON only; diagnostics use stderr. Keep server.py tool schemas and worker dispatch arguments aligned. Reject unknown arguments before mutation.
- Validate finite numbers and reject bools as numbers. Tool dimensions are mm; native ICAPI values can be metres.
- Use one project database, exact source pinning, parameterized SQL and isolated test databases. Invalidate downstream stages when inputs change.
- Layout ranking covers the implemented 18 linear variants; it is not general 3D packing or structural approval.
- Use docs/DEVELOPMENT.md verification commands. Distinguish SQLite/layout tests from native CAD evidence.
