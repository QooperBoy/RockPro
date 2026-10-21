---
description: RockPro native geometry and source preservation
applyTo: "Integracja/ironcad_adapter.py,Integracja/wholecase_common.py,Integracja/review_skeleton*.py,Integracja/rockpro_cad/mcp/worker.py"
---

- Keep the two-half / ten-plate manifest and six-parameter allowlist. Do not loosen IDs or shape checks to accept unsupported files.
- Drive COM serially in the same Windows user/session as IronCAD. Preserve the worker lock and source identity.
- Changes use SaveAsCopy to a new working ICS, never SaveAs or source-save fallback. Measure geometry before saving and after reopening.
- Record source hash, parameters, saved flag and failure stage. Failed operations do not advance the project source or register successful snapshots.
- Archive and working revision are separate. Checksum integrity and historical geometry validation are separate facts.
