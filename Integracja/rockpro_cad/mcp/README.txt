RockPro CAD — local MCP stdio

Current protocol tools (11):
  inspect_project, change_dimensions_on_copy,
  list_projects, save_project, get_project, set_stage,
  list_snapshots, create_snapshot,
  preview_layout, get_layout, save_layout.
Use tools/list for the live contract. Historical serverInfo/assembly versions
are component identities; they are not proof of the deployed product release.

Run from Integracja:
  .venv\Scripts\python.exe rockpro_cad\mcp\server.py
The transport is newline-delimited JSON-RPC over stdio, no HTTP listener.
Diagnostics go to stderr. No arbitrary shell/Python execution tools exist.

UI and AI call the same dispatcher and SQLite registry. The card's quantity
counts cases; layout.spec.count counts devices per case. Workflow statuses
are manual records, not proof of automated CAD checks.

preview_layout computes envelopes and rankings without CAD. get_layout and
save_layout use the project database. Rankings compare 18 linear variants,
not all possible 3D packings. The CAD copy operation currently changes the
six parameters of the verified ten-panel skeleton; equipment and partitions
in the layout preview are not inserted as CAD parts.

Native operations require the same Windows account/session as the open
IronCAD host and a permitted ICS source inside Integracja. Source identity,
manifest IDs, the six-parameter allowlist, worker lock, finite dimensions and
geometry checks must remain intact. Changes use SaveAsCopy, regenerate,
save, close and reopen the working copy. report.json records failure stage
and source preservation. A failed operation does not advance the project.

Archived snapshot.ics is separate from the working revision. SHA256 detects
external edits, not WORM protection. Historical validation and current archive
integrity are separate facts. Do not edit the source manually during a job.

Full engineering contract and checks: repository docs/DEVELOPMENT.md.
Product/layout scope: LAYOUT.md. Snapshot/layout version linking and concurrent
editor conflicts remain tracked gaps in docs/REPOSITORY_AUDIT.md.
