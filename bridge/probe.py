# -*- coding: utf-8 -*-
"""Bisect probe for bridge.py crashes. Run via Tools > Scripting > Execute Script File.

Logs each step BEFORE running it to %TEMP%\\ctrlx_probe.log (flushed), so the last line
shows where the IDE died. Does not need the token.
"""
import os
import sys

import time

_dir = os.environ.get("TEMP", ".")
LOG = os.path.join(_dir, "ctrlx_probe.log")
try:
    open(LOG, "w").close()
except IOError:
    # locked by an earlier run or an open viewer: use a fresh name
    LOG = os.path.join(_dir, "ctrlx_probe_%d.log" % int(time.time()))


def step(msg):
    # open/close per line so nothing stays locked and the last line survives a crash
    f = open(LOG, "a")
    try:
        f.write(msg + "\n")
    finally:
        f.close()


step("log file: " + LOG)


step("start, python " + sys.version.replace("\n", " "))
step("import json");       import json
step("import socket");     import socket
step("import tempfile");   import tempfile
step("import traceback");  import traceback
step("import StringIO")
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
step("projects.primary")
step("  -> %r" % (projects.primary,))
step("projects.primary.path")
step("  -> %r" % (projects.primary.path if projects.primary else None,))
step("socket create")
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
step("setsockopt")
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
step("bind")
srv.bind(("127.0.0.1", 8766))
step("listen")
srv.listen(5)
step("settimeout")
srv.settimeout(1.0)
step("accept x3 (expect timeouts)")
for i in range(3):
    try:
        srv.accept()
    except socket.timeout:
        step("  timeout %d" % i)
step("PHASE 2: accept loop for 60 s - click around the IDE (open a menu, switch tabs) while it runs")
t0 = time.time()
n = 0
while time.time() - t0 < 60:
    try:
        srv.accept()
    except socket.timeout:
        n += 1
        if n % 10 == 0:
            step("  still looping, %d s" % int(time.time() - t0))
srv.close()
step("DONE - all steps survived")
