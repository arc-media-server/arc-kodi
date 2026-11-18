# Star rating

The existing title page's Context Menu now offers **Rate…** for films, shows and episodes,
matching Android #34. It opens the existing Arc menu as **Your Rating**, with five stars down
to half a star, the current choice ticked and focused, and **Clear Rating** only when rated.
Unrated titles start at five stars; Back cancels without a write. Choosing the current rating
does nothing. Card menus omit ratings, as Android does. No new window or skin is introduced.

The plain-Python ratings helper formats whole/half stars and numbers out of five. The API client
sends `PUT /api/v1/items/{id}/rating` with 1–10 half-star units, or zero to clear. Only a successful
save changes `user_data.rating`; failures preserve the prior value and show Android's translated
failure wording. Existing title callbacks refresh after saving. Strings use reserved ids
30500–30504. No new product decisions or settings.

Validation is being repeated after recovery of the temporary execution environment. Historical
checks on the original implementation passed 114 pytest tests and `tools/check.py`; current
results and real Kodi screenshots will be recorded before the PR is opened. No skin inputs changed.

Logging: a failed save logs the outcome and exception class at warning; a successful save logs
only at debug. No credentials, item names or URLs are logged. Not tried on a TV; no playback,
audio or HDR hardware checks are claimed. Latest main `1175354` had no rating action.
