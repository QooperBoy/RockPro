# Run an IronCAD job and see it in Phoenix — step by step

For developers and admins of the shared RockPro computer. Tested end to end on
10.11.2026 with IronCAD 2023 (API 25.0.0.18479, trial), Phoenix 21.0.0 and the
commands below, exactly as written. Background and open issues:
[OBSERVABILITY_AUDIT_20261110.md](OBSERVABILITY_AUDIT_20261110.md).

## What you will see

```
Studio draft (revision)          <- what the job is for
  └─ Process run                 <- one "job ticket", bound to that draft revision
       ├─ AI decision            <- an agent decided something, with a written reason
       ├─ CAD job (standard)     <- a script decided, IronCAD executed
       │    └─ native.create / regenerate / measure / save / reopen
       └─ CAD job (ai)           <- same executor, but the value came from the AI decision
            └─ native.*
Agent session (client name)      <- every tool call an AI client made to RockPro
  └─ tool: list_projects, tool: denied, ...
```

Two questions are kept apart on purpose:

- **Origin**: who decided. Values are `standard` (a script or rule), `ai`, `manual` and `unknown`.
- **Executor**: who did it. Values are `sdk` (IronCAD API), `python`, `agent` and `constructor`.

"AI moved the handle and IronCAD executed it" is therefore `origin=ai`,
`executor=sdk`. It is not two operations.

The registry (SQLite) is the source of truth. Phoenix is only a viewer. The
exporter reads the registry and never changes it.

## What works today and what does not

- The end-to-end proof in IronCAD 2023 runs on a small diagnostic part that
  the job creates itself, a 100 × 50 × 20 mm block. One scene parameter drives
  its height natively. The job measures it, saves it, reopens it and measures it again.
- The six parametrized case families in Marcin's 2026-11-03 package (TV,
  Wing Compact, kufer, rack, serwis, T1) are **saved in IronCAD 2027** and
  **cannot be opened in 2023**. That is a limit of IronCAD, not of the code.
  Before any real case family can run on the client's computer, those
  models have to be rebuilt in 2023.
- The share of AI work counts measured CAD steps. A large job therefore weighs
  more than a small one; see audit finding O1. Phoenix shows both views:
  `rockpro.ops.*` counts steps and `rockpro.jobs.*` counts jobs.

## 0. One-time setup (admin, once per computer)

Run everything in **PowerShell**, from the repository folder. In the examples
it is `C:\Users\jakub\Projects\RockPro`; replace it with yours.

1. Install IronCAD 2023 and start it once. Click through the licence or trial
   window until the empty IronCAD window is visible.
2. Set up the RockPro Python environment, if it does not exist yet:
   ```powershell
   cd C:\Users\jakub\Projects\RockPro
   py -3 -m venv Integracja\.venv
   Integracja\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
3. Register the IronCAD 2023 API for your Windows user. You need this once per
   user, and again after installing or uninstalling any IronCAD version:
   ```powershell
   $env:OAPERUSERTLIBREG='1'
   Integracja\.venv\Scripts\python.exe Integracja\rockpro_cad\addin\Repair-IcApi.py --year 2023
   $env:OAPERUSERTLIBREG=$null
   ```
   This writes only under your own user's registry (HKCU). If you skip it after
   uninstalling IronCAD 2027, Python fails with *"error loading type library/DLL"*.
   This happened on 10.11.
4. Install Phoenix. It goes into its own folder, `tools\phoenix\.venv`, and
   needs internet only this once:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Phoenix.ps1 -InstallOnly
   ```
5. Copy the data overlay from the models package (`RockPro_MODELE_20261103\DO_WGRANIA_DO_KODU\artifacts`)
   into the repository's `artifacts\`. Studio needs it. Never overwrite
   existing folders.

## 1. Start the two background windows

Open **two** PowerShell windows in the repository folder and leave them open.

Window A, Phoenix (the dashboard):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Phoenix.ps1
```
Wait for the line `Uvicorn running on http://127.0.0.1:6006`. A few `sqlalchemy`
lines and Pydantic/SAWarning warnings before it are normal. If the script says a
port is already in use, Phoenix is already running somewhere: just open
http://127.0.0.1:6006, or close the other window first. Only one Phoenix and one
Studio per port can run on this computer, including other users' RDP sessions.

Window B, Studio (the configurator):
```powershell
cd Integracja
.\.venv\Scripts\python.exe -X utf8 -m rockpro_cad.reference_studio --bundle ..\artifacts\model-library-20261026 --previews ..\artifacts\family-3d-20261027\index.json --database ..\artifacts\studio.sqlite --port 8765 --no-browser
```
Studio prints a URL like `http://127.0.0.1:8765/<token>/`. Copy it. The token
changes every time Studio starts.

