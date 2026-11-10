# Observability audit and adversarial review — 10 November 2026

Subject: `origin/main` at `cafa890` (Marcin's 10.11 publication). Reviewer: Kuba with
Claude, using `.agents/skills/rockpro-adversarial-review`. Offline only: no CAD job was
run, no IronCAD document was opened. IronCAD 2023 is installed on the review machine.

## What exists today

| Layer | Where | Records | Vocabulary |
|---|---|---|---|
| Studio process registry | `process_runs.py`, SQLite `studio_process_runs` | operations, interventions, spans per draft revision | `origin` standard/ai/manual/unknown, `executor` sdk/python/agent/constructor/unknown |
| CAD job collector | `process_capture.py` | one span per job + one operation per `native_progress.jsonl` line | origin from the job descriptor |
| Operation log | `parts/operation_log.py`, `core_case/trace.py` | bounded JSONL metadata | free-text `actor` (`script`, `deterministic-reader`) |
| Agent MCP entry | `mcp/agent_server.py` → `artifacts/agent-runs/*.jsonl` | one row per tool call, argument hash, budgets | `actor='agent'`, `operation='agent.tool'` |
| Viewers | `process_observer.py` (Tk), `reference_studio/process-panel.js` | read-only | — |

The registry design is sound: decision origin is separate from executor, an AI operation
must link to a recorded intervention with a reason, completed attempts are immutable,
and a run cannot be closed as completed with failures, open spans or unresolved
interventions. That makes it the right source of truth for the dashboard.

## Fixed on `review/observability-audit`

1. **[BLOCKING, CONFIRMED] Logging changed the outcome of CAD jobs.** `capture()` ran the
   trace import after the job inside the same context manager. A successful job was
   reported as failed when `native_progress.jsonl` lacked its final newline
   (`ValueError: Niepełny ślad natywny`) or when the run was closed while the job ran
   (`Zakończony przebieg jest niezmienny`). A failed job lost its own error to a
   `JSONDecodeError` from a corrupt trace. `scripts/run_t1_machining_job.py` returns the
   job result from inside `capture()`, so this reached real jobs. Now bookkeeping
   failures are collected, written to stderr, attached as a note to the job's own
   exception, and recorded as a failed `Import śladu natywnego` span when the run is
   still open. Test: `test_trace_problems_never_change_the_job_outcome`.
2. **[MINOR, CONFIRMED]** `POST /process` with a non-object JSON body raised
   `AttributeError` and dropped the connection without a response. Now 400.
3. **[MINOR, CONFIRMED by fuzzing]** A non-string cover `face` raised `TypeError`
   (`unhashable type: 'list'`) in `configurator.validate`. 4000 mutated drafts through
   `preview` and `review` found no other crash site.
4. **[MINOR]** `HANDOVER.md` still told AI clients to expect `server.py` with 8 tools;
   `configure.py` has pointed them at `agent_server.py` (19 tools) since ROC-26.

## Open findings — need a decision

**O1 [IMPORTANT, CONFIRMED] The AI share is weighted by job size, not by decisions.**
The job descriptor's origin is copied to every native line. Probe: an AI intervention
that maps one vent hole inside a 60-part job, plus a 2-part standard job, reports
**95.5 % AI**. `native.regenerate/measure/save/reopen` also count as automation
operations. Proposal: count one operation per occurrence created or changed, report
checks (regenerate, measure, save, reopen) as separate verification counters, and let
the descriptor name the occurrences the AI decided (`ai_occurrences`) while the rest of
the job keeps the standard origin. This changes the metric and one existing test, so it
should be agreed before the dashboard is built on it.

**O2 [IMPORTANT] Agent activity never reaches the registry.** `agent_server.py` logs
tool calls to its own JSONL with no Studio `run_id`, draft or revision. An `ai`
intervention exists only if someone records it by hand, and nothing links it to the
agent run that proposed it. Proposal: optional `studio_run_id` on `AgentSession`, and
an `agent_run_id` field on intervention events, so the dashboard can join both.

**O3 [IMPORTANT] Three logs, three vocabularies.** Registry enums, free-text `actor`,
and the agent JSONL. `OperationLogger.parent_event_id` is the previous event, not a
parent; an exporter must not map it to a span parent or every trace becomes one chain.

**O4 [MINOR]** Every `capture()` call creates a new `job/<uuid>`, so re-running a
failed CAD job is never `attempt=2`; `retry_attempts` stays 0 for real CAD retries.

**O5 [MINOR]** A job whose Python process is killed leaves a `running` span forever.
The run correctly cannot complete, but the dashboard needs a stale-run indicator.

**O6 [INFO]** Model, tokens and cost are null everywhere (`usage_status=unavailable`).
That is correct for subscription clients (Claude Desktop, Codex); it can only be filled
by an API-based agent or by the client's own telemetry export.

**O7 [REQUIREMENT CONFLICT]** `docs/KUBA_HANDOVER.md` says the current direction is
IronCAD 2027; the client uses 2023. For Marcin to confirm.

## Checked and holding

- Offline harness `Verify.ps1 -IronCADYear 2023`: PASS before and after the fixes.
- Studio server on a shared RDP machine: loopback only, random URL token, POST also
  needs the session header and matching Origin. Other Windows users cannot guess it.
- Process panel renders event text with `textContent`; no HTML injection from imported
  reports or agent-written labels.
- Importing a 10 000-event report: 3.1 s; acceptable.
- An AI operation linked to a failed intervention blocks `completed`.

## Dashboard plan (Arize Phoenix, local)

Keep `process_runs.summarize` as the source of the percentages. Add a read-only exporter
that reads the registry (`mode=ro`), job traces and agent JSONL and sends OpenTelemetry
spans to a local Phoenix. Span attributes: `rockpro.origin`, `rockpro.executor`,
`rockpro.stage`, `rockpro.run_id`, draft id/revision/SHA, occurrence id; CAD jobs as
chain spans, agent tool calls as tool spans. Phoenix binds to 127.0.0.1 on the RockPro
machine. Order: O1 decision → O2 link → exporter → agent-side traces.
