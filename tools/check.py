#!/usr/bin/env python3
"""Static checks for the add-on, run before every PR (no Kodi needed):

- every skin XML parses;
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
    for base, _, files in os.walk(SKIN):
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
