#!/usr/bin/env python3
"""Retakes the README screenshots (docs/screenshots/*.jpg) in real Kodi against Arc's shared
screenshot library (arc-media-server docs/SCREENSHOTS.md). Dev only.

Start the library's scratch Arc in arc-media-server
(`cd web && node tools/screenshots.mjs --serve --state <file>`), then Kodi on a virtual display
with a fresh profile (docs/DEVELOPING.md, "Checking it in Kodi"), then:

    python3 tools/readme_shots.py --state <file>

It drives Kodi only with remote keys (tools/kodi_rpc.py), signs in with the library's household
password (a throwaway one for a throwaway server; it is typed into Arc's keyboard, never stored
or printed) and writes 1600-wide JPEGs. Never point it at a real server."""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "tools"), os.path.join(ROOT, "resources", "lib")]
from arc import search  # noqa: E402
from arc.keyboard import PAGES  # noqa: E402  (the address and password keyboard's pages)
from kodi_rpc import DISPLAY, rpc  # noqa: E402

OUT = os.path.join(ROOT, "docs", "screenshots")
# Search's own keyboard, six keys across.
SEARCH = {"search": ["".join(search.KEYS[i:i + search.COLUMNS])
                     for i in range(0, len(search.KEYS), search.COLUMNS)]}


def act(*actions, wait=0.6):
    for a in actions:
        rpc("Input.ExecuteAction", {"action": a})
        time.sleep(wait)


def focused():
    r = rpc("GUI.GetProperties", {"properties": ["currentcontrol"]})
    return r.get("result", {}).get("currentcontrol", {}).get("label", "")


def settle(seconds=3.0):  # time for Arc's answers and the artwork
    time.sleep(seconds)


def shot(name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".jpg")
    subprocess.run(["import", "-display", DISPLAY, "-window", "root", "-resize", "1600x900",
                    "-quality", "84", path], check=True)
    print(path)


class Keyboard:
    """Types into Arc's on-screen keyboard by moving focus key by key, as a remote would."""

    def __init__(self, page, pages=PAGES):
        self.page, self.row, self.col = page, 0, 0   # it opens on the first key
        self.pages = pages

    def _move(self, row, col):
        while self.row < row:
            act("down", wait=0.25); self.row += 1
        while self.row > row:
            act("up", wait=0.25); self.row -= 1
        while self.col < col:
            act("right", wait=0.25); self.col += 1
        while self.col > col:
            act("left", wait=0.25); self.col -= 1

    def _bottom(self, label):
        """Presses a key in the row under the grid (Shift, 123/ABC, Done) and comes back up."""
        self._move(len(self.pages[self.page]) - 1, 0)
        act("down", wait=0.4)
        act(*["left"] * 6, wait=0.2)   # from Shift, at the row's left end
        for _ in range(8):
            if focused() == label:
                break
            act("right", wait=0.3)
        else:
            raise SystemExit("keyboard: no %r key" % label)
        act("select", wait=0.5)
        if label != "Done":
            act("up", wait=0.4)
            last = self.pages[self.page][-1]
            self.row, self.col = len(self.pages[self.page]) - 1, max(0, last.find(focused()))

    def _page_for(self, ch):
        for page in [self.page] + list(self.pages):
            if any(ch in r for r in self.pages[page]):
                return page
        raise SystemExit("keyboard: can't type %r" % ch)

    def _go_to_page(self, page):
        while self.page != page:
            if {self.page, page} == {"lower", "upper"}:
                self._bottom("Shift"); self.page = page
            elif self.page == "symbols":
                self._bottom("ABC"); self.page = "lower"
            else:
                self._bottom("123"); self.page = "symbols"

    def type(self, text):
        for ch in text:
            self._go_to_page(self._page_for(ch))
            for r, row in enumerate(self.pages[self.page]):
                if ch in row:
                    self._move(r, row.index(ch))
            act("select", wait=0.3)

    def done(self):
        self._bottom("Done")

    def clear(self):
        self._bottom("Clear")


def until(label, key, tries=10, match=str.__eq__):
    """Presses key until the focused control's label matches."""
    for _ in range(tries):
        if match(focused(), label):
            return
        act(key)
    raise SystemExit("couldn't reach %r (on %r)" % (label, focused()))


def search_keys():
    """Arc's search keyboard, wherever its focus is (Left until it's on a key)."""
    until("", "left", match=lambda f, _: len(f) == 1)
    kb, label = Keyboard("search", SEARCH), focused()
    for r, row in enumerate(SEARCH["search"]):
        if label in row:
            kb.row, kb.col = r, row.index(label)
    return kb


def walk(state):
    # Connect: the address field opens Arc's keyboard; Done connects.
    act("select"); settle(1.5)
    kb = Keyboard("lower")
    kb.type(state["address"].replace("http://", ""))
    kb.done(); settle(5)
    shot("sign-in")                                  # the code to approve
    until("Sign In with Password", "down")
    act("select"); settle(1.5)
    kb = Keyboard("lower")
    kb.type(state["password"])                       # the library's throwaway password
    kb.done(); settle(6)
    shot("profiles")                                 # Who's watching?
    until(state.get("admin", "Jordan"), "right")
    act("select"); settle(10)
    shot("home")

    act("left"); until("Search", "up")
    act("select"); settle(2)
    search_keys().type("dune"); settle(5)
    shot("search")
    until("Dune: Part Two", "right")
    act("select"); settle(8)
    shot("film")
    act("contextmenu"); settle(2)
    until("Watch Together", "down", match=str.startswith)
    act("select"); settle(4)
    act("select"); settle(2)                         # tick the first person
    shot("watch-together")
    act("back", "back", wait=2)

    kb = search_keys(); kb.clear(); kb.type("breaking"); settle(5)
    until("Breaking Bad", "right")
    act("select"); settle(8)
    act("down", "down", wait=2)                      # onto the next episode, in the season row
    shot("show")
    for _ in range(3):                               # back to Home's sidebar
        act("back", wait=3)
        if focused() == "Search":
            break
    until("Movies", "down")
    act("select"); settle(8)
    until("Recommended", "up")
    act("right", "select"); settle(6)                # Browse, with Play All, Shuffle, Sort, Filter
    shot("library")
    act("back"); settle(3)

    until("Settings", "down")
    act("select"); settle(5)
    shot("settings")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", required=True, help="the JSON written by screenshots.mjs --state")
    args = p.parse_args()
    with open(args.state) as f:
        state = json.load(f)
    if not state.get("address", "").startswith("http://127.0.0.1:"):
        raise SystemExit("only the scratch screenshot server on this machine")
    rpc("Addons.ExecuteAddon", {"addonid": "script.arc"}); settle(6)
    walk(state)


if __name__ == "__main__":
    main()
