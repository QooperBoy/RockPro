RockPro CAD — independent acceptance harness

acceptance.json is the test contract. It deliberately separates:
  automated tests, source review and live IronCAD observations.
A compile result is not proof that the ribbon panel renders correctly.
A populated table is not proof of database persistence.
A saved file is not proof of successful snapshot regeneration.

Execution order
1. Run backend and MCP tests against a temporary database.
2. Review selected project/source handling and snapshot failure paths.
3. Build the native add-in.
4. Root agent alone operates live CAD: connect, select a project, open each
   table, resize, take a snapshot, change dimensions on a copy, reopen.
5. Reviewer inspects resulting report files and source/copy identities.
6. Record PASS / FAIL / NOT RUN individually; do not promote unobserved UX
   checks to PASS.

Live-CAD coordination
Only one actor may use CAD at a time. Independent review of files can run
in parallel. Live COM inspection requires the root agent's handoff.

Release boundary
This version supports the verified two-half, ten-panel skeleton only.
Email ingestion, generated product models, fittings, wheels, nesting,
production drawings and purchasing must be labelled as planned until
their implementations and tests exist.
