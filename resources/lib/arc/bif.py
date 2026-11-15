"""BIF files: Arc's timeline thumbnails as one file (GET /items/{id}/trickplay/{file}/bif), the
format Roku's player uses. A 64-byte header (magic, version, frame count, the timestamp unit in
ms), then an index of (timestamp, offset) pairs ending with 0xffffffff, then the JPEGs. Plain
Python, tested with a made-up file."""

import struct

MAGIC = b"\x89BIF\r\n\x1a\n"


class BIF(object):
    def __init__(self, data):
        if len(data) < 64 or data[:8] != MAGIC:
            raise ValueError("not a BIF file")
        _version, count, unit = struct.unpack_from("<III", data, 8)
        unit = unit or 1000
        self.data = data
        self.frames = []   # (start_ms, offset, end)
        for i in range(count):
            ts, off = struct.unpack_from("<II", data, 64 + 8 * i)
            _next_ts, end = struct.unpack_from("<II", data, 64 + 8 * (i + 1))
            if ts == 0xFFFFFFFF or end <= off or end > len(data):
                break
            self.frames.append((ts * unit, off, end))

    def __len__(self):
        return len(self.frames)

    def index_at(self, position_ms):
        """The frame showing at `position_ms`: the last one starting at or before it."""
        at = 0
        for i, (start, _, _) in enumerate(self.frames):
            if start <= position_ms:
                at = i
            else:
                break
        return at

    def frame(self, i):
        """The JPEG bytes of frame `i`, or None."""
        if not 0 <= i < len(self.frames):
            return None
        _, off, end = self.frames[i]
        return self.data[off:end]


def make(jpegs, interval_ms=10000):
    """A BIF of `jpegs` at `interval_ms` (for the tests)."""
    head = MAGIC + struct.pack("<III", 0, len(jpegs), 1000) + b"\0" * 44
    offset = 64 + 8 * (len(jpegs) + 1)
    index, body = b"", b""
    for i, jpg in enumerate(jpegs):
        index += struct.pack("<II", i * interval_ms // 1000, offset + len(body))
        body += jpg
    index += struct.pack("<II", 0xFFFFFFFF, offset + len(body))
    return head + index + body
