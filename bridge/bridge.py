# -*- coding: utf-8 -*-
"""ctrlX PLC Engineering scripting bridge (IronPython 2.7).

Start it with the IDE (scripts/start_bridge.bat does this):
    "<ctrlX PLC Engineering>.exe" --runscript="C:\\path\\to\\bridge.py"
or from a running IDE: Tools > Scripting > Execute Script File.
Needs CTRLX_MCP_TOKEN in the environment. CTRLX_MCP_PROJECT (optional) is opened at startup.

Serves newline-delimited JSON over TCP on 127.0.0.1 (CTRLX_MCP_PORT, default 8765).
Request : {"id": 1, "token": "...", "cmd": "get_pou", "args": {...}}
Response: {"id": 1, "ok": true, "result": ...} | {"ok": false, "error": "...", "traceback": "..."}

How it runs (all of this was found by trial on ctrlX PLC Engineering 4.6, ScriptEngine 4.2):
* The script returns at once, so the IDE stays usable. Requests are accepted on a background
  thread and each one is run on the IDE's UI thread (a hidden WinForms control created at
  startup, Control.Invoke), one at a time. Compiling or logging in from the background
  thread fails with "An item with the same key has already been added".
* The online module raises "Stack empty" unless a script is executing. The execution entry is
  saved at startup and pushed back before each online call (_save_online_ctx).
* A long call (download, build) blocks the UI for its duration.
* CTRLX_MCP_BLOCK=1 serves on the script thread instead and never returns (headless --noUI).
* trace.create() does not work: the trace object is added in the IDE (Add Object > Trace) and
  configured here. Trace variable names are relative to the application (no "Application.").

Keep it py2/py3 compatible so the protocol can be tested outside the IDE with stubbed
scriptengine globals. The scriptengine names used (projects, online, system, trace,
OnlineChangeOption, TriggerState, TriggerEdge, PouType, ImplementationLanguages, Resolution)
are injected into the script scope by the IDE.
"""
import json
import os
import select
import socket
import sys
import tempfile
import threading
import time
import traceback

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

