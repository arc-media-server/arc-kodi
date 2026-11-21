"""Small, window-local navigation memory; no Kodi imports or persistent settings."""


class FocusMemory(object):
    def __init__(self):
        self.active = None
        self.positions = {}
        self.rows = {}

    def enter(self, control, position, count):
        changed = control != self.active
        self.active = control
        if count <= 0:
            return position
        return min(max(self.positions.get(control, position) if changed else position, 0), count - 1)

    def vertical(self, control, position, count, columns):
        previous = self.positions.get(control)
        if previous is None or columns <= 0 or count <= 0:
            return position
        row = position // columns
        if row == previous // columns:
            return position
        remembered = self.rows.get((control, row), row * columns + previous % columns)
        return min(max(remembered, row * columns), min((row + 1) * columns, count) - 1)

    def remember(self, control, position, columns=0):
        if position < 0:
            return
        self.positions[control] = position
        if columns > 0:
            self.rows[(control, position // columns)] = position
