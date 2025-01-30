import json

import pytest
from main import app
from typer.testing import CliRunner


@pytest.mark.parametrize("category", ["status", "bundle", "show-unit"])
def test_check_file_probe_fails(category):
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a failing file probe
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        f"file://tests/resources/{category}/failing.py",
        f"--{category}",
        f"tests/resources/{category}/{category}.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    check = json.loads(result.stdout)
    # AND the Probe was correctly executed
    assert check == {"failed": 1, "passed": 0}


@pytest.mark.parametrize("category", ["status", "bundle", "show-unit"])
def test_check_file_probe_raises_category(category):
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed for a file probe without stdin
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        f"github://canonical/juju-doctor//tests/resources/{category}/failing.py",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command fails
    assert result.exit_code == 1
    # AND the correct category was mentioned
    assert str(result.exception) == f"You didn't supply {category} input or a live model."
