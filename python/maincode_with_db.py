"""Legacy entrypoint (v2), kept so old instructions still work.

The application was refactored into the ``odinson`` package in v3. From the
repository root, run instead:

    python run.py            # live hardware (falls back to mock without Arduino)
    python run.py --mock     # synthetic data, no hardware needed

This file simply forwards to the new entrypoint.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run import main  # noqa: E402

if __name__ == "__main__":
    main()
