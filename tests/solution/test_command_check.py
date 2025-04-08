import json

from typer.testing import CliRunner

from juju_doctor.main import app


def test_check_multiple_artifacts():
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
    # AND the Probe was correctly executed
    assert json.loads(result.stdout)["failed"] == 3
    assert json.loads(result.stdout)["passed"] == 0


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
    assert json.loads(result.stdout)["failed"] == 3
    assert json.loads(result.stdout)["passed"] == 0


def test_check_multiple_file_probes():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a complex ruleset probe
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "file://tests/resources/probes/python/passing.py",
        "--probe",
        "file://tests/resources/probes/python/failing.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the Probe was correctly executed
    assert json.loads(result.stdout)["failed"] == 3
    assert json.loads(result.stdout)["passed"] == 3


def test_check_returns_valid_json():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a complex ruleset probe
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "file://tests/resources/probes/ruleset/all.yaml",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the result is valid JSON
    try:
        json.loads(result.output)
    except json.JSONDecodeError as e:
        assert False, f"Output is not valid JSON: {e}\nOutput:\n{result.output}"
