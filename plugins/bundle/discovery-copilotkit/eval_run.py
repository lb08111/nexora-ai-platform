#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI: run the discovery-copilotkit eval and print a JSON report.

Run with::

    python plugins/bundle/discovery-copilotkit/eval_run.py

Exit code is 0 when all thresholds pass and 1 otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_session import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
