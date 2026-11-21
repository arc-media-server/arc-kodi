from arc.focus import FocusMemory


def test_same_item_after_leaving_a_section():
    memory = FocusMemory()
    memory.enter(100, 0, 26)
    memory.remember(100, 9, 6)
    memory.enter(120, -1, 0)
    assert memory.enter(100, 0, 26) == 9


def test_short_last_grid_row_does_not_lose_previous_column():
    memory = FocusMemory()
    memory.remember(100, 21, 6)
    down = memory.vertical(100, 25, 26, 6)
    assert down == 25
    memory.remember(100, down, 6)
    assert memory.vertical(100, 19, 26, 6) == 21


def test_each_grid_row_remembers_its_own_item():
    memory = FocusMemory()
    memory.remember(100, 9, 6)
    memory.remember(100, 16, 6)
    assert memory.vertical(100, 10, 26, 6) == 9
    memory.remember(100, 9, 6)
    assert memory.vertical(100, 15, 26, 6) == 16


def test_new_rows_keep_column_and_positions_clamp_after_removal():
    memory = FocusMemory()
    memory.remember(100, 4, 6)
    assert memory.vertical(100, 6, 26, 6) == 10
    memory.enter(120, -1, 0)
    assert memory.enter(100, 0, 3) == 2
    assert memory.enter(100, -1, 0) == -1


def test_horizontal_sections_keep_independent_positions():
    memory = FocusMemory()
    memory.remember(3001, 3)
    memory.remember(3002, 7)
    memory.enter(3002, 7, 10)
    assert memory.enter(3001, 0, 5) == 3
    assert memory.enter(3002, 0, 10) == 7
