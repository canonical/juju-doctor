import json

import pytest
from typer.testing import CliRunner

from juju_doctor.main import app
from juju_doctor.probes import AssertionStatus


def test_check_multiple_artifacts():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a failing file probe
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "file://tests/resources/probes/python/passing.py",
        "--status=tests/resources/artifacts/status.yaml",
        "--bundle=tests/resources/artifacts/bundle.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND only the status and bundle functions pass, since they were supplied an artifact
    assert json.loads(result.stdout)["failed"] == 1
    assert json.loads(result.stdout)["passed"] == 2


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
    # AND only the status function passes, since it was supplied an artifact
    assert json.loads(result.stdout)["failed"] == 5
    assert json.loads(result.stdout)["passed"] == 1


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


def test_duplicate_file_probes_are_excluded():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is supplied with 2 duplicate file probes
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "file://tests/resources/probes/python/failing.py",
        "--probe",
        "file://tests/resources/probes/python/failing.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the second Probe overwrote the first, i.e. only 1 exists
    failing = json.loads(result.stdout)["Results"]["children"][0][AssertionStatus.FAIL.value]
    assert len(failing["children"]) == 1


@pytest.mark.github
def test_check_gh_probe_at_branch():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command executes a GitHub probe on the main branch
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


@pytest.mark.github
def test_duplicate_gh_probes_are_excluded():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is supplied with 2 duplicate file probes
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "github://canonical/juju-doctor//tests/resources/probes/python/failing.py?main",
        "--probe",
        "github://canonical/juju-doctor//tests/resources/probes/python/failing.py?main",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the second Probe overwrote the first, i.e. only 1 exists
    failing = json.loads(result.stdout)["Results"]["children"][0][AssertionStatus.FAIL.value]
    assert len(failing["children"]) == 1
