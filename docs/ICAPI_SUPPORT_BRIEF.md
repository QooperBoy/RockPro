# IronCAD 2027: external ICAPI access and hidden-open support brief

Draft for vendor support; **not sent**. No customer CAD file is attached.
Observed on 22 October 2026. Exact local evidence is retained in ignored artifacts.

## Environment and intended operation

Windows x64, IronCAD 2027. In-process `IZBaseApp.ApiVersion` reports
`29.0.2.20605`. Both Python/comtypes and the official C# ICAPI interop were tested.
Client and existing CAD host have the same user SID and Medium integrity token.

We need to read complete catalog assemblies, place copies in a newly created
hidden scene, save/reopen that scene, and close only documents owned by the job.
The source model must remain unchanged. No desktop automation is used.

## Issue 1: external versus in-process interface access

1. Start the normal IronCAD application and open a saved document.
2. Attach to the existing application or exact document ROT entry.
3. Read the legacy `Application.HWnd` and verify its process identity.
4. Request `IZBaseApp` from `Application.ZIronCADApp`.

Observed externally:

- Both Python and official C# interop return `E_NOINTERFACE` (`0x80004002`).
- `IDispatch.GetTypeInfo` returns `TYPE_E_LIBNOTREGISTERED` (`0x8002801D`).
- The requested SDK IID is `{A5B9AF7D-228B-4ED1-BA42-D51318F7EA20}` in both clients.
- Registered SDK 29.0 type libraries load successfully in the client.

Observed through a documented legacy `triFunction` AddOn in the same host:

- QueryInterface for that same IID succeeds.
- The typed `ApiVersion` getter succeeds.
- Publishing the interface under a private session-only ROT identifier succeeds,
  but an external typed client still receives `E_NOINTERFACE`.
- A fixed managed helper loaded within that AddOn can use ICAPI and open/close
  its own hidden copy. This is a bounded diagnostic, not a production bridge.

Additional evidence: ATL type-info structures in installed Base/App/Core/Drawing
components contain version 12.0, whereas embedded TYPELIB resources identify as
29.0. A diagnostic `LoadRegTypeLib(12.0)` inside the host fails. Private per-user
compatibility metadata loaded in a fresh client but did not fix external access.
This is an observed mismatch, **not a proven root cause**. Installed SDK binaries
were not patched. Experimental registry changes have separate rollback receipts;
check their current state before repeating any repair.

Questions for support: is this a known configuration or marshaling problem in
this build? Which registration/initialization path is supported for an external
Python client? Is a specific update required?

## Issue 2: hidden open and read-only flags

On a new byte-identical job-owned copy, `OpenFile2(path, true, false, out already)`
returned a document with the expected GUID/hash and `Modified=false`, but
`IsReadOnly()` returned `false`. The original file was not opened by this job.

Applying the Windows ReadOnly attribute to a later job-owned copy was followed
by one foreground change during open; that attempt failed its foreground guard
and closed the owned copy. Another such open remained pending behind a modal
window titled `IRONCAD2027`. The dialog contents have not been inspected, so its
precise cause is unconfirmed. No automated click or forced host termination was
attempted. The job was prevented from starting its next CAD phase. The user
subsequently closed the dialog; the job failed its foreground guard, closed its
owned copy, and did not execute A/B.

A later bounded run used a writable, job-owned byte copy for getters/export
only, with GUID/hash and unchanged `Modified` checks. It completed native
placement, save/reopen and owned-document cleanup for two new scenes without
changing the original or foreground. This does not establish that the SDK
read-only mode works or repair the external COM connection.

Questions for support: what is the supported way to open a copy invisibly and
read-only without modal warnings or activation? Does `IsReadOnly()` describe the
file flag, document mode, or another condition? How should a background job
cancel a pending open without affecting unrelated documents?

## Evidence and boundaries

- [Local connection runbook](ICAPI_CONNECTION_RUNBOOK.md)
- [Current hardware MVP scope](HARDWARE_MVP_STATUS.md)
- [Proposed in-process executor](ADR_INPROCESS_CAD_EXECUTOR.md)

We can provide a minimal getter-only reproducer and SDK/build details without
sending the customer assembly. Successful compilation, a getter, or an offline
placement plan is not reported as a successful native assembly operation.

The vendor's [2027 release notes](https://www.ironcad.com/support/readme/2027/Readme.htm)
list `apisupport@ironcad.com` for API development questions and recommend
Visual Studio 2019 or later. The official
[2027 feature description](https://www.ironcad.com/blog/whats-new-in-2027/)
describes Python integration. These declarations are distinct from the runtime
failures observed above.
