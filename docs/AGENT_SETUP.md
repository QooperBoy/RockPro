# Connecting an AI agent to RockPro (Claude Code or OpenAI Codex)

Who this is for: developers and admins who want an AI agent to use RockPro, and
anyone testing an "AI decision" end to end. Checked 11.11.2026 on Windows 11
with the RockPro venv (Python 3.14).

## What the agent gets, and what it does not

The agent talks to RockPro through one program,
`Integracja\rockpro_cad\mcp\agent_server.py`. It gives the agent **19
read and proposal tools**, for example `preview_case`, `recommend_case_families`
and `get_layout`. The full list is the `ALLOWLIST` at the top of that file.

- The agent **cannot** change projects, run IronCAD, set stages or run commands
  through RockPro. Those tools exist only in the operator's `server.py`, which
  the IronCAD panel uses.
- Every tool call is logged to `artifacts\agent-runs\<session id>.jsonl`. The
  log holds the tool name, status, duration, a hash of the arguments and the
  client name (for example `claude-code/2.x`). It does **not** hold the
  arguments themselves, the results or any file contents.
- The CAD work is always done by RockPro's own SDK scripts. In the process
  registry and in Phoenix, an "AI job" means *the AI decided the value*
  (`origin = ai`) and *the script carried it out* (`executor = sdk`).

