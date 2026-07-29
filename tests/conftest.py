import os
import sys

# src/ modules use flat imports (e.g. "from column_detector import ...")
# because main.py is normally run from inside src/ - see pytest.ini. This
# makes the same imports resolve the same way from tests/ without changing
# how the modules themselves import each other.
SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, os.path.abspath(SRC_DIR))
