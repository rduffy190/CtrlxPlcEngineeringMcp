# ctrlX Engineering MCP

An MCP server that lets Claude Code drive ctrlX PLC Engineering (CODESYS V3) through the
CODESYS Scripting Engine: read and write POUs, build, go online, start/stop, read and write
variables, and record traces.

```
Claude Code --stdio--> server/server.py (CPython, FastMCP)
                          | JSON lines over TCP + token (SSH reverse tunnel)
                          v
   PLC Engineering (Windows) running bridge/bridge.py (IronPython 2.7, inside the IDE)
```

Tested with ctrlX PLC Engineering 4.6.2 (ScriptEngine 4.2.0.0) against a ctrlX CORE.

## Setup

**Linux / WSL (where Claude Code runs)**

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    scripts/install_token.sh          # creates .ctrlx_token, exports CTRLX_MCP_TOKEN from ~/.bashrc

`.mcp.json` registers the server for Claude Code in this folder. The token is read from the
environment, so open a new terminal after installing it.

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

Check it from Linux: ask Claude to `ping`, or run

    CTRLX_MCP_TOKEN=$(cat .ctrlx_token) .venv/bin/python -c "import sys; sys.path.insert(0,'server'); import server; print(server.call('ping'))"

If the IDE misbehaves when the script loads at startup, set `AUTORUN=0` in `config.bat` and run
the bridge from Tools > Scripting > Execute Script File. Its log is `%TEMP%\ctrlx_bridge.log`
(`online context saved` and `ui dispatch ready` should appear, then `loop started`).

## Tools

Project: `ping`, `open_project`, `save_project`, `get_tree`, `get_pou`, `set_pou`, `create_pou`,
`create_dut`, `create_gvl`, `delete_object`, `build`, `messages`.
PLCopenXML: `export_plcopen`, `import_plcopen`. Ladder: `ladder_check`, `ladder_import`, `ladder_export`.
Online: `login`, `logout`, `run_state`, `plc_start`, `plc_stop`, `read_var`, `write_var`.
Trace: `trace_setup`, `trace_run`, `trace_stop`, `trace_wait`, `trace_save`.
Escape hatch: `exec_script` (runs IronPython in the IDE; use `dir()` to explore the API).

Object paths are `/`-separated names from the project root, for example
`Device/Plc Logic/Application/PRG_Main`. Name matching is exact; check `get_tree` for the
spelling (`Plc Logic` vs `PLC Logic`).

## Rules for Claude

- **Always ask the user how to download the application** before `login`. An application download
  can replace the program, reset variables to their initial values and stop a running application.
  (A *trace* download is a different thing, see Tracing.) Do not decide it, and do
  not log in "just to look" at a running machine.
- **`change="Never"` stops a running controller when you log in** (seen on a ctrlX CORE). The default
  is `Try` (online change), which keeps it running; it is also what `trace_run` uses.
- To attach to a running PLC use `login` with `change="Try"`. The `download` flag is
  passed to the IDE as "delete foreign applications" on the controller, needs extra rights (a
  permissions error otherwise) and defaults to False; leave it off unless the user asks.
- **Always ask the user how many samples the trace should use** before `trace_setup`; `samples` is
  required and is not defaulted.
- `write_var`, `plc_start`, `plc_stop` and `login` affect a running machine; confirm first.

### Tracing

Scripts cannot create a trace object (`trace.create` returns a stub and adds nothing). Add one
once in the IDE: right-click the Application > Add Object > Trace. After that:

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

`trace_setup` also puts the variables in the trace's first diagram; without that they are recorded
but not drawn. Variable names are relative to the application: no `Application.` prefix. With the prefix the
download silently does nothing. A trace stops itself once its buffer has filled; `trace_save` copes with that. It returns a table of the points where any value
changed (`time_ms` plus one column per variable); sampling follows the task cycle.

### Ladder and other graphical code (PLCopenXML)

`get_pou` and `set_pou` handle text only: the declaration of any POU, and the body of an ST POU.
`create_pou` can make an `ld`/`fbd` POU, but its body cannot be set from text (`set_pou` says so).
Graphical code goes in as PLCopenXML:

The ladder tools use two Claude Code skills on the Linux side, installed side by side in
`~/.claude/skills` (or set `CTRLX_SKILLS_DIR`): **ctrlx-engineer** (`st_to_plcopenxml.py`, the
converter) and **codesys-lad** (the ladder compiler and `ld_trace.py`). Claude passes the source
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

## Tests

    .venv/bin/python tests/test_protocol.py     # bridge protocol, stubbed scriptengine
    .venv/bin/python tests/test_mcp_e2e.py      # MCP server against a stubbed bridge

These do not run against a real IDE. What has been run for real: ping, tree, POU read/write,
save_project, build, login with download, logout, run_state, plc_start, read_var, write_var, and
the trace flow above, and PLCopenXML export/import (`export_xml`, and `import_xml` with text written
to a temp file) including a ladder block, driven through `exec_script`. Not exercised yet: the
`export_plcopen`, `import_plcopen` and `ladder_*` tools end to end, `create_pou`/`create_dut`/`create_gvl`/`delete_object`,
`plc_stop`, trigger-based traces, and starting the bridge with `--runscript` at IDE startup
(`AUTORUN=1`; the menu route is what has been tested).

## License

MIT, see [LICENSE](LICENSE).