## 2. Make a draft in Studio

1. Open the Studio URL with `wizard.html` added at the end, in a browser on
   the same computer.
2. Type a name in **Nazwa draftu** and click **Zapisz draft** (top right).
3. The address bar now ends with `?draft=<draft id>`. You need that ID. You can
   also list it from the database:
   ```powershell
   Integracja\.venv\Scripts\python.exe -c "import sqlite3;print(sqlite3.connect('artifacts/studio.sqlite').execute('select id,revision from configurator_draft_versions').fetchall())"
   ```

## 3. Run the job and record it

Open a third PowerShell window in the repository folder. Keep IronCAD 2023
open and idle. Don't click in it while the job runs.

```powershell
$py = 'Integracja\.venv\Scripts\python.exe'
$db = 'artifacts\studio.sqlite'
$env:ROCKPRO_IRONCAD_YEAR = '2023'

# a) open a job ticket bound to draft revision 1 (paste your draft id)
& $py -X utf8 scripts\studio_process_run.py --database $db start <draft id> 1 "My first 2023 job"
#    -> copy the "id" from the output, e.g. b10cbc57...
$run = '<run id>'

# b) a scripted (standard) resize: 20 -> 40 mm
& $py -X utf8 scripts\run_2023_parametric_job.py --run-id $run --database $db --target-mm 40

# c) optional: an AI decision, then a resize that uses it
& $py -X utf8 scripts\studio_process_run.py --database $db decide $run ai/thickness-45 "Agent proposed 45 mm because ..."
& $py -X utf8 scripts\run_2023_parametric_job.py --run-id $run --database $db --target-mm 45 --origin ai --intervention-id ai/thickness-45

# d) close the ticket
& $py -X utf8 scripts\studio_process_run.py --database $db finish $run completed
```

Each job ends with `"passed": true` and the measured sizes:
`input 20`, `native_expression_resize 40`, `reopened 40`, `60`, `20`.
The new IronCAD files are in `artifacts\jobs\2023-parametric-<time>\`.
Your own models are never opened.

`finish ... completed` is refused if anything failed or is still running.
In that case close it with `partial` or `failed`; that refusal is intentional.

## 4. Send it to Phoenix

```powershell
tools\phoenix\.venv\Scripts\python.exe -X utf8 scripts\export_to_phoenix.py --database artifacts\studio.sqlite
```

The exporter prints lines like these:

- `sent run <id>: 42 spans`
- `sent agent <file>: 3 spans`
- `waiting: ...` for things still running
- `nothing new`

To keep the dashboard up to date automatically, leave this running in its own
window:

```powershell
tools\phoenix\.venv\Scripts\python.exe -X utf8 scripts\export_to_phoenix.py --database artifacts\studio.sqlite --watch 15
```

Rules:

- A run is sent once it is closed.
- An agent session is sent after 5 minutes without new tool calls. Set this with `--agent-idle`.
- `--flush` sends a snapshot of unfinished items. Avoid it for normal use:
  Phoenix keeps the first copy of each span.

## 5. Read the dashboard

Open `http://127.0.0.1:6006`, then open the **rockpro** project.

- **Traces** tab: one row per process run and per agent session. Click a run
  to see its tree. The **Output** of the top span is the summary:
  `by_origin`, `by_executor`, `percent`, `jobs_by_origin`.
- **Attributes** tab of the top span:
  - `rockpro.ops.ai` and `rockpro.ops.standard` count measured steps.
  - `rockpro.jobs.ai` and `rockpro.jobs.standard` count jobs.
  - `rockpro.interventions` counts AI decisions.
  - `rockpro.ops.failed` and `rockpro.open_spans` show problems.
  - `rockpro.draft_id` and `rockpro.draft_revision` show what the run was for.
- **AI decisions**: spans with the person icon (kind `agent`). The **Input** is
  the agent's written reason.
- **Spans** tab, filter box. Copy these lines exactly:
  - `attributes['rockpro']['origin'] == 'ai'` shows everything an AI decided.
  - `span_kind == 'AGENT'` shows AI decisions and agent sessions.
  - `status_code == 'ERROR'` shows failed steps, jobs and tool calls.
  - `attributes['rockpro']['error_code'] == 'AGENT_TOOL_DENIED'` shows agent calls refused by the policy.

