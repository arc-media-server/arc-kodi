#!/usr/bin/env python3
"""Static checks for the add-on, run before every PR (no Kodi needed):

- every skin XML parses, and resources/skins/ is what tools/build_skin.py makes from skin/;
- every control id a window's Python names exists in that window's XML;
- every string id used in Python (T(30xxx)) and XML ($ADDON[script.arc 30xxx]) is in strings.po;
- nothing under resources/lib/arc/ imports a Kodi module (that layer must stay testable);
- addon.xml parses and names default.py.

Exits non-zero on the first failure, naming it.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIN = os.path.join(ROOT, "resources", "skins", "Main")
ARC = os.path.join(ROOT, "resources", "lib", "arc")
KODI = os.path.join(ROOT, "resources", "lib", "kodi")
PO = os.path.join(ROOT, "resources", "language", "resource.language.en_gb", "strings.po")

errors = []


def fail(msg):
    errors.append(msg)


def po_ids():
    ids = set()
    with open(PO, encoding="utf-8") as f:
        for line in f:
            m = re.match(r'msgctxt\s+"#(\d+)"', line.strip())
            if m:
                ids.add(int(m.group(1)))
    return ids


def check_xml_parses():
    for folder in (SKIN, os.path.join(ROOT, "skin")):
      for base, _, files in os.walk(folder):
        for name in files:
            if name.endswith(".xml"):
                path = os.path.join(base, name)
                try:
                    ET.parse(path)
                except ET.ParseError as e:
                    fail("XML won't parse: %s: %s" % (os.path.relpath(path, ROOT), e))


def check_strings():
    ids = po_ids()
    used = set()
    pat_py = re.compile(r"\bT\((\d{5})\)")
    pat_xml = re.compile(r"\$ADDON\[script\.arc (\d{5})\]")
    for base, _, files in os.walk(os.path.join(ROOT, "resources", "lib")):
        for name in files:
            if name.endswith(".py"):
                text = open(os.path.join(base, name), encoding="utf-8").read()
                used.update(int(x) for x in pat_py.findall(text))
    for base, _, files in os.walk(SKIN):
        for name in files:
            if name.endswith(".xml"):
                text = open(os.path.join(base, name), encoding="utf-8").read()
                used.update(int(x) for x in pat_xml.findall(text))
    for sid in sorted(used - ids):
        fail("string %d is used but not in strings.po" % sid)


def check_arc_pure():
    banned = re.compile(r"^\s*(import|from)\s+(xbmc|xbmcgui|xbmcaddon|xbmcvfs|xbmcplugin)")
    for base, _, files in os.walk(ARC):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(base, name)
                for i, line in enumerate(open(path, encoding="utf-8"), 1):
                    if banned.match(line):
                        fail("%s:%d imports a Kodi module; the arc/ layer must stay testable"
                             % (os.path.relpath(path, ROOT), i))


def check_addon():
    path = os.path.join(ROOT, "addon.xml")
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        fail("addon.xml won't parse: %s" % e)
        return
    ext = tree.find(".//extension[@point='xbmc.python.script']")
    if ext is None or ext.get("library") != "default.py":
        fail("addon.xml must declare default.py as the script library")


def check_skin_built():
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_skin.py"), "--check"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail("the built skin is stale; run tools/build_skin.py\n    " + r.stdout.strip().replace("\n", "\n    "))


def check_control_ids():
    """Every control id a window's Python names (module constants in windows/*.py) exists in the
    built XML of the window(s) that module opens."""
    built = os.path.join(SKIN, "1080i")
    windows = os.path.join(KODI, "windows")
    skip = re.compile(r"(BASE|MAX|SIZE|ACTION|ROWS?_?COUNT)")
    for name in sorted(os.listdir(windows)):
        if not name.endswith(".py"):
            continue
        text = open(os.path.join(windows, name), encoding="utf-8").read()
        xmls = set(re.findall(r'xml = "(script-arc-[a-z-]+\.xml)"', text))
        if "GridWindow" in text and "library" in name:
            xmls.add("script-arc-grid.xml")
        if not xmls:
            continue
        ids = set()
        for x in xmls:
            path = os.path.join(built, x)
            if not os.path.exists(path):
                fail("%s opens %s, which isn't built" % (name, x))
                continue
            ids |= {int(e.get("id")) for e in ET.parse(path).iter() if (e.get("id") or "").isdigit()}
        for const, value in re.findall(r"^(?:    )?([A-Z][A-Z_0-9]*) = (\d+)\s*(?:#.*)?$", text, re.M):
            if skip.search(const):
                continue
            if int(value) not in ids:
                fail("windows/%s: %s = %s isn't a control in %s" % (name, const, value, ", ".join(sorted(xmls))))
    # The player overlay lives outside windows/.
    path = os.path.join(built, "script-arc-player.xml")
    text = open(os.path.join(KODI, "player_osd.py"), encoding="utf-8").read()
    if os.path.exists(path):
        ids = {int(e.get("id")) for e in ET.parse(path).iter() if (e.get("id") or "").isdigit()}
        for const, value in re.findall(r"^([A-Z][A-Z_0-9]*) = (\d+)\s*$", text, re.M):
            if int(value) not in ids:
                fail("player_osd.py: %s = %s isn't a control in script-arc-player.xml" % (const, value))


def check_media():
    """Every image a built window names exists in the media folder (Kodi shows nothing, silently,
    for a missing one), and the media folder holds nothing unused."""
    media = os.path.join(SKIN, "media")
    have = set(os.listdir(media)) if os.path.isdir(media) else set()
    used = set()
    built = os.path.join(SKIN, "1080i")
    for name in os.listdir(built):
        text = open(os.path.join(built, name), encoding="utf-8").read()
        used |= set(re.findall(r"(arc-[a-z0-9-]+\.png)", text))
    # The sidebar's icons are named from a ListItem property: arc-icon-<name>.png.
    used |= {n for n in have if n.startswith("arc-icon-")}
    for n in sorted(used - have):
        if "$INFO" not in n:
            fail("a window uses %s, which isn't in resources/skins/Main/media" % n)
    for n in sorted(have - used):
        fail("resources/skins/Main/media/%s isn't used by any window" % n)


def check_py_compiles():
    import py_compile
    for base, _, files in os.walk(os.path.join(ROOT, "resources", "lib")):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(base, name)
                try:
                    py_compile.compile(path, doraise=True)
                except py_compile.PyCompileError as e:
                    fail("%s won't compile: %s" % (os.path.relpath(path, ROOT), e))
    for name in ("default.py",):
        try:
            py_compile.compile(os.path.join(ROOT, name), doraise=True)
        except py_compile.PyCompileError as e:
            fail("%s won't compile: %s" % (name, e))


def main():
    check_xml_parses()
    check_skin_built()
    check_control_ids()
    check_media()
    check_strings()
    check_arc_pure()
    check_addon()
    check_py_compiles()
    if errors:
        print("check.py found %d problem(s):" % len(errors))
        for e in errors:
            print("  - " + e)
        return 1
    print("check.py: all good")
    return 0


if __name__ == "__main__":
    sys.exit(main())
