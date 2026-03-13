from pathlib import Path
import runpy
import sys

PROJECT_DIR = Path(__file__).resolve().parent / "aerospec-agent"
sys.path.insert(0, str(PROJECT_DIR))
runpy.run_path(str(PROJECT_DIR / "app.py"), run_name="__main__")
