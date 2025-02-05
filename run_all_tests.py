import sys

import pytest

if __name__ == '__main__':
    # Call pytest with the tests directory and the html-report option.
    exit_code = pytest.main(["./tests", "--html-report=./reports/report.html"])
    sys.exit(exit_code)
