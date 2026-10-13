"""Pytest bootstrap: put flows/ and scrapers/ on sys.path and point the
dictionary loaders at the real data/dictionaries dir."""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "flows"))
sys.path.insert(0, os.path.join(REPO, "scrapers"))
os.environ.setdefault("DICTIONARY_DIR", os.path.join(REPO, "data", "dictionaries"))

