"""Arc for Kodi: the full-screen client. Entry point — hands off to resources/lib/kodi/app.py."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "lib"))


def main():
    from kodi.app import App
    App().run()


if __name__ == "__main__":
    main()
