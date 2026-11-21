# Wording and a credit in the README

The agent notes, docs, change notes and code and skin comments now describe the add-on on its own
terms: Kodi-specific behaviour follows Kodi's own settings and conventions, and product behaviour
follows Arc's design and Plex. The README credits the add-on's inspiration instead (owner,
21 November). Text only; no behaviour changed.

**Checks:** `python3 -m pytest -q` (186 passed), `python3 tools/check.py` (all good),
`python3 tools/build_skin.py` (no change to the built windows).

**Logging:** none; text only.
