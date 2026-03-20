"""
backend/_paths.py
Shared sys.path setup for all backend modules.
Import this at the top of every backend file.

Usage:
    import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    sys.path.insert(0, os.path.join(sys.path[0], 'backend'))
"""
import sys
import os

def setup():
    here = os.path.abspath(__file__)
    root = os.path.dirname(os.path.dirname(here))          # cricketiq/
    backend = os.path.join(root, 'backend')                # cricketiq/backend/
    for p in [root, backend]:
        if p not in sys.path:
            sys.path.insert(0, p)

setup()
