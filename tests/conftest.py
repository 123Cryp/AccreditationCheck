import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
_STUB_DIR = os.path.join(_THIS_DIR, "genlayer_stub")

# The offline genlayer_stub package must be importable as `genlayer` BEFORE
# contract.py's `from genlayer import *` runs, and the real project root
# must be importable so `import contract` finds contract.py.
for path in (_STUB_DIR, _PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)
