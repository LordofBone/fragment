import os

import pytest

if __name__ == "__main__":
    # Create a reports directory if it doesn’t exist
    reports_dir = os.path.join(os.path.dirname(__file__), "test_reports")
    os.makedirs(reports_dir, exist_ok=True)

    # Run pytest with an HTML report
    pytest.main(["--html=test_reports/report.html", "--self-contained-html"])
