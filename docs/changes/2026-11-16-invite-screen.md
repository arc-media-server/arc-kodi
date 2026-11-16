# Watch Together's invite screen

The owner found the invite screen confusing: it was Arc's menu, so the people and the actions
were rows in one list ("Alex", "Send Invite", "Use a Code Instead"), and a person looked like an
option. It now has its own window (`kodi/windows/invite.py`, `script-arc-invite.xml`):

- what to do at the top: "Choose who to watch <title> with from the people below. They'll find
  it on Home under Watch Together." (for a room already open: "Choose who else to invite from
  the people below…");
- the people in a box of their own, each with a tick ring (an empty ring, or a white disc with
  a check once ticked); Select ticks or unticks. Someone who can't watch the title is greyed,
  says so, and can't be ticked; a friend says "Friend";
- under the box, side by side, **Send Invite** and **Use a Code Instead** (only Send Invite for
  a room already open). Send Invite is greyed until someone is ticked, and Down from the box
  goes to whichever button can be used.

With nobody to invite the box and Send Invite are left out and the message says to use a code.
Back closes the screen without doing anything, as before. What each button does is unchanged.

The invite button reads "Send Invite" (also in #20, the same change).

## Logging

Unchanged: "Watch Together room made for N people", and warnings when a room isn't made.

## Checked

Kodi on Xvfb against a scratch Arc (Blade Runner, the scripted second profile Alex): the screen
opens from the title's ⋯ menu; ticking Alex lights Send Invite; Send Invite made the room ("room
made for 1 people"). Not on real hardware.
