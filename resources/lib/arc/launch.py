"""Choose a profile at add-on launch from the server's current profile list."""


def launch_profile(status, automatic_id=None, *, fresh=True):
    current = status.get("profile")
    if not fresh or status.get("friend"):
        return current

    profiles = status.get("profiles") or []
    if automatic_id:
        # An invalid preference goes to the picker, even if one other profile remains.
        return next((p for p in profiles if p.get("id") == automatic_id and not p.get("has_pin")), None)
    if len(profiles) == 1 and current and current.get("id") == profiles[0].get("id"):
        # Keep Kodi's existing single-profile shortcut for an already selected, unlocked profile.
        if not profiles[0].get("has_pin"):
            return profiles[0]
    return None
