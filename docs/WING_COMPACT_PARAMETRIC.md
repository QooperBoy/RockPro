# Wing Compact — native prototype, IronCAD 2027

This adapter creates a new parametric copy of the imported mixer case. It does
not extend the installed add-in, public MCP allowlist or Studio generator to
arbitrary ICS files. Source SHA256, process ID, API major and a non-existing
output are checked before mutation; the runner holds the shared CAD writer lock.

## Implemented behaviour

- 26 scene length parameters with Polish notes: hood envelope/lift, device
  translation, front/rear latch rows, three handles, feet, supports and foam.
- 28 dimensioned material parts; two compound foams retain their device-shaped
  contours. Thirty material histories are rebuilt from source profile curves,
  without inheriting obsolete constructor dimension relations.
- Catalog units retain rotations and physical sizes. The original topology has
  a tall removable hood over a shallow base, four latches, three handles and
  four rubber feet. This is not a hinged shallow-lid template.
- 36 subtraction operations keep source contours and follow explicit hardware,
  device or support anchors. The five device-related floor-foam recesses follow
  the mixer, not the external rubber feet.
- 232 Polish scene labels; source part/feature aliases remain separate from
  labels, so renaming does not change the binding keys.

## Native evidence, 29 October 2026

Private evidence: `artifacts/wing-compact-20261029/build-02/result.json` and
`present-01/result.json`. Eight native checks PASS: initial geometry, larger
envelope (663 × 534 × 251.8 mm), hardware/feet adjustments, hood lift 200 mm,
device displacement (+2, -2, +1 mm), restore/naming, save/reopen and hardware
editing after reopening. Each check measures 162 physical parts and 36 cut
profiles; it checks rigid geometry, material dimensions, world poses, curve
lengths and coarse device containment in the plywood interior.

Maximum measured pose error is below 0.00005 mm; cut error below 0.00004 mm.
The presentation pass changes names/notes without changing world poses or scene
parameter expressions. Source disk hash and preexisting document modification
states were preserved. The final ICS and verified snapshot live in the private
workspace project `projekty/Mikser_WingCompact_parametryczny_20261029`.

## Boundaries

The envelope controls describe the external **plywood** hood, excluding projecting
hardware. They are not internal dimensions. The fixed base profile cannot be
stretched to invent a base-height control. Decreasing the envelope below the
reference size requires a new fit review; notes are recommendations, not hard
collision guards. Quantity and free rotation are not editable controls here.

The source has an unused right-foam handle opening without a right-wall handle.
It is preserved and explicitly named as reserved, never nearest-matched to a
handle on another wall. Separate foot screw drills are absent from the source.
Support and shaped-foam fine adjustments have bindings but were not separately
exercised by the native scenario set. No full BRep collision audit, CNC output
or constructor/production approval is claimed.

## Reproduction

`scripts/prepare_wing_compact.py` reads private inspected source metadata and
generates the source-pinned plan. `scripts/native/WingCompact2027.cs` runs through
`scripts/run_t1_machining_job.py` with `ROCKPRO_IRONCAD_YEAR=2027`; use a fresh
job folder and new output revision. `PresentWingCompact2027.cs` only refines
metadata on that exact generated open document. Do not overwrite snapshots or
reuse stale process IDs, reference paths or source inventories.

Imported extrudes can have no accessible curves; read-only inspectors tolerate
null curve arrays. Reconstruction only accepts the reviewed extrude histories.
Generate a fresh part body before resetting/binding its SizeBox. Preserve
feature aliases by durable source IDs because rebuilding changes history order.
