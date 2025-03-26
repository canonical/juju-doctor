import json

from main import app
from typer.testing import CliRunner


def test_check_file_probe_fails():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a failing file probe
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "file://tests/resources/probes/python/failing.py",
        "--status=tests/resources/artifacts/status.yaml",
        "--bundle=tests/resources/artifacts/bundle.yaml",
        "--show-unit=tests/resources/artifacts/show-unit.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    check = json.loads(result.stdout)
    # AND the Probe was correctly executed
    assert check == {"failed": 3, "passed": 0}


def test_check_gh_probe_fails():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a failing GitHub probe
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "github://canonical/juju-doctor//tests/resources/probes/python/failing.py?main",
        "--status",
        "tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the Probe was correctly executed
    check = json.loads(result.stdout)
    assert check == {"failed": 3, "passed": 0}


def test_check_raises_recursion_error():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a circular ruleset execution chain
    test_args = [
        "check",
        "--probe",
        "file://tests/resources/probes/ruleset/circular.yaml",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # THEN the command raises a RecursionError
    # with pytest.raises(RecursionError):  # FIXME Catch RecursionError natively with typer.CLIRunner
    runner.invoke(app, test_args, catch_exceptions=False)
