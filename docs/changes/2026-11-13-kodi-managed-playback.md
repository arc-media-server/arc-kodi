# Let Kodi own format compatibility

Owner decision: use Kodi's player and settings for decoding, software fallback, local HDR/Dolby
Vision conversion, tone mapping and audio output instead of maintaining per-device rules.

- Remove display-HDR probes, the P8-only whitelist, display-derived 10-bit ceiling and
  passthrough-toggle reporting. The shared source codec/container lists remain broad defaults.
- Omit HDR/profile/audio-output restrictions rather than send an empty SDR-only HDR array.
  This uses Arc's existing API semantics; no server change is needed.
- Declare Arc's 16-bit source ceiling so its browser-oriented H.264 Hi10 default does not force
  conversion before Kodi can try its software decoder. This describes accepted sources, not
  a display output mode or verified hardware decoder.
- Keep the resolution limit, selected quality, server/profile limits, track/version choices,
  source-relative progress and existing error fallback. The add-on now reads its existing
  maximum-resolution setting instead of always using the function's 2160p default.
- Put request-policy construction in the Kodi-free layer and document the playback policy.

Logging: replace probe-derived capability detail with one debug-only Kodi-managed policy/height
line per playback object. Existing request/playback failures remain logged; no tokens, URLs,
credentials or file paths added. No new info-level events or per-frame logging.

Limits: this is a source-playback policy, not a guarantee every Kodi device can play every file
or output original Dolby Vision/FEL/Atmos. No real Kodi/hardware playback checks are claimed.

Validation: Python 3.12; all 42 pytest tests passed and `python3 tools/check.py` passed.
Tests cover omitted HDR/profile/output fields, source bit depth, independent requests,
resolution preferences/default recovery, request limits/track/version/resume forwarding and
existing fallback behavior against a stand-in server. `git diff --check` passed. No skin/media
changes, so regeneration was unnecessary. pytest was absent and installed only into a temporary
test directory; project/runtime dependencies are unchanged. External pytest plugin autoload
was disabled for the final run to isolate the repository's tests. No real Kodi, hardware,
owner server or production media was used.
