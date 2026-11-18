"""Compatibility entry point for the existing Streamlit review application."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend" / "legacy"))
sys.path.insert(0, str(ROOT / "backend" / "app"))
runpy.run_path(str(ROOT / "backend" / "legacy" / "main.py"), run_name="__main__")
