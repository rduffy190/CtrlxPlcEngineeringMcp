"""End-to-end test: MCP client --stdio--> server/server.py --TCP--> bridge (stubbed IDE).

Run: .venv/bin/python tests/test_mcp_e2e.py
"""
import asyncio
import builtins
import json
import os
import sys
import threading
import time
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bridge"))
sys.path.insert(0, os.path.join(ROOT, "server"))
PORT = "18766"
TOKEN = "e2e-token"
os.environ.update(CTRLX_MCP_TOKEN=TOKEN, CTRLX_MCP_PORT=PORT)

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402


class Node:
    def __init__(self, name, children=(), text=True):
        self._name, self._children = name, list(children)
        self.has_textual_declaration = text
        self.has_textual_implementation = text
        self.textual_declaration = types.SimpleNamespace(text="decl", replace=self._set_d)
        self.textual_implementation = types.SimpleNamespace(text="impl", replace=self._set_i)
        self.parent = None

    def _set_d(self, t):
        self.textual_declaration.text = t

    def _set_i(self, t):
        self.textual_implementation.text = t

    def get_name(self):
        return self._name

    def get_children(self, recursive):
        return self._children

    def add(self, child):
        child.parent = self
        self._children.append(child)
        return child

    def create_pou(self, name, kind, lang):
        return self.add(Node(name))

    def create_dut(self, name):
        return self.add(Node(name))

    def create_gvl(self, name):
        return self.add(Node(name))

    def remove(self):
        self.parent._children.remove(self)


class Online:
    application_state = "Run"
    is_logged_in = True

    def read_value(self, n):
        return 42


app = Node("Application", text=False)
app.add(Node("PLC_PRG"))
proj = Node("proj", text=False)
proj.add(Node("Device", text=False)).add(Node("PLC Logic", text=False)).add(app)
proj.path = "/x.project"
proj.save = lambda: None
built = []
app.build = lambda: built.append(1)   # build() is on the application, not the project
proj.active_application = None
msg = types.SimpleNamespace(severity="Error", text="C0032: type mismatch")
sysstub = types.SimpleNamespace(get_message_categories=lambda _: ["c"],
                                get_message_objects=lambda c: [msg])
for k, v in dict(projects=types.SimpleNamespace(primary=proj),
                 online=types.SimpleNamespace(create_online_application=lambda a: Online()),
                 system=sysstub, trace=None,
                 PouType=types.SimpleNamespace(Program="Program", FunctionBlock="FB"),
                 ImplementationLanguages=types.SimpleNamespace(st="st")).items():
    setattr(builtins, k, v)

import bridge  # noqa: E402

APP = "Device/PLC Logic/Application"


def data(res):
    assert not res.isError, res.content
    text = "".join(c.text for c in res.content)
    try:
        return json.loads(text)
    except ValueError:
        return text


async def run():
    params = StdioServerParameters(
        command=sys.executable, args=[os.path.join(ROOT, "server", "server.py")],
        env={**os.environ, "CTRLX_BRIDGE_PORT": PORT})
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = {t.name for t in (await s.list_tools()).tools}
        expected = {"ping", "open_project", "save_project", "get_tree", "get_pou", "set_pou",
                    "create_pou", "create_dut", "create_gvl", "delete_object", "build",
                    "messages", "login", "logout", "run_state", "plc_start", "plc_stop",
                    "read_var", "write_var", "trace_setup", "trace_run", "trace_wait",
                    "trace_save", "exec_script"}
        assert expected <= tools, f"missing tools: {expected - tools}"

        async def tool(tool_name, /, **a):
            return await s.call_tool(tool_name, a)

        assert data(await tool("ping"))["project"] == "/x.project"
        tree = data(await tool("get_tree", path=APP, depth=1))
        assert any(n["name"] == "PLC_PRG" for n in (tree if isinstance(tree, list) else [tree]))

        await tool("set_pou", path=f"{APP}/PLC_PRG", declaration="PROGRAM PLC_PRG", implementation="x := 1;")
        pou = data(await tool("get_pou", path=f"{APP}/PLC_PRG"))
        assert pou["declaration"] == "PROGRAM PLC_PRG" and pou["implementation"] == "x := 1;"

        await tool("create_pou", parent=APP, name="Motor", kind="FunctionBlock")
        await tool("create_gvl", parent=APP, name="GVL")
        await tool("create_dut", parent=APP, name="ST_Axis")
        await tool("delete_object", path=f"{APP}/GVL")
        names = [c.get_name() for c in app.get_children(False)]
        assert names == ["PLC_PRG", "Motor", "ST_Axis"], names

        b = data(await tool("build", app=APP))
        assert b["errors"] == 1 and "type mismatch" in b["messages"][0]["text"]
        assert built == [1] and proj.active_application is app
        assert data(await tool("read_var", app=APP, names=["PLC_PRG.n"])) == {"PLC_PRG.n": "42"}
        assert data(await tool("exec_script", code="result = 6 * 7"))["result"] == 42

        # error paths must surface as tool errors, not crash the server
        bad = await tool("get_pou", path="Device/Nope")
        assert bad.isError and "not found" in bad.content[0].text
        bad = await tool("create_pou", parent=APP, name="X", kind="Bogus")
        assert bad.isError
    print("e2e ok")


