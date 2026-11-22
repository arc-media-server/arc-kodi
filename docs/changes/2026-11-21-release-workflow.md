# Releases from a one-click build

**What:** a new `.github/workflows/build.yml` (arc-media-server#488). Actions → Build → Run
workflow on `main` runs `pytest` and `tools/check.py`, zips the add-on with `tools/package.py`,
writes `SHA256SUMS.txt` and publishes a pre-release `kodi-build-<run>` with GitHub's generated
notes. A `v*` tag makes a normal release.

**Versions:** `addon.xml`'s major.minor plus the run number (`0.1.57`), or the tag's version,
stamped into `addon.xml` in the run only, so Kodi treats each build as an update and the zip's
name matches the release.

**Decisions:**
- Only a manual run on `main` or a `v*` tag releases; marked pushes and manual runs on other
  branches keep a run artifact only, so agents can't publish. Nothing runs on pull requests.
- `contents: write` only on the release job; a newer run never cancels one that's publishing.
- A Kodi repository add-on for automatic updates stays a later question.

**Checks:** pytest (186 passed) and check.py passed locally; the version stamping and packaging
(`script.arc-0.1.7.zip`) ran locally; the workflow parses as YAML. `actionlint` wasn't run. The
workflow hasn't run on GitHub: the owner does the first release.

**Logging:** nothing new in the add-on.
