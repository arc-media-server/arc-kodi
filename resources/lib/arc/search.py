"""Search, as the Apple app's: what's typed on Arc's on-screen keyboard (or into the search box), and the
answer in rows: Movies, TV Shows, Episodes, Collections, People and Genres, each only when it has
matches. Arc forgives accents, case and small typos; the app searches once typing pauses.

Plain Python: the Kodi window (kodi/windows/search.py) draws the keys and rows."""

# The keyboard: letters, then digits, six keys across (as PM4K's grid); Space, Delete and Clear
# sit under it.
LETTERS = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "1234567890"
KEYS = list(LETTERS + DIGITS)
COLUMNS = 6

SPACE, DELETE, CLEAR = "space", "delete", "clear"

MAX_LENGTH = 100

# Rows in the Apple app's order, with the kind of card each shows. "top" is Top Results: movies
# and shows together, alternating, each keeping Arc's best-first order (as Android and Apple TV).
ROWS = [("top", "poster"), ("episodes", "thumb"),
        ("collections", "poster"), ("people", "face"), ("genres", "pill")]

def edit(text, key):
    """The text after a key: a character, SPACE, DELETE or CLEAR."""
    text = text or ""
    if key == CLEAR:
        return ""
    if key == DELETE:
        return text[:-1]
    if key == SPACE:
        # No leading or doubled spaces: they'd search for the same thing.
        return text + " " if text and not text.endswith(" ") and len(text) < MAX_LENGTH else text
    if isinstance(key, str) and len(key) == 1 and len(text) < MAX_LENGTH:
        return text + key
    return text


def query(text):
    """What's sent to Arc: the text without spaces at either end; None when nothing's typed."""
    q = (text or "").strip()
    return q or None


def rows(data):
    """The answer as [(kind, style, entries)], only the rows with matches, in ROWS order."""
    data = data if isinstance(data, dict) else {}
    out = []
    for kind, style in ROWS:
        if kind == "top":
            movies, shows = data.get("movies") or [], data.get("shows") or []
            mixed = [e for pair in zip(movies, shows) for e in pair]
            longer = movies if len(movies) > len(shows) else shows
            entries = [e for e in mixed + longer[min(len(movies), len(shows)):] if isinstance(e, dict)]
        else:
            entries = [e for e in data.get(kind) or [] if isinstance(e, dict)]
        if kind == "people":
            entries = [e for e in entries if e.get("id") and e.get("name")]
        elif kind == "genres":
            entries = [e for e in entries if e.get("name") and e.get("library_id")]
        elif kind == "collections":
            entries = [e for e in entries if e.get("id")]
        else:
            entries = [e for e in entries if e.get("id")]
        if entries:
            out.append((kind, style, entries))
    return out


def known_for(person):
    """What a person is known for, as a heading ("actor" -> "Actor")."""
    text = (person.get("known_for") or "").strip()
    return text[:1].upper() + text[1:]


def initials(name):
    return "".join(w[:1] for w in (name or "").split()[:2]).upper()


def collection_image(collection):
    """A collection's picture: its own primary image when Arc has one, otherwise the route that
    makes one from its titles."""
    images = collection.get("images") or {}
    return images.get("primary") or "/api/collections/%s/images/primary" % collection.get("id")
