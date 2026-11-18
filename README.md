# ctrlX Engineering MCP

An MCP server that lets an AI agent drive ctrlX PLC Engineering (CODESYS V3) through the
CODESYS Scripting Engine: read and write POUs, build, go online, start/stop, read and write
variables, and record traces. It is a standard MCP server over stdio, so any MCP client can use it (Claude Code
is the one it was developed with).

```
MCP client (agent) --stdio--> server/server.py (CPython, FastMCP)
                          | JSON lines over TCP + token (SSH reverse tunnel)
                          v
   PLC Engineering (Windows) running bridge/bridge.py (IronPython 2.7, inside the IDE)
```

Tested with ctrlX PLC Engineering 4.6.2 on Linux+Windows split setup (against a ctrlX CORE), and 4.6.1
(ScriptEngine 4.2.0.0) with everything on one Windows PC.

## Setup

**Everything on one Windows PC (the MCP client and PLC Engineering together)**

    scripts\install_windows.bat

It first checks for Python 3.10 or newer, git, the IDE and, optionally, the `claude` CLI. Then it creates `.venv`,
installs the requirements, creates `scripts\.ctrlx_token`, writes `scripts\config.bat` with `TUNNEL=0` and reports
which of the [required skills](#required-skills-ladder-and-hmi-tools) are present. Last it registers the server:
with Claude Code (`claude mcp add`, local scope) when the `claude` CLI is found, otherwise it prints a generic
configuration to add to your MCP client, see [Registering with an MCP client](#registering-with-an-mcp-client).
The server reads the token from the file when `CTRLX_MCP_TOKEN` is not set. Then run `scripts\start_bridge.bat`,
(re)start your MCP client and ask it to `ping`. No SSH or tunnel is involved: the server talks to the bridge on
127.0.0.1:8765 directly. The ladder and HMI tools need three skills, see
[Required skills](#required-skills-ladder-and-hmi-tools) for the repositories and install commands.

**Split setup (the MCP client on Linux/WSL, PLC Engineering on Windows)**

**Linux / WSL (where the MCP client runs)**

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    scripts/install_token.sh          # creates .ctrlx_token, exports CTRLX_MCP_TOKEN from ~/.bashrc

`.mcp.json` registers the server for Claude Code (and any client that reads that file) in this folder. The token is
read from the environment, so open a new terminal after installing it. Other clients: see
[Registering with an MCP client](#registering-with-an-mcp-client).

**Windows (where PLC Engineering runs)**

1. Copy this folder (at least `bridge/` and `scripts/`) to the Windows machine.
2. Copy the token printed by `install_token.sh` into `scripts\.ctrlx_token`.
3. Copy `scripts\config.example.bat` to `scripts\config.bat` and edit it (Linux user and host,
   IDE path, optional project to open).
4. Make SSH login to the Linux box key-based (`ssh-keygen`, then `ssh-copy-id`), or the tunnel
   window waits for a password.
5. Run `scripts\start_bridge.bat`. It opens the tunnel and starts the IDE with the bridge loaded.

The bridge listens on 127.0.0.1 only, and every request needs the token. `CTRLX_MCP_PORT` changes
the port (default 8765), `CTRLX_MCP_ALLOW_EXEC=0` disables the `exec_script` tool.

Check it from Linux: ask the agent to `ping`, or run

    CTRLX_MCP_TOKEN=$(cat .ctrlx_token) .venv/bin/python -c "import sys; sys.path.insert(0,'server'); import server; print(server.call('ping'))"

If the IDE misbehaves when the script loads at startup, set `AUTORUN=0` in `config.bat` and run
the bridge from Tools > Scripting > Execute Script File. Its log is `%TEMP%\ctrlx_bridge.log`
(`online context saved` and `ui dispatch ready` should appear, then `loop started`).

## Registering with an MCP client

The server is a plain stdio MCP server: the client starts `python server/server.py` and talks MCP over its stdin and
stdout. Any client that can launch a command works. Add an entry like this to the client's MCP configuration (use
absolute paths; on Linux/WSL the interpreter is `.venv/bin/python`):

```json
{
  "mcpServers": {
    "ctrlx-engineering": {
      "command": "C:\\path\\to\\ctrlx-engineering-mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\ctrlx-engineering-mcp\\server\\server.py"],
      "env": { "CTRLX_BRIDGE_HOST": "127.0.0.1", "CTRLX_BRIDGE_PORT": "8765" }
    }
  }
}
```

The token is read from `CTRLX_MCP_TOKEN` or, when that is not set, from `scripts\.ctrlx_token`, so a client that cannot
pass environment variables still works. Claude Code can do the same with
`claude mcp add ctrlx-engineering -s local -- <python> <server.py>`, which is what the installer runs. The
`.mcp.json` in this folder is the Linux version of the snippet above; on Windows it does not apply (it points at
`.venv/bin/python`), so the client shows a connection error until the server is registered with Windows paths.

## Required skills (ladder and HMI tools)

**The release zip already contains them** in `skills/` next to `server/`, and the server and the installer use that
folder automatically, so with the zip there is nothing to install. The rest of this section is for a clone of the
repository, or to update the skills.

Most tools need nothing but this repo. The ladder and HMI tools run scripts from three skill folders (a `SKILL.md`
with guidance plus Python scripts; the tools only run the scripts, so no particular agent is needed) that live in
their own repositories. Install them first or those tools fail saying the skill script was not found:

| Skill (folder name) | Repository | Needed for |
|---|---|---|
| `ctrlx-engineer` | [rduffy190/CtrlxPlcSkill](https://github.com/rduffy190/CtrlxPlcSkill) | `ladder_check`, `ladder_import` (the ST/PLCopenXML converter and the house conventions) |
| `codesys-lad` | [rduffy190/CtrlxLadderSkill](https://github.com/rduffy190/CtrlxLadderSkill) | `ladder_check`, `ladder_import`, `ladder_export` (the ladder compiler and tracer) |
| `ctrlx-hmi` | [rduffy190/ctrlx-hmi-skill](https://github.com/rduffy190/ctrlx-hmi-skill) | `build_hmi`, `publish_hmi` (the visualization generator and SVG preview) |

Clone each one into the skills folder under the folder name in the first column (the repository names differ from
the folder names, and the converter looks for `codesys-lad` next to `ctrlx-engineer`). The default skills folder is
`.claude/skills` in your home directory (Claude Code's convention); any other folder works if you set
`CTRLX_SKILLS_DIR`. On Windows (PowerShell):

    git clone https://github.com/rduffy190/CtrlxPlcSkill     "$env:USERPROFILE\.claude\skills\ctrlx-engineer"
    git clone https://github.com/rduffy190/CtrlxLadderSkill  "$env:USERPROFILE\.claude\skills\codesys-lad"
    git clone https://github.com/rduffy190/ctrlx-hmi-skill   "$env:USERPROFILE\.claude\skills\ctrlx-hmi"

On Linux/WSL:

    git clone https://github.com/rduffy190/CtrlxPlcSkill     ~/.claude/skills/ctrlx-engineer
    git clone https://github.com/rduffy190/CtrlxLadderSkill  ~/.claude/skills/codesys-lad
    git clone https://github.com/rduffy190/ctrlx-hmi-skill   ~/.claude/skills/ctrlx-hmi

The ctrlx-hmi skill also needs templates that you make once from your own ctrlX PLC Engineering (they are exports of
CODESYS objects, so they are not shipped); its README explains it under "First run". Set `CTRLX_SKILLS_DIR` to use
another folder; without it the server looks in `skills/` next to `server/` (the release zip), then in
`~/.claude/skills`. The skills run on the machine where the MCP server runs, not on the
IDE machine. `scripts\install_windows.bat` only checks for them and prints these commands for any that are missing;
it never installs them for you.

## Windows vs Linux

Which setup you have decides how the server is registered and what it can do for you. The tools are the same in
both; the differences are in starting the IDE and where files live.

| | Everything on one Windows PC | MCP client on Linux/WSL, IDE on Windows (tunnel) |
|---|---|---|
| Register the server | `scripts\install_windows.bat` (registers Claude Code at local scope; for another client use the snippet above; for Claude Code at user scope, add it to `~/.claude.json`) | `.mcp.json` in this folder (`.venv/bin/python`); open a new terminal after `install_token.sh` |
| Token | `scripts\.ctrlx_token`, read by the server | `CTRLX_MCP_TOKEN` in the environment, the same value in `scripts\.ctrlx_token` on Windows |
| Reaching the bridge | direct, `127.0.0.1:8765` (`TUNNEL=0`) | SSH reverse tunnel opened by `start_bridge.bat` (`TUNNEL=1`, needs key-based SSH to the Linux box) |
| Starting the IDE | automatic: the first tool call runs `start_bridge.bat` and waits about a minute (`CTRLX_AUTOSTART=0` turns it off) | by hand: run `scripts\start_bridge.bat` on the Windows machine before using the tools |
| Skills (`ctrlx-engineer`, `codesys-lad`, `ctrlx-hmi`) | `%USERPROFILE%\.claude\skills` or `CTRLX_SKILLS_DIR` | `~/.claude/skills` or `CTRLX_SKILLS_DIR` on the Linux side |
| Paths you pass | Windows paths, for the IDE and the server alike | Project and object paths are Windows paths on the IDE machine (`open_project`, `import_plcopen` with `file`); files for the server (`import_visu`'s export, `build_hmi`'s screen) are Linux paths and are sent over the tunnel as text |
| HMI import | the bridge runs the headless helper IDE on this PC | the same: the bridge, on the Windows machine, runs it; nothing extra to install on Linux |

Not available over the tunnel: auto-start (the server cannot launch an IDE on another machine). The helper IDE
for `import_visu` needs a free port on the Windows machine (`CTRLX_HELPER_PORT`, default 8766), which is
not part of the tunnel.

## Tools

Project: `ping`, `open_project`, `save_project`, `get_tree`, `get_pou`, `set_pou`, `create_pou`, `add_task_call`, `remove_task_call`, `list_io`, `map_io`,
`create_dut`, `create_gvl`, `create_folder`, `move_object`, `delete_object`, `build`, `messages`.
`create_folder` (a path such as `02_Gapper/POUs` creates every missing level, repeats are safe) and `move_object` group objects into folders; names do not change, so code and task calls keep working. The application must be logged out.
HMI: `build_hmi` (screen definition to `.export`, plus SVG previews), `import_visu` (a visugen `.export` into the open project),
`add_web_visu` (web visualization that starts on a visu), `publish_hmi` (build, import, web visu and save in one call; needs the ctrlx-hmi skill).

PLCopenXML: `export_plcopen`, `import_plcopen`. Ladder: `ladder_check`, `ladder_import`, `ladder_export`.
Online (the user logs in and downloads in the IDE themselves; `login` can fail on the download confirmation dialog): `login`, `logout`, `run_state`, `plc_start`, `plc_stop`, `read_var`, `write_var`.
Trace: `list_traces`, `get_trace`, `create_trace`, `trace_setup`, `trace_run`, `trace_status`, `trace_stop`, `trace_wait`, `trace_save`.
Escape hatch: `exec_script` (runs IronPython in the IDE; use `dir()` to explore the API).

Object paths are `/`-separated names from the project root, for example
`Device/Plc Logic/Application/PRG_Main`. Name matching is exact; check `get_tree` for the
spelling (`Plc Logic` vs `PLC Logic`).

## Rules for the agent

These are written for the agent driving the tools. Put them in its instructions or system prompt, whichever client
you use.

- **Always ask the user how to download the application** before `login`. An application download
  can replace the program, reset variables to their initial values and stop a running application.
  (A *trace* download is a different thing, see Tracing.) Do not decide it, and do
  not log in "just to look" at a running machine.
- **`change="Never"` stops a running controller when you log in** (seen on a ctrlX CORE). The default
  is `Try` (online change), which keeps it running; it is also what `trace_run` uses.
- To attach to a running PLC use `login` with `change="Try"`. The `download` flag is
  passed to the IDE as "delete foreign applications" on the controller, needs extra rights (a
  permissions error otherwise) and defaults to False; leave it off unless the user asks.
- **Always ask the user how many samples the trace should use** before setting `samples` in `trace_setup`;
  never pick a number yourself.
- `write_var`, `plc_start`, `plc_stop` and `login` affect a running machine; confirm first.
- **A program only runs if a task calls it.** After importing or creating a `PRG_`, use `add_task_call`
  (default task `MainTask`). The IDE may show a dialog while the task is re-imported; tell the user to watch it.

### Tracing

`create_trace name="MyTrace"` adds an empty trace object. Scripts cannot create one (`trace.create` returns a stub)
and no template is shipped, so the bridge copies a trace that is already in the project (`from_trace`, or the first
one) and clears it. A project needs one trace added in the IDE once (right-click the Application > Add Object >
Trace); after that `create_trace` makes as many as you like. `list_traces` and `get_trace` read what exists; `trace_setup` changes only the
arguments you give (`variables`, `add_variables`, `remove_variables`, trigger, `trigger_enabled`, `auto_start`,
`task_name`, `record_condition`, `comment`). Then:

    trace_setup  trace="Device/Plc Logic/Application/MyTrace"  samples=<ask the user>  variables=["PRG_Main.bEnable", ...]
    trace_run    app="Device/Plc Logic/Application"  trace=...     # downloads and starts
    ... do things (write_var, plc_start, ...) ...
    trace_save   trace=...      # stops if needed, exports, returns the value changes per variable

Repeat runs of the same trace: `trace_run ... download=False` re-arms the trigger and starts the
trace already on the controller, with no download. `trace_stop` stops it early. Download again
whenever the trace's variables or settings change.

**The trace download is not an application download.** It sends only the trace configuration to the
controller; the PLC program is untouched and the controller keeps running. On trace download the IDE
shows a dialog that the user may have to acknowledge. `trace_run` waits for it, so tell the user to
watch the IDE.

`trace_save` takes `mode` (`changes`, `samples` for every sample, `csv` for the raw export), a `start_ms`/`end_ms` window,
a `variables` filter and `upload=True` to pull the data from the controller first; `trace_status` shows whether it is
running or has been downloaded. A trace level is a number; leave it out for a BOOL trigger.

`trace_setup` also puts the variables in the trace's first diagram; without that they are recorded
but not drawn. Variable names are relative to the application: no `Application.` prefix. With the prefix the
download silently does nothing. A trace stops itself once its buffer has filled; `trace_save` copes with that. It returns a table of the points where any value
changed (`time_ms` plus one column per variable); sampling follows the task cycle.

### Ladder and other graphical code (PLCopenXML)

`get_pou` and `set_pou` handle text only: the declaration of any POU, and the body of an ST POU.
`create_pou` can make an `ld`/`fbd` POU, but its body cannot be set from text (`set_pou` says so).
Graphical code goes in as PLCopenXML:

The ladder tools use two skills (see [Required skills](#required-skills-ladder-and-hmi-tools)), installed side by
side on the machine that runs the server: **ctrlx-engineer** (`st_to_plcopenxml.py`, the
converter) and **codesys-lad** (the ladder compiler and `ld_trace.py`). The agent passes the source
text to the tool; the server runs the skill's scripts on it. Nothing is copied to the Windows PC.

1. `ladder_check sources={"FB_X.st": "<text>"}` compiles without touching the IDE and returns the
   converter's warnings plus `trace`: every output as a boolean expression, per network. Check it
   against the intent. `sources` maps a `.st` file name to its text (a GVL is named after its
   file); `libs` holds declarations of library POUs the rungs call. A source error raises, with
   the network and the position.
2. Ask the user, then `logout` (the IDE refuses to add objects while logged in; the controller
   keeps running), and `export_plcopen` the objects you are about to replace as a backup.
3. `ladder_import` with the same arguments compiles and imports in one step; nothing is imported
   if the source does not compile. The XML goes through the tunnel as text and the bridge imports
   it from a temp file on the Windows side, so no shared folder is needed. `conflict` is
   `Replace`, `Copy` or `Skip` for objects that already exist; confirm `Replace` with the user.
4. `build`, fix errors, `login` as the user directs.

To review ladder that is already in the project, `ladder_export paths=[...]` returns the same
`trace` for it. `include_xml=True` adds the raw PLCopenXML. `import_plcopen` and `export_plcopen`
move raw XML for anything you built another way.

## How the bridge works (and why)

These were found by trial; they explain the odd structure of `bridge/bridge.py`.

- **UI thread.** `--runscript` runs the script on the IDE's UI thread, and a script that never
  returns freezes the IDE (a message pump in the loop did not help). So the script returns at
  once; a background thread accepts connections and runs each request on the UI thread through a
  hidden WinForms control (`Control.Invoke`). Building or logging in from the background thread
  fails with `An item with the same key has already been added` (compiler).
- **`Stack empty`.** The online module keeps a stack of running scripts and raises `Stack empty`
  when it is empty, which it is once the bridge script has returned. The bridge saves the stack
  entry at startup and pushes it back before online calls.
- **`CTRLX_MCP_BLOCK=1`** serves on the script thread and never returns. Use it only for headless
  `--noUI` runs; the IDE window is frozen while it runs.
- **Long calls** (download, build) block the IDE UI while they run.
- **Stale online object.** The bridge caches one online object per application. After a login or
  logout in the IDE it can go stale: reads fail with `Invalid variable reference` and writes do
  nothing. `read_var` and `write_var` retry once with a fresh object.
- **Imports go where they are called.** `import_xml` on the project puts new objects at the
  project root; on the application it puts them in the application. `import_plcopen` calls it
  on `parent` (default the application). Objects that already exist are matched and replaced
  either way.
- **`build`** is `application.build()`, not a project method. Build messages come from
  `system.get_message_categories(True)`; do not call `system.clear_messages()` (it left the
  Messages pane broken). Compile problems can also surface only at `login`.
- Do not force-kill the IDE after a hung call; close it normally.
- **I/O mapping.** `list_io` shows a card's channels (an input card has `Input` channels, an output card `Output`);
  `map_io` maps, remaps or unmaps them (`variable` null unmaps). The mapping string needs the application name in front,
  `Application.GVL_IO.bDI_Start`; `map_io` adds it. Without it the build reports "Invalid application in mapping".
  Cards live under `Device/Realtime_Data/<master>/<card>`. A mapping change reaches the controller on the next download.
- **Task calls.** The scripting engine has no call to add a program to a task. `add_task_call` exports the
  task (`export_native`), adds an entry to its `PouList` and re-imports it; the IDE asks the user to allow the
  task import. `remove_task_call` removes the child call object directly (no dialog).
- **Non-ASCII text.** IronPython's json encoder fails on a non-ASCII `str` (it tries to UTF-8-decode text that
  is already decoded), which lost the reply and timed out the client. `_jsonable` hands it UTF-8 bytes.

## Example

`examples/intersection/` is a four-way intersection in ladder (fixed-time NS/EW cycle, fault input
with flashing red, reset), written to test the ladder tools. Build and simulate it with the
ladder skills (`st_to_plcopenxml.py`, then `test_intersection.py`), import it with `ladder_import`,
then `add_task_call` for `PRG_Intersection` so a task runs it.

`examples/intersection/hmi/` holds the screen definition for it (`screen_intersection.py`) and the preview scenarios.
Build and publish it with `build_hmi` / `publish_hmi`; that needs the ctrlx-hmi skill with its templates, which each
user makes once from their own PLC Engineering (see the skill's README, "First run"). No generated `.export` is
shipped.

## Tests

    .venv/bin/python tests/test_protocol.py     # bridge protocol, stubbed scriptengine
    .venv/bin/python tests/test_mcp_e2e.py      # MCP server against a stubbed bridge

These do not run against a real IDE. What has been run for real: ping, tree, POU read/write,
save_project, build, login with download, logout, run_state, plc_start, read_var, write_var, and
the trace flow above, and PLCopenXML export/import (`export_xml`, and `import_xml` with text written
to a temp file) including a ladder block, driven through `exec_script`. Not exercised yet: the
`export_plcopen`, `import_plcopen` and `ladder_*` tools end to end, `create_pou`/`create_dut`/`create_gvl`/`delete_object`, `create_folder`/`move_object` against the stubs only (the same scripting calls, `create_folder` and `move`, were run for real through `exec_script`),
`plc_stop`, trigger-based traces, and starting the bridge with `--runscript` at IDE startup
(`AUTORUN=1`; the menu route is what has been tested).

## License

MIT, see [LICENSE](LICENSE). Parts of this software were generated and tested with Claude Opus 5.5 and
Claude Sonnet 5.5, see [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md).

## HMI import

A visualization export from the ctrlx-hmi skill carries the whole device tree, and an open project refuses it
("cannot be pasted here"). The server sends the export to the bridge as text (`visu_import`), so it works the same
from Linux over the tunnel. The bridge, on the machine with the IDE, starts a second, headless IDE (`--noUI`, its
windows hidden) as a helper on `CTRLX_HELPER_PORT` (default 8766), imports the export into a temp project there,
exports only the Visualization Manager, text lists and visus as object files (`visu_extract`), stops the helper and
imports the files into the open project (`visu_apply`). Same-named objects are replaced; an existing Visualization
Manager is kept. `add_web_visu` copies a Web Visualization that is already in the project (`from_web_visu`, or
the first one) and sets the name, start visu and client size (1920x1080 by default); a project needs one added in
the IDE once (right-click the Visualization Manager > Add Object > Web Visualization). The scripting engine has no call to
create visualizations. The helper's log is `%TEMP%\ctrlx_bridge_<port>.log`; `start_bridge.bat` also takes
`BRIDGE_PORT`, `BRIDGE_PROJECT` and `BRIDGE_HEADLESS=1` for a second instance by hand. `build_hmi` and
`publish_hmi` run the skill's generator on the machine running the server, which needs the ctrlx-hmi skill there
(`CTRLX_SKILLS_DIR`).

## Auto-start

On Windows, when the bridge is on this PC and a tool call finds nothing listening, the server runs
`scripts\start_bridge.bat` itself (IDE plus bridge, and the project from `config.bat`) and waits up to three
minutes for it, so the first call after boot takes about a minute. It tries once per five minutes.
`CTRLX_AUTOSTART=0` turns it off.

Over the SSH tunnel (Linux client) the server cannot start the IDE, so start `scripts\start_bridge.bat` on the
Windows machine first; everything else, including the HMI tools, works the same.