Phoenix's time picker (top right) defaults to *Last 7 Days*. Widen it to see
older runs.

## 6. Agent logs (Claude Code or OpenAI Codex)

AI clients talk to RockPro only through `Integracja\rockpro_cad\mcp\agent_server.py`.
It offers read and proposal tools and nothing that writes, runs CAD or runs
shell commands. Every call is logged to `artifacts\agent-runs\<session>.jsonl`.
The log holds the tool name, status, duration, a hash of the arguments and the
client name. It does not hold the arguments, any results, or file contents.

Connect a client. Use full paths; the Python is the RockPro venv.

- **Claude Code**: add a `.mcp.json` in the folder you open Claude Code in
  (or use `claude mcp add`):
  ```json
  {"mcpServers": {"rockpro-cad": {"command": "C:\\...\\RockPro\\Integracja\\.venv\\Scripts\\python.exe",
    "args": ["C:\\...\\RockPro\\Integracja\\rockpro_cad\\mcp\\agent_server.py"]}}}
  ```
- **OpenAI Codex**: in `%USERPROFILE%\.codex\config.toml`:
  ```toml
  [mcp_servers.rockpro-cad]
  command = 'C:\...\RockPro\Integracja\.venv\Scripts\python.exe'
  args = ['C:\...\RockPro\Integracja\rockpro_cad\mcp\agent_server.py']
  ```
- `python configure.py` writes the same thing to `mcp-config.local.json`.
  It also sets up the demo, so on an existing install copy the two lines instead.

Restart the client and check that its tool list shows `rockpro-cad` with about
19 tools. In Phoenix, sessions appear as *Agent session (claude-code/…)* or
*Agent session (codex-…)*.

Limits of the agent log today:

- Model name, tokens and cost stay empty. Subscription apps don't report them
  to tool servers.
- Sessions are not yet linked to a process run (audit O2). An agent's decision
  reaches the run only when someone records it with `studio_process_run.py decide`.

### Keeping agents away from private files (admin)

`agent_server.py` limits what the agent can do **through RockPro**. It does not
limit the client's own built-in tools: Claude Code and Codex can read files and
run commands themselves. On the shared computer, set this up per Windows user:

- **Claude Code**: use managed or user settings with `permissions.deny` for
  `Bash`, `Edit`, `Write` and `WebFetch`, and allow only `mcp__rockpro-cad__*`.
  Start it in a folder that contains nothing private.
- **Codex**: set `sandbox_mode = "read-only"` and an approval policy that asks
  before every command. Start it in an empty working folder.
- Engineers' private folders should not be readable by the Windows account
  that runs the agent.

Check these keys against the client version you install; they change between
releases.

## 7. Shared computer (RDP) notes

- Phoenix and Studio listen only on `127.0.0.1`. Every user logged in over RDP
  can open them in a browser *on that computer*; nobody can reach them from
  the network. Studio also needs its per-start URL token.
- Phoenix has no login in this setup. Anyone logged into the computer can read
  every trace. Traces contain run labels, AI reasons and draft IDs, not models.
  If that is too open, see Phoenix's authentication settings (`PHOENIX_ENABLE_AUTH`).
- Run **one** IronCAD job at a time. The scripts take a machine-wide CAD lock.
- Phoenix data lives in `artifacts\phoenix\`. Deleting that folder resets the
  dashboard; the registry is unaffected. To re-send everything, also delete
  `artifacts\phoenix\export-state.json`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `COMError ... error loading type library/DLL` | Run step 0.3, then retry. |
| `Operation unavailable` / nothing happens | IronCAD shows a dialog (trial, licence, save?). Close it and retry. |
| `Wrong CAD host: API 29...` | The 2027 IronCAD is running. Close it and start 2023. |
| `Przebieg Studio nie jest aktywny` | That run is already closed. Start a new one. |
| `Najpierw zapisz powód interwencji AI` | Run `decide` before the `--origin ai` job, with the same ID. |
| Phoenix: `Failed to bind to address 127.0.0.1:4317` / `port ... already in use` | Phoenix is already running (another window or RDP user). Use it at http://127.0.0.1:6006, or stop it first. |
| Studio: address already in use on 8765 | Another Studio is running. Close it, or start yours with `--port 8766`. |
| Exporter: `Phoenix did not accept the spans` | Window A (Phoenix) is not running. |
| A corrected run still shows old values | Phoenix keeps the first copy of a span. Delete that trace (`DELETE http://127.0.0.1:6006/v1/traces/<trace id>`), remove the run from `export-state.json` and export again. |
