"""Developer tools shipped inside the package.

Unlike the repo's ``tools/`` directory (sdist only), this package is in the
wheel, so a ``pip install texastoast`` on the Pi gets the tools too — the
``texastoast-bench`` console script lives here.

Nothing in this package may import tkinter at module import time; the tools
import it inside their entry functions so the package stays importable on
headless systems.
"""
