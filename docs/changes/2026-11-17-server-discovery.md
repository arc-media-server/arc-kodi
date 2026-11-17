# Find Arc on the home network

The Connect screen searches the Kodi device's own private IPv4 /24 on port 8099,
using anonymous GET /api/v1/discover requests. Arc answers appear below the address
box under “On your network”; “Search Again” starts a fresh search. The existing
address entry and Connect button remain available.

This follows Android #42 and the existing TV/Roku discovery: RFC1918 networks
only, no self/network/broadcast probes, short timeouts, bounded parallel requests,
Arc product and API-version validation, duplicate server IDs removed. Results use
the address actually probed, never an address supplied by the discovery response.
The first server takes focus unless the address keyboard is open or a manual
address has been entered. Later answers do not move focus. Back and repeated
searches cancel publication and further probes; already active requests finish
within their short timeout. Discovery sends no stored credentials and bypasses
HTTP proxies and redirects.

No new screen or control style was introduced: the existing Connect screen uses
Arc's pill buttons and list rows. Only the source skin was edited; built XML was
regenerated. Kodi exposes its current IPv4 address without the interface's prefix,
so search is restricted to its /24, matching the requested bound. IPv6 and remote
networks require manual entry. No product decision beyond the requested behavior.

Checks: `python3 -m pytest -q` — 129 passed (one external pytest plugin
deprecation warning); `python3 tools/check.py` — passed;
`python3 tools/build_skin.py` — regenerated all 16 windows. Tests use local HTTP
stand-ins and injected probe functions, never actual LAN searches. Layout evidence
is in [the screenshot folder](2026-11-17-server-discovery/): real Debian Kodi
21.2 on Xvfb, driven and captured with `tools/kodi_rpc.py` (scratch copy
configured for its dedicated RPC port). The screenshot fixture limits candidates
to loopback and redirects the port to scratch Arc 18459; it never scans the host
LAN. Verified first-row focus, the address keyboard, and Search Again using remote
keys. The screenshot revealed a clipped address; the list row was enlarged and
recaptured with both lines visible. Not tried on a TV;
virtual Kodi cannot certify hardware playback, audio, or HDR.

Logging: one completion outcome with a server count. Expected unreachable/non-Arc
probes are quiet; no names, addresses, URLs, credentials, or codes are logged.
