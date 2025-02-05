#!/usr/bin/env python
"""
run_all_tests.py

This script discovers and runs all unit tests in the "tests" directory.
You can run it from the project root as:

    python run_all_tests.py

It will execute all tests (for example, those defined in tests/test_suite.py).
"""

import os
import sys
import unittest

if __name__ == "__main__":
    # Ensure that the tests directory is in the Python path
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")
    if TESTS_DIR not in sys.path:
        sys.path.insert(0, TESTS_DIR)

    # Discover and run all tests in the "tests" directory
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=TESTS_DIR)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    # Exit with an error code if any tests failed
    sys.exit(not result.wasSuccessful())
