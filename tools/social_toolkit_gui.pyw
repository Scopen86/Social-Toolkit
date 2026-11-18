"""Windows no-console launcher for the Social Toolkit GUI.

Double-click this file (or use ``run_gui.vbs`` in the project root) to start
the app with pythonw.exe, so no terminal window is shown.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.social_toolkit_gui import main

if __name__ == "__main__":
    main()