def test_parse_csv():
    import server
    text = ("\ufeff[key]; [value]\nName; Application.T\nIecTaskName; MainTask\nEveryNCycles; 1\n"
            "0.Variable; PRG.a\n0.Data; \n; 100; 1\n; 300; 1\n; 500; 0\n"
            "1.Variable; PRG.b\n1.Data; \n; 100; 2\n; 300; 2\n; 500; 3\n")
    out = server.parse_csv(text, max_rows=10)
    assert out["columns"] == ["time_ms", "PRG.a", "PRG.b"]
    assert out["changes"] == [[100, "1", "2"], [500, "0", "3"]]   # t=300 repeats the previous row
    assert out["samples"] == 3 and out["meta"]["IecTaskName"] == "MainTask" and not out["truncated"]
    assert server.parse_csv(text, 1)["truncated"]
    assert server.parse_csv("", 5)["changes"] == []


def test_stale_online_object():
    """A cached online object that went stale is replaced on a failed read or a failed write probe."""
    class Stale(Online):
        def read_value(self, n):
            raise Exception("Internal error: Invalid variable reference")

    class Fresh(Online):
        written = []

        def set_prepared_value(self, n, v):
            Fresh.written.append((n, v))

        def write_prepared_values(self):
            pass

    made = []

    def create(a):
        obj = Stale() if not made else Fresh()
        made.append(obj)
        return obj

    old = builtins.online
    builtins.online = types.SimpleNamespace(create_online_application=create)
    bridge.online = builtins.online
    bridge._online_apps.clear()
    try:
        assert bridge.h_read_var({"app": APP, "names": ["x"]}) == {"x": "42"}
        assert len(made) == 2                       # stale one replaced once
        bridge._online_apps.clear(); made.clear()
        assert bridge.h_write_var({"app": APP, "values": {"x": 1}}) is True
        assert Fresh.written == [("x", "1")] and len(made) == 2
        class Always(Online):
            def read_value(self, n):
                raise Exception("Invalid variable reference")
        bridge._online_apps.clear()
        bridge.online = types.SimpleNamespace(create_online_application=lambda a: Always())
        try:
            bridge.h_read_var({"app": APP, "names": ["x"]})
        except Exception as e:
            assert "Invalid variable reference" in str(e)   # a real error still comes through
        else:
            raise AssertionError("expected the error")
    finally:
        builtins.online = bridge.online = old
        bridge._online_apps.clear()


def test_unreachable_bridge():
    import server
    server.PORT = 1  # nothing listens here
    try:
        server.call("ping")
    except server.BridgeError as e:
        assert "unreachable" in str(e)
    else:
        raise AssertionError("expected BridgeError")


if __name__ == "__main__":
    threading.Thread(target=bridge.serve, daemon=True).start()
    time.sleep(0.5)
    test_parse_csv()
    test_stale_online_object()
    test_unreachable_bridge()
    asyncio.run(run())
