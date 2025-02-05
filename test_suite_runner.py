#!/usr/bin/env python
"""
run_all_tests.py

This script runs all Pytest tests found under the "tests" folder and generates an
HTML report using the "pytest-html-reporter" plugin.

Usage:
  python run_all_tests.py
"""

import os

import pytest

if __name__ == "__main__":
    # Create a local "report" directory (you can change the name if needed)
    report_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(report_dir, exist_ok=True)

    # Define the path for the final HTML report
    report_path = os.path.join(report_dir, "report.html")

    # Run pytest with custom arguments:
    # 1) We point Pytest to the "tests" folder
    # 2) We pass --html-report=YOUR_REPORT_PATH to use the "pytest-html-reporter" plugin
    #    to generate an HTML report at "report/report.html"
    exit_code = pytest.main([
        "./tests",  # folder containing tests
        f"--html-report={report_path}",
    ])

    # Exit code from pytest will be 0 if all tests pass, 1 (or other) on failures.
    # You could further act on this exit_code if you want.
    exit(exit_code)
