#!/usr/bin/env python3
"""Zips the add-on as script.arc/ into dist/, ready for Kodi's "Install from zip file".

    python3 tools/package.py
"""

import os
import xml.etree.ElementTree as ET
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INCLUDE = ("addon.xml", "default.py", "LICENSE", "README.md", "resources")
# Never ship these.
SKIP_DIRS = {".git", "__pycache__", "tests", "tools", "docs", "dist", ".github"}
SKIP_EXT = {".pyc", ".pyo"}


def version():
    return ET.parse(os.path.join(ROOT, "addon.xml")).getroot().get("version")


def main():
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    zip_path = os.path.join(out_dir, "script.arc-%s.zip" % version())
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for entry in INCLUDE:
            path = os.path.join(ROOT, entry)
            if os.path.isfile(path):
                z.write(path, "script.arc/" + entry)
            else:
                for base, dirs, files in os.walk(path):
                    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                    for name in files:
                        if os.path.splitext(name)[1] in SKIP_EXT:
                            continue
                        full = os.path.join(base, name)
                        rel = os.path.relpath(full, ROOT)
                        z.write(full, "script.arc/" + rel)
    print("wrote", os.path.relpath(zip_path, ROOT))


if __name__ == "__main__":
    main()
