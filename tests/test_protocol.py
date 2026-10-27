"""Protocol test: runs the bridge outside the IDE with stubbed scriptengine globals."""
import builtins
import json
import os
import socket
import sys
import threading
import time
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bridge"))
os.environ.update(CTRLX_MCP_TOKEN="t0k", CTRLX_MCP_PORT="18765")


class Node:
    def __init__(self, name, children=()):
        self._name, self._children = name, list(children)
        self.has_textual_declaration = True
        self.textual_declaration = types.SimpleNamespace(text="decl", replace=self._set)

    def _set(self, t):
        self.textual_declaration.text = t

    def get_name(self):
        return self._name

    def get_children(self, recursive):
        return self._children


app = Node("Application", [Node("GVL")])
proj = Node("proj", [Node("Device", [Node("PLC Logic", [app])])])
proj.path = "/x.project"
for name, val in dict(projects=types.SimpleNamespace(primary=proj), online=None,
                      system=None, trace=None).items():
    setattr(builtins, name, val)

import bridge  # noqa: E402


def rpc(cmd, token="t0k", **args):
    with socket.create_connection(("127.0.0.1", 18765), timeout=5) as s:
        s.sendall(json.dumps({"id": 1, "token": token, "cmd": cmd, "args": args}).encode() + b"\n")
        return json.loads(s.makefile().readline())


def main():
    threading.Thread(target=bridge.serve, daemon=True).start()
    time.sleep(0.5)
    assert rpc("ping")["ok"]
    assert rpc("ping", token="bad")["error"] == "unauthorized"
    assert "unknown cmd" in rpc("nope")["error"]
    tree = rpc("get_tree", path="Device/PLC Logic", depth=2)["result"]
    assert tree[0]["name"] == "Application" and tree[0]["children"][0]["name"] == "GVL"
    assert rpc("set_pou", path="Device/PLC Logic/Application/GVL", declaration="VAR_GLOBAL END_VAR")["ok"]
    assert rpc("get_pou", path="Device/PLC Logic/Application/GVL")["result"]["declaration"] == "VAR_GLOBAL END_VAR"
    r = rpc("get_pou", path="Device/Missing")
    assert not r["ok"] and "not found" in r["error"]
    r = rpc("exec", code="print('hi')\nresult = 1 + 1")["result"]
    assert r == {"stdout": "hi\n", "result": 2}
    print("ok")


if __name__ == "__main__":
    main()
