import json

import pytest
from main import app
from typer.testing import CliRunner


@pytest.mark.parametrize("category", ["status", "bundle", "show-unit"])
def test_check_gh_probe_fails(category):
    runner = CliRunner()
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        f"github://canonical/juju-doctor//tests/resources/{category}/failing.py",
        f"--{category}",
        f"tests/resources/{category}/{category}.yaml",
    ]
    result = runner.invoke(app, test_args)
    assert result.exit_code == 0
    check = json.loads(result.stdout)
    assert check == {"failed": 1, "passed": 0}


@pytest.mark.parametrize("category", ["status", "bundle", "show-unit"])
def test_check_gh_probe_raises_category(category):
    runner = CliRunner()
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        f"github://canonical/juju-doctor//tests/resources/{category}/failing.py",
    ]
    result = runner.invoke(app, test_args)
    assert result.exit_code == 1
    assert str(result.exception) == f"You didn't supply {category} input or a live model."
