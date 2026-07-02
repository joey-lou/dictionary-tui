#!/usr/bin/env python3
"""Build Xinhua ZH-ZH pack. Entrypoint: delegates to xinhua package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from xinhua.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
