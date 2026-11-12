# The RockPro Phoenix dashboard — user manual

For everyone who runs RockPro jobs or AI agents and wants to see what happened:
which steps ran, which values a script chose and which an AI chose, and what
failed. Checked on 12.11.2026 with IronCAD 2023, Phoenix 21.0.0 and the
commands below.

Phoenix is a local web page at **http://127.0.0.1:6006**. It only shows data;
the source of truth is the RockPro registry (`artifacts\studio.sqlite`) and the
agent logs (`artifacts\agent-runs\`). Nothing you do in Phoenix changes RockPro.

## What is recorded automatically

| What | Recorded when | Appears in Phoenix |
|---|---|---|
| A CAD job (`run_2023_parametric_job.py`) | always: the job opens its own run and closes it at the end | about 30 s after the job ends |
| Each IronCAD step of that job (create, regenerate, measure, save, reopen) | always, as part of the job | with the job |
| An AI decision and its reason | when the job is run with `--origin ai --decision-reason "…"` | with the job |
| Every tool call an AI agent (Claude Code, Codex) makes to RockPro | always (`agent_server.py`) | 5 minutes after the agent's last call |

Not recorded (yet): clicks in the IronCAD window itself, work in the RockPro
panel (`server.py`), and anything an agent does outside RockPro (its own file
or shell tools). See the proposals for Marcin in the audit document.

## 1. Start it (once)

You need the one-time setup from [OBSERVABILITY_HOWTO.md](OBSERVABILITY_HOWTO.md),
step 0. Then, in PowerShell in the RockPro folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Observability.ps1
```

It prints:

```
Phoenix:  running at http://127.0.0.1:6006
Exporter: running (process 6032), every 30 s, database C:\...\RockPro\artifacts\studio.sqlite
Open http://127.0.0.1:6006  ->  project 'rockpro'  ->  Traces.
```

Both run in the background, without windows, and keep running after you
close PowerShell. Running the command again is safe; it only starts what is missing.

| You want to… | Add to the command |
|---|---|
| start it automatically when you log in to Windows | `-EnableAtLogon` (undo: `-DisableAtLogon`) |
| see whether it runs, and the last export messages | `-Status` |
| stop it | `-Stop` |

On the shared (RDP) computer there is one Phoenix for everybody. `-Stop` stops
your exporter, and Phoenix only if you started it.

**Studio must use the same database.** Start Studio with
`--database ..\artifacts\studio.sqlite` (HOWTO step 1, window B) and save at
least one draft. A job is always bound to a draft revision; that is how you
later know what the job was for.

## 2. Run jobs: nothing else to do

Start IronCAD 2023 first and leave it idle. Then:

```powershell
$py = 'Integracja\.venv\Scripts\python.exe'
$env:ROCKPRO_IRONCAD_YEAR = '2023'

# a job whose value comes from a rule or script (origin "standard")
& $py -X utf8 scripts\run_2023_parametric_job.py --target-mm 40

# a job whose value an AI proposed: give the AI's reason, it is recorded first
& $py -X utf8 scripts\run_2023_parametric_job.py --target-mm 12 --origin ai --decision-reason "agent_session=<id> client=claude-code: proposed 12 mm because ..."
```

The first line of the output names the run:
`recording into new run 7f2e28fa… (draft b4be9a8c… rev 1); it is closed automatically`.
The last line says how it was closed:

- `completed`: everything finished.
- `partial`: the job finished, but something in the recording was incomplete.
- `failed`: the job failed. The error is printed above, as before.

The run is bound to the **newest saved draft**. To choose one, add
`--draft-id <id> --draft-revision <n>`. To give the run a name, add
`--label "..."`. To run without recording, add `--no-record`; the job then
never appears in Phoenix.

Several jobs in **one** run (one ticket for a whole case) is still possible
by hand. You open the run, pass `--run-id` to each job, and close it yourself:
see HOWTO step 3.

## 3. Open the dashboard

1. Open **http://127.0.0.1:6006** in a browser on the same computer.
2. Click the **rockpro** card. The **Spans** tab opens; with its default filter
   `parent_id is None` it shows one row per process run and per agent session,
   newest first.
3. The time range is top right (**Last 7 Days** by default). Widen it for older
   work.

Row types (column **kind** and **name**):

| kind | name | What it is |
|---|---|---|
| chain | `Process run: <label>` | one recorded run: a job ticket bound to a draft revision |
| agent | `Agent session (claude-code/…)` or `(codex…)` | one AI client session and its RockPro tool calls |

The **output** column of a process run is its summary, for example
`{"by_origin": {"standard": 8, "ai": 10, …}, "by_executor": {"sdk": 18, …}}`.

## 4. Read a process run

Click the row. A panel opens with the tree on the left and details on the right.

```
Process run: 2023 parametric job: 12 mm (ai)     status OK, 3.9 s
├─ AI decision: ai/resize-12mm                   Input = the reason you gave
├─ CAD job (standard)                            the "create" job
│   └─ native.create, native.regenerate, native.measure, native.save, native.reopen …
└─ CAD job (ai)                                  the job that used the AI's value
    └─ native.measure, native.regenerate, …
```

Click any node. On the right:

- **Info**: **Input** and **Output**. For an AI decision the Input is the
  written reason. For the run itself the Output is the summary.
- **Attributes**: everything RockPro recorded about that step. The useful ones:

| Attribute | Meaning |
|---|---|
| `rockpro.origin` | who **decided**: `standard` (rule/script), `ai`, `manual`, `unknown` |
| `rockpro.executor` | who **did** it: `sdk` (IronCAD API), `python`, `agent`, `constructor` |
| `rockpro.ops.ai`, `rockpro.ops.standard` | (run) measured steps by origin |
| `rockpro.percent.ai` | (run) the AI share of those steps |
| `rockpro.jobs.ai`, `rockpro.jobs.standard` | (run) jobs by origin |
| `rockpro.interventions` | (run) number of AI decisions |
| `rockpro.ops.failed`, `rockpro.open_spans` | (run) problems: failed or unfinished steps |
| `rockpro.draft_id`, `rockpro.draft_revision` | (run) which Studio draft the run was for |
| `rockpro.intervention_id` | (AI job) the decision it used |

"AI decided, IronCAD executed" is one step with `origin=ai`, `executor=sdk`;
it is not counted twice.

**Read the AI share with care.** `rockpro.percent.ai` counts measured steps,
so a big job weighs more than a small one. Compare it with `rockpro.jobs.*`
(audit finding O1, a decision for Marcin).

Status colours: **OK** (green) finished, **ERROR** (red) failed, **UNSET**
still running or refused by a limit.

## 5. Read an agent session

Click an `Agent session (…)` row. Each child is one tool call, named
`tool: <name>`. The session's Output lists the tools and counts:
`{"tools": ["preview_layout"], "failed": 0, "blocked": 0, "refused": 0}`.

- `failed`: the tool raised an error.
- `blocked` (red): the tool rejected the agent's input; the attribute
  `rockpro.diagnostic_codes` says why, e.g. `FIELD_REQUIRED`.
- `refused`: the RockPro policy refused the call: a tool the agent may not use
  (`AGENT_TOOL_DENIED`), or the session's 30-call / 120-second budget.

The log never contains the agent's arguments, results or file contents; only
a hash of the arguments (`rockpro.arguments_sha256`). The session ID in the
name of its log file (`artifacts\agent-runs\<id>.jsonl`) is
`rockpro.agent.run_id`. Put it in `--decision-reason` when you run a job with
the agent's value; that is how the two are connected today (audit O2).

## 6. Find things: filters

In the **Spans** tab, replace the filter `parent_id is None` with one of these
(copy exactly) and press Enter:

| Show me… | Filter |
|---|---|
| everything an AI decided | `attributes['rockpro']['origin'] == 'ai'` |
| AI decisions and agent sessions | `span_kind == 'AGENT'` |
| everything that failed | `status_code == 'ERROR'` |
| agent calls refused by the policy | `attributes['rockpro']['error_code'] == 'AGENT_TOOL_DENIED'` |
| all steps of one run | `attributes['rockpro']['run_id'] == '<run id>'` |

## 7. "Where is my run?"

```powershell
.\scripts\Start-Observability.ps1 -Status
```

The last lines are the exporter's messages:

| Message | Meaning, and what to do |
|---|---|
| `sent run <id>: 22 spans` | it is in Phoenix; check the time range |
| `waiting: run <id> '…' is still open` | the run was opened by hand and never closed. Close it: `studio_process_run.py finish <id> completed` (or `partial` / `failed`) |
| `… Open for 33 h: probably abandoned` | the same, but old: almost certainly forgotten. Close it as `failed` |
| `waiting: agent session <id> (still active)` | the agent was used in the last 5 minutes; it comes later |
| `export failed (retrying): …` | Phoenix is not running; start it again |

List the runs that were never closed:

```powershell
Integracja\.venv\Scripts\python.exe -X utf8 scripts\studio_process_run.py list --open
```

A job you ran with `--no-record` or with a different `--database` is not in
this registry, so it never appears.

## 8. Good to know

- **Privacy.** Phoenix has no login here. Anyone logged in to this computer
  can open it and read every run label, AI reason and draft ID (no models, no
  files). Don't put personal data in labels or reasons.
- **Corrections.** Phoenix keeps the first copy of everything. A closed run is
  never sent twice, and a run can't change after it is closed.
- **Reset the dashboard.** Stop it, delete `artifacts\phoenix`, and start it
  again: everything in the registry is sent again. The registry itself is not
  touched.
- **Another database.** Set `ROCKPRO_STUDIO_DATABASE` (or pass `-Database` /
  `--database`); the job, `studio_process_run.py` and the exporter all use it.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No saved Studio draft in …\studio.sqlite` | Start Studio with that database and save a draft (HOWTO steps 1–2), or pass `--draft-id`. |
| `Phoenix stopped while starting` | The log lines printed above say why. Often port 4317 is taken by another Phoenix: `Get-NetTCPConnection -LocalPort 4317`. |
| Page doesn't open | `-Status`. If Phoenix is not running, start it again. Logs: `artifacts\phoenix\logs\`. |
| A run is missing | Section 7. |
| `MK_E_UNAVAILABLE` from the job | IronCAD 2023 is not running or shows a dialog. The run is closed as `failed` automatically. |
| `--origin ai needs --decision-reason` | Give the AI's reason, so the decision is recorded before the job uses it. |
