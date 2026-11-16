# Consolidate the remaining Kodi feature-parity PRs

PR #4 was squash-merged as main 2ff66a1. Its tree matches the original parity branch
4e3ed6e, but its original commits are not ancestors of main. PRs #5–#11 were a stack
on that original history, all targeting main; their overlapping changes now conflict.

At the owner's request, replace those seven open PRs with one standalone PR based directly
on current main. Carry forward the complete latest stack at 30d5c48 (kodi-offsets):

- #5: library sort/filters, folders, people/collections and play queues;
- #6: chapters, thumbnails, episode selection and playback speed;
- #7: settings, password sign-in and the PIN pad;
- #8: search;
- #9: live updates;
- #10: Watch Together and row navigation;
- #11: audio/subtitle offsets.

The staged tree matched 30d5c48 exactly before this note and a trailing-whitespace-only
cleanup in the existing Watch Together note. Application code, tests, translations, source
skins, generated windows and artwork remain identical to that stack. No feature work or
conflict resolution that chooses between application versions is introduced. Main and the
original branches are preserved; the old PRs are closed as superseded only after the
replacement exists. No merge, branch deletion or force push.

Validation in this session (Python 3.12.14): `python3 tools/check.py` passed;
`python3 tools/build_skin.py` regenerated all 13 windows without changing their content;
source/asset/test equivalence and final whitespace checks passed.
`python3 -m pytest -q` could not run because pytest is absent from both available Python
interpreters. No tools were installed. The original #11 report's 96 passing tests are
historical evidence, not a fresh result. No Kodi/hardware/playback acceptance is claimed,
and no owner server, media, data or keys were accessed.

Logging behavior is unchanged. The original feature notes retain their logging coverage;
this consolidation adds no runtime messages.
