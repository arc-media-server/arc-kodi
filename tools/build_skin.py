#!/usr/bin/env python3
"""Builds the add-on's WindowXML files from skin/ into resources/skins/Main/1080i/.

Kodi only loads <include>s, named colours and fonts from the user's active skin, never from an
add-on's own folder. So the windows are written in skin/ using our shared pieces
(skin/includes.xml: <constant>s for colours and fonts, <include>s for buttons and cards), and this
tool expands them into self-contained files Kodi reads as they are. Run it after changing
anything in skin/ and commit what it writes; tools/check.py fails when the output is stale.

    python3 tools/build_skin.py          # write
    python3 tools/build_skin.py --check  # exit 1 if the committed output differs
"""

import copy
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "skin")
OUT = os.path.join(ROOT, "resources", "skins", "Main", "1080i")

HEADER = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!-- Built by tools/build_skin.py from skin/%s: edit that, not this. -->\n"


def load_includes():
    root = ET.parse(os.path.join(SRC, "includes.xml")).getroot()
    constants, includes = {}, {}
    for el in root:
        if el.tag == "constant":
            constants[el.get("name")] = (el.text or "").strip()
        elif el.tag == "include":
            params = {p.get("name"): p.get("default", "") for p in el.findall("param")}
            definition = el.find("definition")
            body = list(definition) if definition is not None else [c for c in el if c.tag != "param"]
            includes[el.get("name")] = (params, body)
    return constants, includes


def _substitute(el, values):
    pat = re.compile(r"\$PARAM\[(\w+)\]")

    def sub(text):
        return pat.sub(lambda m: values.get(m.group(1), ""), text) if text else text

    for node in el.iter():
        node.text = sub(node.text)
        for k, v in list(node.attrib.items()):
            node.attrib[k] = sub(v)


def expand(parent, includes, depth=0):
    if depth > 10:
        raise ValueError("includes nest too deep")
    i = 0
    while i < len(parent):
        child = parent[i]
        if child.tag == "include":
            name = child.get("content") or (child.text or "").strip()
            if name not in includes:
                raise ValueError("unknown include %r" % name)
            params, body = includes[name]
            values = dict(params)
            for p in child.findall("param"):
                values[p.get("name")] = p.get("value", "")
            # Explicit tags on the control win over the include's (e.g. a button's own <width>).
            own = {c.tag for c in parent if c.tag not in ("include", "control")}
            pieces = []
            for b in body:
                if b.tag != "control" and b.tag in own:
                    continue
                n = copy.deepcopy(b)
                _substitute(n, values)
                pieces.append(n)
            parent.remove(child)
            for j, n in enumerate(pieces):
                parent.insert(i + j, n)
            continue  # re-examine from the first inserted piece (it may hold includes)
        expand(child, includes, depth + 1)
        i += 1


def apply_constants(root, constants):
    for node in root.iter():
        if node.text and node.text.strip() in constants:
            node.text = constants[node.text.strip()]
        for k, v in list(node.attrib.items()):
            if v in constants:
                node.attrib[k] = constants[v]


def build_one(name, constants, includes):
    tree = ET.parse(os.path.join(SRC, name))
    root = tree.getroot()
    expand(root, includes)
    apply_constants(root, constants)
    ET.indent(root, space="  ")
    text = ET.tostring(root, encoding="unicode")
    if "$PARAM[" in text:
        raise ValueError("%s: a $PARAM[...] was left unexpanded" % name)
    return HEADER % name + ET.tostring(root, encoding="unicode") + "\n"


def build():
    constants, includes = load_includes()
    out = {}
    for name in sorted(os.listdir(SRC)):
        if name.startswith("script-arc-") and name.endswith(".xml"):
            out[name] = build_one(name, constants, includes)
    return out


def main(argv):
    built = build()
    if "--check" in argv:
        stale = []
        for name, text in built.items():
            path = os.path.join(OUT, name)
            if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
                stale.append(name)
        extra = [n for n in os.listdir(OUT) if n.endswith(".xml") and n not in built] if os.path.isdir(OUT) else []
        for n in stale:
            print("stale: %s (run tools/build_skin.py)" % n)
        for n in extra:
            print("not built from skin/: %s" % n)
        return 1 if stale or extra else 0
    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(OUT):
        if name.endswith(".xml") and name not in built:
            os.remove(os.path.join(OUT, name))
    for name, text in built.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(text)
    print("built %d windows into %s" % (len(built), os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
