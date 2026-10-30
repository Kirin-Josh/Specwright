import sys
from pathlib import Path

# The scorers import the API's schemas; run with: apps/api/.venv/Scripts/python -m pytest evals
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
