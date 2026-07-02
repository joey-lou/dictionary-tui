#!/usr/bin/env python3
"""Build Webster 1913 EN pack. Entrypoint: delegates to webster1913 package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from webster1913.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
