import json

import pytest
from main import app
from typer.testing import CliRunner


def test_check_gh_probe_fails():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a failing GitHub probe
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "file://tests/resources/failing.py",  # FIXME: change this to github:// after the PR is merged
        "--status",
        "tests/resources/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the Probe was correctly executed
    check = json.loads(result.stdout)
    assert check == {"failed": 1, "passed": 0}
