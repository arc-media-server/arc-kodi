#!/usr/bin/env python3
"""Drives a Kodi running on a virtual display (see CLAUDE.md, "Checking it in Kodi"): sends remote
keys and JSON-RPC calls over Kodi's TCP JSON-RPC (port 9090, on by default for this machine) and
takes screenshots of the display. Dev only.

    python3 tools/kodi_rpc.py action down right select     # remote keys (Kodi action names)
    python3 tools/kodi_rpc.py text 127.0.0.1:8199          # type into an open keyboard
    python3 tools/kodi_rpc.py shot home                    # $ARC_SHOTS/home.png (960x540)
    python3 tools/kodi_rpc.py Addons.ExecuteAddon '{"addonid":"script.arc"}'
"""
import json
import os
import socket
import subprocess
import sys
import time

DISPLAY = os.environ.get("DISPLAY", ":99")
SHOTS = os.environ.get("ARC_SHOTS", "shots")

def rpc(method, params=None):
    s = socket.create_connection(("127.0.0.1", 9090), timeout=10)
    s.sendall(json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}).encode())
    buf = b""
    while True:
        chunk = s.recv(65536)
        if not chunk: break
        buf += chunk
        try:
            out = json.loads(buf); break
        except ValueError:
            continue
    s.close()
    return out

def shot(name):
    os.makedirs(SHOTS, exist_ok=True)
    path = os.path.join(SHOTS, "%s.png" % name)
    subprocess.run(["import", "-display", DISPLAY, "-window", "root", "-resize", "960x540", path], check=True)
    return path

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "shot":
        print(shot(sys.argv[2]))
    elif cmd == "action":
        for a in sys.argv[2:]:
            print(a, rpc("Input.ExecuteAction", {"action": a}).get("result")); time.sleep(0.6)
    elif cmd == "text":
        print(rpc("Input.SendText", {"text": sys.argv[2], "done": True}))
    else:
        params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        print(json.dumps(rpc(cmd, params))[:2000])
