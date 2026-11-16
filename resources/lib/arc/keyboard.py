"""Arc's on-screen keyboard for typing a server address, a password or a Watch Together code, in
place of Kodi's own keyboard: a grid of keys ten across, in three pages (small letters, capitals,
digits and symbols), and a row under it: Shift, the page switch, Space, Delete, Clear and Done.
Plain Python: kodi/windows/keyboard.py draws it."""

COLUMNS = 10
MAX_LENGTH = 200

# The pages, row by row. The small letters' last row has what an address or an email needs most.
PAGES = {
    "lower": ["abcdefghij", "klmnopqrst", "uvwxyz.-_@"],
    "upper": ["ABCDEFGHIJ", "KLMNOPQRST", "UVWXYZ.-_@"],
    "symbols": ["1234567890", "./:-_@?#&=", "!$%*+~,;()"],
}

# What each kind of text starts on: an address in small letters, a code (capitals and digits,
# as Arc makes them) in capitals.
START = {"address": "lower", "password": "lower", "code": "upper"}

SPACE, DELETE, CLEAR = "space", "delete", "clear"
HIDDEN = "•"   # a password shows as dots


def keys(page):
    """The page's keys, left to right, top to bottom."""
    return [k for row in PAGES.get(page, PAGES["lower"]) for k in row]


def shifted(page):
    """Shift: small letters and capitals swap; from the symbols, back to small letters."""
    return "upper" if page == "lower" else "lower"


def switched(page):
    """The page switch (123 / ABC): symbols, or back to letters."""
    return "lower" if page == "symbols" else "symbols"


def edit(text, key, limit=MAX_LENGTH):
    """The text after a key: a character, SPACE, DELETE or CLEAR."""
    text = text or ""
    if key == CLEAR:
        return ""
    if key == DELETE:
        return text[:-1]
    if key == SPACE:
        key = " "
    if isinstance(key, str) and len(key) == 1 and len(text) < limit:
        return text + key
    return text


def shown(text, hidden=False):
    """What the text field shows: the text, or a dot per character for a password."""
    text = text or ""
    return HIDDEN * len(text) if hidden else text
