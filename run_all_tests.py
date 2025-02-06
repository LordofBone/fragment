#!/usr/bin/env python
"""
run_all_tests.py

Run all tests (including GUI) under tests/, generating an HTML report.
Does not stop on fails or warnings.
"""

import os
import sys

import pytest

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)  # Ensure we are in the same directory as run_all_tests.py

    report_dir = os.path.join(script_dir, "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "report.html")

    # Use --maxfail=0 so that we do NOT stop on first fail,
    # and -v (verbose) for more detail
    exit_code = pytest.main([
        "--maxfail=0",
        "-v",
        "./tests",
        f"--html-report={report_path}",
    ])
    sys.exit(exit_code)
