from arc import keyboard


def test_pages():
    for page in keyboard.PAGES:
        assert len(keyboard.keys(page)) == 30
        assert all(len(row) == keyboard.COLUMNS for row in keyboard.PAGES[page])
    assert keyboard.keys("upper")[0] == "A"
    assert ":" in keyboard.keys("symbols") and "/" in keyboard.keys("symbols")
    assert keyboard.shifted("lower") == "upper" and keyboard.shifted("upper") == "lower"
    assert keyboard.shifted("symbols") == "lower"
    assert keyboard.switched("lower") == "symbols" and keyboard.switched("symbols") == "lower"
    assert keyboard.START["code"] == "upper"


def test_edit_and_show():
    t = ""
    for k in ["1", "9", "2", ".", keyboard.SPACE, "x"]:
        t = keyboard.edit(t, k)
    assert t == "192. x"
    assert keyboard.edit(t, keyboard.DELETE) == "192. "
    assert keyboard.edit(t, keyboard.CLEAR) == ""
    assert keyboard.edit("ab", "c", limit=2) == "ab"
    assert keyboard.edit("ab", "multi") == "ab"
    assert keyboard.shown("secret", hidden=True) == "•" * 6
    assert keyboard.shown("abc") == "abc"
