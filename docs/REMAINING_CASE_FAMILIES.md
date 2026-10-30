# Remaining case families — 30 October 2026

The user requested three further **families**, not one task for every ICS file:
chests, racks and drawer/workstation cases. Inspect each scene before deciding
which complete constructions and variants it contains. Television and mixer
families already have separate verified prototypes.

## Chest — native prototype R001

Source-pinned `prepare_kufer.py` and `native/Kufer2027.cs` operate on a new 2027
copy only. 29 scene controls, 356 physical parts, 44 dimensioned material parts,
40 reconstructed extrude histories, 84 available subtraction operations and
465 Polish scene descriptions. Four partition histories include API-inaccessible
operations and are retained natively, rather than silently dropping details.

Controls include the plywood envelope, body/lid heights, joint hardware rows,
eight lifting handles, edge handle, label dish, four partition positions and
shared wheel/stacking-dish offsets. Catalog hardware stays rigid. Partition
slots in the supports share the partition's X displacement. Existing unused
source slots are retained. Quantity is source-defined, not a fake scalar control.

Private evidence `artifacts/kufer-20261030/build-02`: seven native checks PASS,
including larger envelope, independent mounting adjustments, partition/hood
movement, restore, save/reopen and editing after reopening. `present-01` PASS
adds final Polish descriptions and green plywood without changing world poses
or parameter expressions. Snapshot and CSVs are in the private chest project.

The first diagnostic detected four zero-sized imported latch-body bounding boxes
before regeneration. The capture now materializes only zero-sized source-copy
bodies before measuring the baseline. No catalog shape was resized to satisfy
the test. A transient COM error reading AddOns during wrapper cleanup occurred
after native PASS (managed result 0); the separate final metadata/save job then
completed through the SDK with exit 0. Other addons/documents were not removed.

Envelope controls are external **plywood** dimensions, excluding projecting
hardware and wheels, not internal free space or dimensions inferred from the
filename. Lid lift is an exploded view, not a hinge rotation simulation. Native
geometry/anchor checks do not constitute full BRep collision or CNC approval.

## Rack and drawer families

Rack 9U has a body and two removable end covers. Its source-pinned plan has
19 controls, 451 physical parts, 55 dimensioned material parts and 28 available
subtractions. The 19-inch mounting width is fixed; the 410-mm rails keep 9U.
Height adjustment adds free space above the rails rather than inventing U units.
Both cover depths/openings, latch heights, handle rows, rail offsets and paired
wheel/socket adjustments have separate controls.

The reference has a front plywood cover 7 mm lower than its frame and front
latch halves 3.5 mm too low. The explicit correction parameter defaults to 7 mm;
the source mounting cuts were already at the correct height and do not receive
that correction. The two right handle contours are the same 130 × 78 mm as the
left templates, but their source placement was offset. Their coordinates are
corrected to the corresponding H7159 anchors, retaining the opposite side's
0.2-mm template Z datum. This is a source-layout repair, not a vendor CNC approval.

Rack native evidence `artifacts/rack-20261030/build-01`: seven checks PASS,
including save/reopen and mounting edits afterwards. Physical roof/panel
alignment passes at baseline and resized dimensions. `present-02` additionally
checks all four latch-half Z centers (agreement within 1e-9 mm), preserves poses
and formulas, and sets the 244 plywood face appearances to green. Imported
per-face colors had overridden the part color. The documented IZBodyFace API
is used; no surface geometry or spline buffers are edited. The first snapshot
is preserved; CURRENT.json points at the new SNAPSHOT_KOLOR copy.

Offline repository/backend/parts/core-design/core-contracts/QA/harness PASS,
evidence `artifacts/verification/20261030T125428228936Z`. Constructor/BRep/CNC
approval remains separate. Drawer reference: 4 Drawers + Table contains folded
and deployed states of the case. Inspect and select the canonical state rather
than counting both as purchased parts. Keep catalog geometry rigid and separate
drawer motion from resizing.

The shared managed adapter clears job-local ID maps and geometry baselines at
each invocation, because the bridge can reuse a loaded assembly between jobs.

## Shared handover

`native/PresentFamily2027.cs` refines metadata on the exact generated document.
`archive_parametric_family.py` requires both native and presentation PASS,
checks the preserved source hash and refuses an existing snapshot before copying
the model and exporting parameter/part-map CSVs. All actual manifests, models,
customer descriptions and native evidence stay outside public source history.

## Drawer/workstation completed

Native `artifacts/szuflady-20261030/build-02`: seven scenarios PASS; presentation-01 PASS (422 names, 24 cuts, 322 green plywood faces). 26 controls, 380 physical parts, 76 dimensioned materials. Only the deployed source state is retained in the new copy; the folded duplicate remains in the original. Drawers are numbered bottom to top. Four independent extensions and front heights, body dimensions, top lid, handle/latch positions, table XY and leg Z are editable. Source top lid angle is 105 degrees, not a folding animation.

Rotated material growth uses local feature axes and six local bounds, with analytical anchor drift compensation. Table connectors follow cabinet-depth peg spacing; cabinet pegs preserve working height. Tests check front gaps >=6 mm, upper reserve and physical connector/hinge offsets. Mapping validation rejected an assembly ID in the first diagnostic; final checks use physical hinge leaves 1693/1700. Catalog shapes remain rigid. Pads are not certified runner models, leg ground contact needs constructor review, and native checks are not complete BRep/CNC approval.

Final offline seven groups PASS: `artifacts/verification/20261030T132924106935Z`. Separate native evidence is above; the offline harness does not operate IronCAD. Long native jobs can report a wrapper AddOns.Count cleanup COM error after managed success; check native and CLR results before any retry. Separate presentation/save completed. Reference copies were checkpointed and closed, with other documents preserved; capture immutable document GUIDs before closing COM document objects. All three families have preserved snapshots and guides; constructor acceptance remains pending.