**Important on a shared computer:** the allowlist limits only what the agent
can do *through RockPro*. Claude Code and Codex have their own tools for
reading files and running commands. See [Keeping agents away from private
files](#keeping-agents-away-from-private-files-admin).

## 0. Before you start

- The RockPro venv exists: `Integracja\.venv\Scripts\python.exe`. If it
  doesn't, run `Setup.ps1` (see [HANDOVER.md](../HANDOVER.md)).
- You know the full path of your RockPro folder, e.g. `C:\Users\you\Projects\RockPro`.

## 1. Claude Code

Claude Code reads a file called `.mcp.json` in the folder you open it in.

1. In the RockPro folder, copy the template:
   ```powershell
   Copy-Item .mcp_example.json .mcp.json
   ```
2. Open `.mcp.json` in a text editor. Replace both `C:\\path\\to\\RockPro`
   with your folder. Keep the **double** backslashes; JSON needs them.
   `.mcp.json` is ignored by Git, because it holds your local paths.
3. Start Claude Code **in the RockPro folder**:
   - Terminal: `cd C:\...\RockPro` then `claude`.
   - Desktop app (Code tab): start a new session and choose the RockPro folder.
4. Claude Code asks whether to use the MCP servers from `.mcp.json`. Approve
   `rockpro-cad`.
5. Type `/mcp`. You should see `rockpro-cad` as connected, with 19 tools. In
   Claude Code the tools are named `mcp__rockpro-cad__<tool>`.

You can also add the server without editing JSON (this writes the same `.mcp.json`):
```powershell
claude mcp add rockpro-cad --scope project -- "C:\...\RockPro\Integracja\.venv\Scripts\python.exe" -X utf8 "C:\...\RockPro\Integracja\rockpro_cad\mcp\agent_server.py"
```

## 2. OpenAI Codex

Codex keeps its MCP servers in your user config, not in the project folder.

1. Open `%USERPROFILE%\.codex\config.toml` (create it if it is missing).
2. Add this, with your folder. Single quotes keep the backslashes as they are:
   ```toml
   [mcp_servers.rockpro-cad]
   command = 'C:\...\RockPro\Integracja\.venv\Scripts\python.exe'
   args = ['-X', 'utf8', 'C:\...\RockPro\Integracja\rockpro_cad\mcp\agent_server.py']
   ```
   Don't remove other `[mcp_servers.*]` entries already in the file.
3. Or let Codex write it for you:
   ```powershell
   codex mcp add rockpro-cad -- "C:\...\RockPro\Integracja\.venv\Scripts\python.exe" -X utf8 "C:\...\RockPro\Integracja\rockpro_cad\mcp\agent_server.py"
   ```
4. Start Codex and type `/mcp`. You should see `rockpro-cad` with 19 tools.

Because this config is per Windows user, each person on the shared computer
sets it up in their own account.

## 3. Check that it works

Ask the agent:

> List the rockpro-cad tools you have, then call `list_device_records` and tell me how many records there are.

Then look at the log:
```powershell
Get-ChildItem artifacts\agent-runs\*.jsonl | Sort-Object LastWriteTime | Select-Object -Last 1
```
The newest file is your session. Its name (without `.jsonl`) is the **agent
session id**. Each line is one tool call with `"client": "claude-code/…"` or
`"codex…"`.

After 5 minutes without new calls, the Phoenix exporter sends the session
(guide: [OBSERVABILITY_HOWTO.md](OBSERVABILITY_HOWTO.md), step 4). In Phoenix
it appears as **Agent session (claude-code/…)**, with one child span per tool call.

## 4. Test an AI decision end to end

This checks the whole path. A real agent proposes a value using RockPro tools;
IronCAD 2023 builds it; the dashboard shows both the agent's tool calls and
the AI job.

You need: IronCAD 2023 open and idle, Phoenix running, and a Studio draft
(steps 1–2 of [OBSERVABILITY_HOWTO.md](OBSERVABILITY_HOWTO.md)).

Use a **new** agent session for this test. A session may make 30 RockPro
calls within 120 seconds of its first call; after that, every call is refused.

1. **Open a run** (job window, as in the HOWTO step 3):
   ```powershell
   $py = 'Integracja\.venv\Scripts\python.exe'
   $db = 'artifacts\studio.sqlite'
   & $py -X utf8 scripts\studio_process_run.py --database $db start <draft id> 1 "Agent decision test"
   $run = '<run id from the output>'
   ```
2. **Ask the agent** (in Claude Code or Codex, started as above):
   > Use only the rockpro-cad tools. Call `preview_case` for a simple case of
   > your choice and look at the panel thickness it uses. Propose one panel
   > thickness in whole millimetres between 5 and 500 (not 60) for a test
   > part, and explain in two sentences which tool result you based it on.
   > Don't edit any files.
3. **Find the agent session id**: the newest file in `artifacts\agent-runs`
   (the command in section 3).
4. **Record the decision** with the agent's own reason and the session id:
   ```powershell
   & $py -X utf8 scripts\studio_process_run.py --database $db decide $run ai/agent-thickness "agent_session=<session id> client=claude-code: <paste the agent's reason>"
   ```
5. **Run the job with the agent's value** (here 18 mm as an example):
   ```powershell
   & $py -X utf8 scripts\run_2023_parametric_job.py --run-id $run --database $db --target-mm 18 --origin ai --intervention-id ai/agent-thickness
   ```
   It must end with `"passed": true`, and `native_expression_resize` must show the agent's value.
6. **Close and export:**
   ```powershell
   & $py -X utf8 scripts\studio_process_run.py --database $db finish $run completed
   tools\phoenix\.venv\Scripts\python.exe -X utf8 scripts\export_to_phoenix.py --database artifacts\studio.sqlite --agent-idle 0
   ```
   `--agent-idle 0` sends the agent session now, instead of after 5 minutes.
   Only use it when the agent has finished.
7. **Check in Phoenix** (`http://127.0.0.1:6006` → rockpro → Traces):
   - **Agent session (…)**: the tools the agent really called; none should be refused.
   - **Process run: Agent decision test**: an *AI decision* span whose input
     is your reason with the session id, and one *CAD job (ai)*.
   - The AI job's measured size equals the agent's proposal.

What this test proves: a real agent connects, uses only allowed tools, and
its proposal is carried out and checked in IronCAD. What it does **not**
prove: that the decision came from that agent. You copy the value, and the
two traces are linked only by the session id you typed. Linking them
automatically is audit finding O2
([OBSERVABILITY_AUDIT_20261110.md](OBSERVABILITY_AUDIT_20261110.md)).

## Keeping agents away from private files (admin)

The client's rule is that AI must not touch engineers' private files. RockPro
can only enforce this for its own tools. The rest is set up per Windows user:

- **Claude Code**: in `.claude\settings.json` (project) or the user/managed
  settings, deny the built-in tools and allow only RockPro:
  ```json
  {
    "permissions": {
      "allow": ["mcp__rockpro-cad"],
      "deny": ["Read", "Glob", "Grep", "Edit", "Write", "NotebookEdit", "Bash", "PowerShell", "WebFetch", "WebSearch"]
    }
  }
  ```
  `Read` matters: denying only `Edit`/`Write` still lets the agent read files.
  Managed settings (set by an admin) can't be overridden by the user;
  project and user settings can.
- **Codex**: `sandbox_mode = "read-only"` stops writes and commands, but it
  does **not** stop reading. Use `approval_policy = "untrusted"` so Codex
  asks before running commands, and start Codex in an empty folder.
- **Windows (the real boundary)**: engineers' private folders must not be
  readable by the Windows account that runs the agent. Client settings help;
  file permissions enforce.
- Start agents in a folder that contains nothing private. The RockPro checkout
  itself contains no customer data; `artifacts\` may contain CAD outputs.

Setting names change between client versions. Check them against the version
you install, and test by asking the agent to read a file it shouldn't.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/mcp` shows `rockpro-cad` failed | Wrong path in `.mcp.json`/`config.toml`, or the venv is missing. Run the `command` with its `args` in PowerShell yourself; it should wait silently (Ctrl+C to stop). |
| Claude Code doesn't ask about `.mcp.json` | It was opened in another folder, or you declined earlier. Open it in the RockPro folder; check `/mcp`. |
| Agent says a tool is refused (`AGENT_TOOL_DENIED`) | The tool is not on the allowlist, by design. |
| `AGENT_TIME_LIMIT` or `AGENT_CALL_LIMIT` | Session budget (`Policy` in `agent_server.py`): 30 calls and 120 s, counted from the agent's first RockPro call. Start a new client session (Claude Code: new session; Codex: restart). Keep one task per session. Audit O11. |
| No new file in `artifacts\agent-runs` | The agent didn't call any RockPro tool, or `ROCKPRO_AGENT_LOG_DIR` points elsewhere. |
| Exporter: `waiting: agent session …` | Normal while the agent is active; sent after 5 idle minutes (or `--agent-idle 0`). |
