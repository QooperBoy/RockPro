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

Next reference copies: Rack 9U and 4 Drawers + Table. The source-pinned
`native/FamilyParametric2027.cs` has been compiled but has not yet been exercised
on either model. Do not report the preparation as a working parametric template.
Keep rack rails/catalog geometry rigid and separate drawer motion from resizing.

## Shared handover

`native/PresentFamily2027.cs` refines metadata on the exact generated document.
`archive_parametric_family.py` requires both native and presentation PASS,
checks the preserved source hash and refuses an existing snapshot before copying
the model and exporting parameter/part-map CSVs. All actual manifests, models,
customer descriptions and native evidence stay outside public source history.
