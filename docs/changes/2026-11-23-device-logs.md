# Send logs on Kodi

Arc’s Settings sends recent app events only after confirmation. Detailed logging lasts two hours.
The upload projects recognised Arc log templates into fixed event codes, with no raw kodi.log,
log arguments or exception text. The bounded journal is stored in addon_data and cleared when
signing out or changing server. An uncaught add-on error offers to send logs on the next launch.

Checks: 192 pytest tests passed with scratch loopback access, and tools/check.py passed.
Kodi’s on-device screen and an actual crash were outside this check.

Server dependency: [Arc Media Server #508](https://github.com/arc-media-server/arc-media-server/pull/508).
