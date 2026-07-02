#!/usr/bin/env python3
"""Build CC-CEDICT ZH-EN pack. Entrypoint: delegates to cedict package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cedict.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