HOST = os.environ.get("CTRLX_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("CTRLX_MCP_PORT", "8765"))
TOKEN = os.environ.get("CTRLX_MCP_TOKEN", "")
ALLOW_EXEC = os.environ.get("CTRLX_MCP_ALLOW_EXEC", "1") == "1"
PROJECT = os.environ.get("CTRLX_MCP_PROJECT", "")
# 1 = serve on the script thread and never return (headless --noUI, where returning ends the process)
BLOCK = os.environ.get("CTRLX_MCP_BLOCK", "0") == "1"
UI = os.environ.get("CTRLX_MCP_UI", "1") == "1"   # run each request on the IDE UI thread
LOG = os.path.join(os.environ.get("TEMP", tempfile.gettempdir()), "ctrlx_bridge.log")
MAX_REQUEST = 16 * 1024 * 1024

# Live objects that must outlive a single request.
_online_apps = {}   # app path -> online application
_editors = {}       # trace path -> trace editor


# ---------------------------------------------------------------- helpers

def _log(msg):
    """Append to a log file; open/close each time so a crash keeps the last line."""
    try:
        f = open(LOG, "a")
        try:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
        finally:
            f.close()
    except Exception:
        pass


_ui_ctrl = None   # hidden WinForms control created on the UI thread


def _init_ui():
    """Create a control on the thread running this script (the IDE's UI thread) so the
    background loop can hand requests to it with Invoke."""
    global _ui_ctrl
    if not UI:
        return
    try:
        import clr
        clr.AddReference("System.Windows.Forms")
        from System.Windows.Forms import Control
        c = Control()
        c.Handle                      # forces the handle onto this thread
        _ui_ctrl = c
        _log("ui dispatch ready")
    except Exception as e:
        _log("ui dispatch unavailable: %r" % (e,))


def _run_on_ui(fn):
    """Run fn on the UI thread and return its result; fn itself must not raise."""
    if _ui_ctrl is None:
        return fn()
    from System import Func
    return _ui_ctrl.Invoke(Func[object](fn))


def _proj():
    p = projects.primary
    if p is None:
        raise RuntimeError("no project open")
    return p


def _find(path):
    """Resolve 'Device/PLC Logic/Application/GVL' by walking children by name."""
    node = _proj()
    for part in [p for p in path.split("/") if p]:
        for child in node.get_children(False):
            if child.get_name() == part:
                node = child
                break
        else:
            raise ValueError("'%s' not found under '%s'" % (part, node.get_name()))
    return node


def _enum(enum_cls, name):
    try:
        return getattr(enum_cls, name)
    except AttributeError:
        raise ValueError("unknown %s '%s'" % (getattr(enum_cls, "__name__", enum_cls), name))


def _tree(node, depth):
    out = []
    for c in node.get_children(False):
        item = {"name": c.get_name(),
                "text": bool(getattr(c, "has_textual_declaration", False))}
        if depth > 1:
            item["children"] = _tree(c, depth - 1)
        out.append(item)
    return out


def _messages():
    """Collect build messages. Defensive: the message API differs between versions."""
    out = []
    try:
        cats = [c for c in system.get_message_categories(True) if c is not None]
    except Exception:
        cats = []
    for cat in cats:
        try:
            for m in system.get_message_objects(cat):
                out.append({"severity": str(getattr(m, "severity", "")),
                            "text": str(getattr(m, "text", m))})
        except Exception as e:
            out.append({"severity": "bridge", "text": "message read failed: %s" % e})
    return out


_online_ctx = None   # (stack, entry) of the online module's execution stack, saved at startup


def _save_online_ctx():
    """The online module keeps a stack of running scripts and raises 'Stack empty' when it is
    empty. It is only filled while a script is executing; in background mode that script
    returns at once. Remember the entry now so _ensure_online_ctx can put it back."""
    global _online_ctx
    try:
        import clr
        from System.Reflection import BindingFlags
        f = online.GetType().GetField("_executionStack",
                                      BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public)
        st = f.GetValue(online)
        if st.Count:
            _online_ctx = (st, st.Peek())
            _log("online context saved")
        else:
            _log("online context: stack empty at startup")
    except Exception as e:
        _log("online context not saved: %r" % (e,))


def _ensure_online_ctx():
    if _online_ctx is not None and _online_ctx[0].Count == 0:
        _online_ctx[0].Push(_online_ctx[1])
        _log("online context restored")


def _online(app_path):
    _ensure_online_ctx()
    app = _find(app_path)
    oa = _online_apps.get(app_path)
    if oa is None:
        oa = online.create_online_application(app)
        _online_apps[app_path] = oa
    return oa


# --------------------------------------------------------------- handlers

def h_ping(a):
    return {"bridge": "ctrlx-mcp", "python": sys.version,
            "project": (projects.primary.path if projects.primary else None)}


def h_exec(a):
    """Run arbitrary scripting code. Assign to `result` to return a value."""
    if not ALLOW_EXEC:
        raise RuntimeError("exec disabled (CTRLX_MCP_ALLOW_EXEC=0)")
    env = dict(globals())
    env["result"] = None
    buf, old = StringIO(), sys.stdout
    sys.stdout = buf
    try:
        exec(a["code"], env)
    finally:
        sys.stdout = old
    return {"stdout": buf.getvalue(), "result": env["result"]}


def h_open_project(a):
    p = projects.open(a["path"])
    return {"path": p.path}


def h_save_project(a):
    _proj().save()
    return True


def h_close_project(a):
    _online_apps.clear()
    _editors.clear()
    _proj().close()
    return True


def h_get_tree(a):
    root = _find(a["path"]) if a.get("path") else _proj()
    return _tree(root, int(a.get("depth", 3)))


def h_get_pou(a):
    n = _find(a["path"])
    r = {"declaration": n.textual_declaration.text}
    if getattr(n, "has_textual_implementation", False):
        r["implementation"] = n.textual_implementation.text
    return r


def h_set_pou(a):
    n = _find(a["path"])
    if a.get("declaration") is not None:
        n.textual_declaration.replace(a["declaration"])
    if a.get("implementation") is not None:
        n.textual_implementation.replace(a["implementation"])
    return True


def h_create_pou(a):
    parent = _find(a["parent"])
    kind = _enum(PouType, a.get("kind", "Program"))
    lang = _enum(ImplementationLanguages, a.get("language", "st"))
    n = parent.create_pou(a["name"], kind, lang)
    return {"name": n.get_name()}


def h_create_dut(a):
    n = _find(a["parent"]).create_dut(a["name"])
    return {"name": n.get_name()}


def h_create_gvl(a):
    n = _find(a["parent"]).create_gvl(a["name"])
    return {"name": n.get_name()}


def h_delete(a):
    _find(a["path"]).remove()
    return True


def h_build(a):
    # build() lives on the application object, not the project
    if a.get("app"):
        app = _find(a["app"])
        projects.primary.active_application = app
    else:
        app = projects.primary.active_application
        if app is None:
            raise ValueError("no active application; pass app")
    app.build()
    msgs = _messages()
    errors = [m for m in msgs if "error" in m["severity"].lower()]
    return {"errors": len(errors), "messages": msgs}


def h_messages(a):
    return _messages()


# ---- online

def h_login(a):
    oa = _online(a["app"])
    oa.login(_enum(OnlineChangeOption, a.get("change", "Never")), bool(a.get("download", True)))
    return True


def h_logout(a):
    oa = _online_apps.pop(a["app"], None)
    if oa is not None:
        oa.logout()
    return True


def h_run_state(a):
    oa = _online(a["app"])
    return {"state": str(oa.application_state), "logged_in": bool(oa.is_logged_in)}


def h_plc_start(a):
    _online(a["app"]).start()
    return True


def h_plc_stop(a):
    _online(a["app"]).stop()
    return True


def h_read_var(a):
    oa = _online(a["app"])
    return {n: str(oa.read_value(n)) for n in a["names"]}


def h_write_var(a):
    oa = _online(a["app"])
    for n, v in a["values"].items():
        oa.set_prepared_value(n, str(v))
    oa.write_prepared_values()
    return True


# ---- trace

def h_trace_setup(a):
    """Configure an existing trace object. Trace.create does not work in this ScriptEngine, so the
    trace is added in the IDE (Add Object > Trace). Variable names are relative to the
    application (no 'Application.' prefix; with it the download silently does nothing)."""
    t = _find(a["trace"])
    if not hasattr(t, "variable_list"):
        raise ValueError("'%s' is not a trace object; add one in the IDE (Add Object > Trace)" % a["trace"])
    if a.get("variables") is not None:
        t.variable_list.clear()
        for v in a["variables"]:
            if v.startswith("Application."):
                v = v[len("Application."):]
            t.add_trace_variable(v)
    if a.get("every_n_cycles"):
        t.every_n_cycles = int(a["every_n_cycles"])
    if a.get("resolution"):
        t.resolution = _enum(Resolution, a["resolution"])
    if a.get("trigger_variable"):
        t.trigger_enabled = True
        t.trigger_variable = a["trigger_variable"]
        t.trigger_edge = _enum(TriggerEdge, a.get("trigger_edge", "Positive"))
        if a.get("trigger_level") is not None:
            t.trigger_level = str(a["trigger_level"])
        t.post_trigger_samples = int(a.get("post_trigger_samples", 100))
    return {"trace": a["trace"], "variables": [str(v.variable_name) for v in t.variable_list]}


def h_trace_run(a):
    """Log in if needed (no download), then download and start the trace."""
    oa = _online(a["app"])
    if not oa.is_logged_in:
        oa.login(OnlineChangeOption.Never, False)
    ed = _find(a["trace"]).open_editor()
    ed.download()
    ed.start()
    _editors[a["trace"]] = ed
    deadline = time.time() + 5
    while not ed.is_running and time.time() < deadline:
        system.delay(100)
    if not ed.is_running:
        raise RuntimeError("trace did not start (editor logged in: %s)" % ed.is_logged_in)
    return True


def _editor(path):
    ed = _editors.get(path)
    if ed is None:
        raise RuntimeError("trace '%s' not running; call trace_run first" % path)
    return ed


def h_trace_state(a):
    return str(_editor(a["trace"]).get_trigger_state())


def h_trace_wait(a):
    """Poll for the trigger. Returns {'triggered': bool, 'state': str}."""
    ed = _editor(a["trace"])
    deadline = time.time() + float(a.get("timeout_s", 30))
    while True:
        st = ed.get_trigger_state()
        if st == TriggerState.TriggerReached:
            return {"triggered": True, "state": str(st)}
        if time.time() >= deadline:
            return {"triggered": False, "state": str(st)}
        system.delay(200)


def h_trace_save(a):
    """Stop the trace, export CSV and return its text."""
    ed = _editor(a["trace"])
    ed.stop()
    path = a.get("csv_path")
    tmp = None
    if not path:
        fd, tmp = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        path = tmp
    ed.save(path)
    with open(path, "rb") as f:
        raw = f.read()
    if tmp:
        os.remove(tmp)
    return {"path": None if tmp else path,
            "csv": raw.decode("utf-8", "replace")}


HANDLERS = dict(
    (k[2:], v) for k, v in list(globals().items())
    if k.startswith("h_") and callable(v))


# ------------------------------------------------------------------ server

def dispatch(req):
    rid = req.get("id")
    if not TOKEN or req.get("token") != TOKEN:
        return {"id": rid, "ok": False, "error": "unauthorized"}
    fn = HANDLERS.get(req.get("cmd"))
    if fn is None:
        return {"id": rid, "ok": False, "error": "unknown cmd '%s'" % req.get("cmd")}
    try:
        return {"id": rid, "ok": True, "result": fn(req.get("args") or {})}
    except Exception as e:
        return {"id": rid, "ok": False, "error": "%s: %s" % (type(e).__name__, e),
                "traceback": traceback.format_exc()}


def _read_line(conn):
    buf = b""
    while b"\n" not in buf:
        chunk = conn.recv(65536)
        if not chunk:
            break
        buf += chunk
        if len(buf) > MAX_REQUEST:
            raise ValueError("request too large")
    return buf.split(b"\n", 1)[0]


def serve():
    if not TOKEN:
        raise SystemExit("CTRLX_MCP_TOKEN must be set")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # On Windows SO_REUSEADDR lets a second copy bind the same port silently; refuse instead.
    srv.setsockopt(socket.SOL_SOCKET,
                   getattr(socket, "SO_EXCLUSIVEADDRUSE", socket.SO_REUSEADDR), 1)
    try:
        srv.bind((HOST, PORT))
    except socket.error as e:
        raise SystemExit("cannot listen on %s:%d (bridge already running?): %s" % (HOST, PORT, e))
    srv.listen(5)
    srv.settimeout(1.0)  # wake regularly so the IDE can abort the script
    _save_online_ctx()
    if not BLOCK:
        _init_ui()
    if PROJECT and projects.primary is None:
        try:
            projects.open(PROJECT)
            _log("opened project %s" % PROJECT)
        except Exception as e:
            _log("could not open project %s: %r" % (PROJECT, e))
    print("ctrlx-mcp bridge listening on %s:%d" % (HOST, PORT))
    if BLOCK:
        _loop(srv)
    else:
        # --runscript / Execute Script File run on the IDE's UI thread: a script that never
        # returns freezes the IDE. Accept on a background thread and return.
        try:
            # a .NET worker thread starts with a small stack; exceptions in IronPython
            # are stack hungry and overflow it ("new guard page could not be created")
            threading.stack_size(64 * 1024 * 1024)
        except Exception as e:
            _log("stack_size failed: %r" % (e,))
        t = threading.Thread(target=_loop, args=(srv,))
        t.daemon = True
        t.start()
        print("ctrlx-mcp bridge running in background thread (log: %s)" % LOG)


def _loop(srv):
    _log("loop started")
    while True:
        # select instead of catching socket.timeout every second: no exceptions when idle
        try:
            ready = select.select([srv], [], [], 1.0)[0]
        except Exception as e:
            _log("select failed: %r" % (e,))
            time.sleep(1)
            continue
        if not ready:
            continue
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue
        _log("connection")
        try:
            conn.settimeout(10)
            line = _read_line(conn)
            if line:
                try:
                    req = json.loads(line.decode("utf-8"))
                    resp = _run_on_ui(lambda: dispatch(req))
                except ValueError as e:
                    resp = {"ok": False, "error": "bad request: %s" % e}
                except Exception as e:
                    _log(traceback.format_exc())
                    resp = {"ok": False, "error": "bridge: %s: %s" % (type(e).__name__, e)}
                conn.settimeout(None)
                conn.sendall(json.dumps(resp, default=str).encode("utf-8") + b"\n")
        except Exception:
            _log(traceback.format_exc())
            traceback.print_exc()
        finally:
            conn.close()


if __name__ == "__main__":
    serve()
