RockPro CAD MCP 0.1

Run from Integracja:
  .venv\Scripts\python.exe rockpro_cad\mcp\server.py

MCP transport is newline-delimited JSON-RPC over stdio. No network port is opened.
Tools: inspect_project; change_dimensions_on_copy.
Example tool arguments:
  {"changes":{"RP_Length":1014,"RP_Depth":662}}

The native panel can call the same implementation:
  .venv\Scripts\python.exe rockpro_cad\mcp\worker.py request.json
request.json:
  {"name":"inspect_project","arguments":{}}
The CLI prints one JSON object with ok and result/error.

Run under the same Windows account/desktop context as the open IronCAD application.
The default source is the final ICS named in skeleton_state.json's skeleton_manifest.json.
Source must be open in IronCAD. Optional source is restricted to ICS below Integracja.
Only this verified skeleton family (two groups, five plates each, known IDs) is supported.
No generic CAD editing, shell execution, arbitrary Python, or arbitrary output paths.

Native SaveAsCopy takes an in-memory snapshot, including unsaved source changes.
Failure stops the operation: no unsafe SaveAs or source Save fallback.
The revision is written to rockpro_cad/revisions/<random UUID>/RockPro_revision.ics.
Every successful revision is regenerated, geometry-checked, saved, closed and reopened,
then checked again. report.json records the checks. A failed copy is retained for diagnosis;
it is not claimed as production-ready. The source file hash, parameters and saved state
must remain unchanged. Operations through this dispatcher are mutually exclusive.
Do not edit the source manually during an operation.

MVP restrictions:
- MCP registration in the AI client is separate; this folder does not modify client config.
- COM must not be called while a modal IronCAD dialog prevents automation.
- No hardware, WoodLAB metadata or production/manufacturing assurance.
- Native SaveAsCopy behavior must be verified in the installed IronCAD build.
- Minimal MCP protocol support: initialize, notifications, ping, tools/list, tools/call.
  No resources, prompts, HTTP, authorization service, cancellation, or progress streaming.
- Current bounds are conservative software limits, not validated construction limits.

PROJECT REGISTRY v0.2 (2026-10-20)
SQLite data/projects.sqlite3 is a new local registry, not an imported historical RockPro database.
Eight MCP tools: inspect_project, change_dimensions_on_copy, list_projects, save_project,
get_project, set_stage, list_snapshots, create_snapshot.
The project card stores name/client/device/quantity/notes and an exact working ICS path.
Stage status is a manual record (draft/waiting/review/approved/outdated), NOT proof of CAD validation.
After changed geometry, dependent stages are outdated. Quantity changes invalidate materials/production;
device changes invalidate layout onward. Partial metadata updates preserve omitted fields.
A native create_snapshot uses the unchanged dimension-copy pipeline including SaveAsCopy,
geometry validation, save, close and reopen. It then copies the validated saved revision into
snapshot.ics, separate from the open working document. No snapshots are registered on CAD failure.
Dimension changes with project_id advance the project's working source only after success.
Archives are not editable through change_dimensions_on_copy and cannot be bound as project sources.
An external program can still edit files: list_snapshots checks the stored SHA256 and reports
integrity verified/modified/missing. 'validation: passed' is the historical geometry result, not
proof that an archive has stayed untouched. UI should display integrity separately.
get_project returns project with 9 stages and snapshots. create_snapshot returns snapshot/project.
change_dimensions_on_copy returns its existing audit report plus snapshot/project when project_id given.
The stdio MCP protocol is the sole UI/backend transport. No separate HTTP listener is started.
Tests: python -m unittest discover -s mcp -p "test*.py" -v
