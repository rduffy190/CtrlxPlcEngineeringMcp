"""MCP server for ctrlX PLC Engineering. Proxies tool calls to bridge/bridge.py.

Env: CTRLX_BRIDGE_HOST (127.0.0.1), CTRLX_BRIDGE_PORT (8765), CTRLX_MCP_TOKEN (required).
"""
import csv
import io
import json
import re
import os
import socket
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

HOST = os.environ.get("CTRLX_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("CTRLX_BRIDGE_PORT", "8765"))
TOKEN = os.environ.get("CTRLX_MCP_TOKEN", "")

mcp = FastMCP("ctrlx-engineering")


class BridgeError(RuntimeError):
    pass


def call(cmd: str, timeout: float = 60, **args: Any) -> Any:
    """One request/response round trip to the bridge."""
    req = json.dumps({"id": 1, "token": TOKEN, "cmd": cmd, "args": args}).encode() + b"\n"
    try:
        with socket.create_connection((HOST, PORT), timeout=10) as s:
            s.sendall(req)
            s.settimeout(timeout)
            buf = b""
            while not buf.endswith(b"\n"):
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
    except OSError as e:
        raise BridgeError(f"bridge unreachable at {HOST}:{PORT}: {e}") from e
    resp = json.loads(buf)
    if not resp.get("ok"):
        raise BridgeError(resp.get("error", "unknown error") + "\n" + resp.get("traceback", ""))
    return resp.get("result")


def parse_csv(text: str, max_rows: int) -> dict:
    """Parse a ctrlX trace export: a key;value header, then per variable `N.Variable; name` and
    `N.Data;` followed by `; time_ms; value` rows. Returns the series merged into a change table."""
    names: dict[int, str] = {}
    series: dict[int, dict[int, str]] = {}
    cur = None
    meta: dict[str, str] = {}
    for line in text.lstrip("\ufeff").splitlines():
        m = re.match(r"(\d+)\.Variable;\s*(.+)", line)
        if m:
            names[int(m.group(1))] = m.group(2).strip()
            continue
        m = re.match(r"(\d+)\.Data;", line)
        if m:
            cur = int(m.group(1))
            series[cur] = {}
            continue
        parts = [p.strip() for p in line.split(";")]
        if cur is not None and line.startswith(";") and len(parts) >= 3 and parts[1].lstrip("-").isdigit():
            series[cur][int(parts[1])] = parts[2]
        elif cur is None and len(parts) == 2 and parts[0] in ("Name", "IecTaskName", "EveryNCycles"):
            meta[parts[0]] = parts[1]
    ids = sorted(series)
    times = sorted({t for k in ids for t in series[k]})
    rows, prev = [], None
    for t in times:
        row = [series[k].get(t, prev[i] if prev else "") for i, k in enumerate(ids)]
        if row != prev:
            rows.append([t] + row)
        prev = row
    return {"meta": meta, "columns": ["time_ms"] + [names.get(k, str(k)) for k in ids],
            "samples": len(times), "changes": rows[:max_rows], "truncated": len(rows) > max_rows}


# ---- project

@mcp.tool()
def ping() -> Any:
    """Check the bridge is reachable; returns the open project path."""
    return call("ping")


@mcp.tool()
def open_project(path: str) -> Any:
    """Open a .project file in PLC Engineering."""
    return call("open_project", timeout=300, path=path)


@mcp.tool()
def save_project() -> Any:
    """Save the open project."""
    return call("save_project")


@mcp.tool()
def get_tree(path: str = "", depth: int = 3) -> Any:
    """List the project tree. Paths are '/'-separated names, e.g. 'Device/PLC Logic/Application'."""
    return call("get_tree", path=path, depth=depth)


@mcp.tool()
def get_pou(path: str) -> Any:
    """Read declaration and implementation text of a POU/GVL/DUT."""
    return call("get_pou", path=path)


@mcp.tool()
def set_pou(path: str, declaration: Optional[str] = None, implementation: Optional[str] = None) -> Any:
    """Replace declaration and/or implementation text of an existing object."""
    return call("set_pou", path=path, declaration=declaration, implementation=implementation)


@mcp.tool()
def create_pou(parent: str, name: str, kind: str = "Program", language: str = "st") -> Any:
    """Create a POU under parent. kind: Program|FunctionBlock|Function. language: st|ld|fbd..."""
    return call("create_pou", parent=parent, name=name, kind=kind, language=language)


@mcp.tool()
def create_dut(parent: str, name: str) -> Any:
    """Create a DUT under parent."""
    return call("create_dut", parent=parent, name=name)


@mcp.tool()
def create_gvl(parent: str, name: str) -> Any:
    """Create a global variable list under parent."""
    return call("create_gvl", parent=parent, name=name)


@mcp.tool()
def delete_object(path: str) -> Any:
    """Delete a project object. Irreversible until the project is reloaded without saving."""
    return call("delete", path=path)


@mcp.tool()
def build(app: Optional[str] = None) -> Any:
    """Build application `app` (default: the active one) and return error count plus messages."""
    return call("build", timeout=600, **({"app": app} if app else {}))


@mcp.tool()
def messages() -> Any:
    """Return the current message store (build/compile messages)."""
    return call("messages")


# ---- online

@mcp.tool()
def login(app: str, download: bool = False, change: str = "Try") -> Any:
    """Log in to the application at path `app`. ALWAYS ask the user how to download before calling; a
    download can stop the application and reset its variables.

    `change` is the IDE's online-change option: Try (online change, the default), Force, Keep or
    Never. Never STOPS a running controller when logging in; use Try to attach to a running
    application. `download` is passed to the IDE as "delete foreign applications" on the controller
    (needs extra rights); leave it False unless the user asks."""
    return call("login", timeout=300, app=app, download=download, change=change)


@mcp.tool()
def logout(app: str) -> Any:
    """Log out of the application."""
    return call("logout", app=app)


@mcp.tool()
def run_state(app: str) -> Any:
    """Application run state and login status."""
    return call("run_state", app=app)


@mcp.tool()
def plc_start(app: str) -> Any:
    """Start the application on the controller."""
    return call("plc_start", app=app)


@mcp.tool()
def plc_stop(app: str) -> Any:
    """Stop the application on the controller."""
    return call("plc_stop", app=app)


@mcp.tool()
def read_var(app: str, names: list[str]) -> Any:
    """Read online variables, e.g. ['PLC_PRG.counter']."""
    return call("read_var", app=app, names=names)


@mcp.tool()
def write_var(app: str, values: dict[str, Any]) -> Any:
    """Write online variables (name -> value). Affects a running machine; confirm first."""
    return call("write_var", app=app, values=values)


# ---- trace

@mcp.tool()
def trace_setup(trace: str, samples: int, variables: Optional[list[str]] = None, every_n_cycles: Optional[int] = None,
                resolution: Optional[str] = None, trigger_variable: Optional[str] = None,
                trigger_edge: str = "Positive", trigger_level: Optional[float] = None) -> Any:
    """Configure an existing trace object (add it in the IDE first: Add Object > Trace; scripts cannot
    create one). ALWAYS ask the user how many `samples` the trace should use before calling; never
    pick a number yourself. Variables are relative to the application, e.g. 'PRG_Main.bEnable'."""
    return call("trace_setup", trace=trace, variables=variables, every_n_cycles=every_n_cycles,
                resolution=resolution, trigger_variable=trigger_variable, trigger_edge=trigger_edge,
                trigger_level=trigger_level, samples=samples)


@mcp.tool()
def trace_run(app: str, trace: str, download: bool = True) -> Any:
    """Start the trace at path `trace` (logs in without download if needed). With download=True the
    trace is downloaded first; the IDE may ask the user to acknowledge that in a dialog, so tell the
    user and wait. With download=False the trace already on the controller is re-armed and started
    again (use it for repeat runs when its variables and settings have not changed)."""
    return call("trace_run", timeout=600, app=app, trace=trace, download=download)


@mcp.tool()
def trace_stop(trace: str) -> Any:
    """Stop the trace if it is still running (it stops itself when its buffer is full)."""
    return call("trace_stop", trace=trace)


@mcp.tool()
def trace_wait(trace: str, timeout_s: float = 30) -> Any:
    """Wait for the trigger. Returns {triggered, state}."""
    return call("trace_wait", timeout=timeout_s + 30, trace=trace, timeout_s=timeout_s)


@mcp.tool()
def trace_save(trace: str, max_rows: int = 500) -> Any:
    """Stop the trace, export CSV and return value changes per variable (time_ms plus one column each)."""
    res = call("trace_save", timeout=120, trace=trace)
    return parse_csv(res["csv"], max_rows)


# ---- escape hatch

@mcp.tool()
def exec_script(code: str) -> Any:
    """Run IronPython in the scripting engine. Assign to `result` to return a value.
    Use for introspection (dir(obj)) or anything without a dedicated tool."""
    return call("exec", timeout=300, code=code)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("CTRLX_MCP_TOKEN must be set")
    mcp.run()
