#!/usr/bin/env python3
"""Repo-checkout shim for the controller bench.

The bench lives in the package (``texastoast/devtools/bench.py``) so that a
plain ``pip install texastoast`` gets it as the ``texastoast-bench`` console
script. This file exists so a checkout can run it the same way the tile
editor is run::

    python tools/controller_bench.py --sim
"""

import sys
from pathlib import Path

# A script's sys.path[0] is tools/, not the checkout root — without this the
# import would silently pick up whatever texastoast is pip-installed instead
# of the code sitting next to this file.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from texastoast.devtools.bench import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
