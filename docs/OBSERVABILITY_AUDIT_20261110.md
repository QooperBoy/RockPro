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

5. **[MINOR, CONFIRMED]** The real-stdio test of `agent_server.py` wrote its session into
   the real `artifacts/agent-runs`, so every test run would appear as an agent session on
   the dashboard. Four such files were found and moved to `artifacts/agent-runs-test-leftovers`.
   `ROCKPRO_AGENT_LOG_DIR` now redirects the log; the test uses a temp folder and checks it.
6. **[ADDED]** Agent logs record the MCP `clientInfo` (e.g. `claude-code/2.x`,
   `codex-mcp-client/…`) as `client`, limited to a short safe string. It is a label the
   client reports, not proof of identity.
7. **[ADDED]** `studio_process_run.py` takes `--database` (it always used the default
   SQLite, while Studio may use another file) and a `decide` command that records an AI
   decision with its reason and the current time.
8. **[ADDED]** Phoenix exporter (`rockpro_cad/phoenix_export.py`, `scripts/export_to_phoenix.py`),
   `scripts/Start-Phoenix.ps1`, the 2023 end-to-end job `scripts/run_2023_parametric_job.py`
   and the guide [OBSERVABILITY_HOWTO.md](OBSERVABILITY_HOWTO.md).

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

**O7 [REQUIREMENT CONFLICT → docs updated]** `docs/KUBA_HANDOVER.md` said the current
direction was IronCAD 2027; the client uses 2023. HANDOVER, KUBA_HANDOVER and DEVELOPMENT
now name 2023 as the target. Marcin should still confirm the plan for the 2027-saved models (O10).

**O8 [MINOR, CONFIRMED]** `timestamp_utc` is free text (up to 80 characters). Nothing checks
the format, or that the time falls inside the run. In the E2E test, a hand-written decision
dated 12:00 UTC stretched a 68-second run to 1 h 9 min in Phoenix. The exporter now bounds
the run span by the run's own `created_at`/`updated_at` and counts
`rockpro.events_outside_run_window`; the registry itself still accepts any text.
Proposal: require ISO-8601 with a timezone in `validate_event`.

**O9 [IMPORTANT, shared computer]** `agent_server.py` limits only what an agent can do
*through RockPro*. Claude Code and Codex have their own file and shell tools. "Agents must
not touch engineers' private files" has to be enforced by the client configuration and by
Windows permissions, not by the MCP allowlist. See the admin section of
[OBSERVABILITY_HOWTO](OBSERVABILITY_HOWTO.md).

**O10 [BLOCKER for real families on 2023]** All six parametrized family models in the
2026-11-03 package are saved in IronCAD 2027 (`*_IC2027.ics`), and 2023 cannot open them.
The 2023 end-to-end proof therefore runs on a diagnostic part that the job creates itself.

**O11 [IMPORTANT, CONFIRMED, partly fixed 11.11]** The agent session's 120-second budget
started when `agent_server.py` started. Claude Code and Codex start it when the window
opens, so a user who typed the first prompt after two minutes got `AGENT_TIME_LIMIT` on
every RockPro call. Fixed: the clock starts at the first tool call
(`test_time_budget_starts_at_first_call_not_when_client_opens`). Still open: one
interactive session with follow-up questions over more than 2 minutes, or more than 30
calls, is still refused until the client is restarted. The budget fits autonomous runs,
not conversations. Options for Marcin: a per-turn budget, an idle reset, or a larger
limit configured per client in `.mcp.json`.

**O12 [IMPORTANT, CONFIRMED, fixed 12.11]** The agent log recorded a tool call as
`passed` whenever the tool did not raise. Tools such as `preview_case` report rejected
input as data (`"status": "blocked"` with diagnostics), so in the first real Claude Code
session 11 rejected `preview_case` calls showed as passed, and Phoenix would have shown
them green. The log now writes `blocked` / `AGENT_TOOL_BLOCKED` with the tool's
status and its diagnostic codes only (no paths or messages). The exporter shows these
spans as errors and counts `rockpro.agent.blocked_calls`. The agent's response is unchanged.

Observed in the same session: the only project had no saved case request, so a
`preview_case` call needed a complete 42 KB plan written by hand. The agent spent its
120 s budget on that and was then refused (O11 in practice). The test now uses
`preview_layout` ([AGENT_SETUP.md](AGENT_SETUP.md), section 4).

## End-to-end test — 10 November 2026, IronCAD 2023

Host 25.0.0.18479 (base 2023, trial; the client has PU1 SP1). Steps exactly as in
[OBSERVABILITY_HOWTO](OBSERVABILITY_HOWTO.md):

| Step | Result |
|---|---|
| Python ↔ IronCAD COM after uninstalling 2027 | FAIL at first: stale per-user 29.0 ICAPI registrations ("error loading type library"). PASS after `Repair-IcApi.py --year 2023` (HKCU only, backed up), without restarting IronCAD |
| Add-in build for 2023 | PASS (`Build.ps1 -IronCADYear 2023`); registration and panel click NOT RUN (they need IronCAD closed) |
| Studio on a new database; save a draft in the wizard | PASS |
| Process run bound to draft revision 1 | PASS |
| Job "create" (C# probe): part, scene parameter, save, reopen | PASS |
| Job "resize" (native expression): 20 → 40 mm, save, reopen at 40, then 60 and 20 | PASS |
| AI decision (`decide`), then resize to 45 mm with `origin=ai` | PASS |
| Close the run as `completed` | PASS: 36 steps, 26 standard / 10 AI (27.8 %), 4 jobs (3 standard, 1 AI), 1 decision; O1 is visible |
| Agent session over stdio (one allowed and one denied call) | PASS: logged with the client name; the denied call shows `AGENT_TOOL_DENIED` |
| Export to Phoenix 21.0.0, then re-export | PASS: 42 + 3 spans; the re-export sends nothing. Phoenix ignores span IDs it already has, so correcting a span means deleting its trace first |
| Phoenix filters `attributes['rockpro']['origin'] == 'ai'` and `span_kind == 'AGENT'` | PASS |

No source model was opened. Every CAD file is new, under `artifacts/`.

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

Status 10.11: the exporter is built and in use, without waiting for O1/O2. It shows the
current step-weighted share (`rockpro.ops.*`) next to job counts (`rockpro.jobs.*`) and
AI decisions, so O1 can be judged on real data. O2 still needs a decision.

Status 12.11 (branch `feat/observability-by-default`): observability is on by default.
`scripts/Start-Observability.ps1` starts Phoenix and the exporter in the background
(optionally at Windows login). `run_2023_parametric_job.py` opens and closes its own run
(bound to the newest saved draft) and can record the AI decision itself
(`--decision-reason`); `--no-record` opts out. The exporter flags runs open for more
than 2 hours as probably abandoned, and `studio_process_run.py list --open` lists them
(a first answer to O5). The shared default database for these tools is
`artifacts/studio.sqlite` (or `ROCKPRO_STUDIO_DATABASE`). User manual:
[PHOENIX_DASHBOARD.md](PHOENIX_DASHBOARD.md). Not covered: the RockPro panel
(`server.py`) and manual work in IronCAD.
