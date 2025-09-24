import json
import os
import re

import pytest
from typer.testing import CliRunner

from juju_doctor.main import app


def test_no_probes():
    # GIVEN no probes were provided
    test_args = [
        "check",
        "--format=json",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = CliRunner().invoke(app, test_args)
    # THEN the command fails
    assert result.exit_code == 2
    # AND the command fails
    assert "No probes were specified" in result.output


def test_no_artifacts():
    # GIVEN no artifacts were provided
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/mixed.py",
    ]
    # WHEN `juju-doctor check` is executed
    result = CliRunner().invoke(app, test_args)
    # THEN the command fails
    assert result.exit_code == 2
    # AND the command fails
    assert "No artifacts were specified" in result.output


def test_check_multiple_artifacts():
    # GIVEN a file probe, missing the Status artifact
    # AND all artifacts are provided
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/mixed.py",
        "--bundle=tests/resources/artifacts/bundle.yaml",
        "--show-unit=tests/resources/artifacts/show-unit.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND only the functions with artifacts are executed
    assert json.loads(result.stdout)["passed"] == 0
    assert json.loads(result.stdout)["failed"] == 1


def test_check_multiple_probes():
    # GIVEN multiple probes and a Status artifact
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/passing.py",
        "--probe=file://tests/resources/probes/python/failing.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND only the status functions are executed
    assert json.loads(result.stdout)["failed"] == 1
    assert json.loads(result.stdout)["passed"] == 1


def test_check_unused_probe_artifacts(caplog):
    # GIVEN a probe is missing the Status artifact
    # AND this artifact is provided
    test_args = [
        "check",
        "--probe=file://tests/resources/probes/python/mixed.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    with caplog.at_level("WARNING"):
        result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the user is warned of their mistake
    assert re.search(r"status.*not used", caplog.text)


def test_check_unused_builtin_artifacts(caplog):
    # GIVEN a RuleSet probe does not use the Show-unit artifact
    # AND this artifact is provided
    test_args = [
        "check",
        "--probe=file://tests/resources/probes/ruleset/builtins.yaml",
        "--show-unit=tests/resources/artifacts/show-unit.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    with caplog.at_level("WARNING"):
        result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the user is warned of their mistake
    assert re.search(r"show_unit.*not used", caplog.text)


def test_check_probe_missing_required_artifacts(caplog):
    # GIVEN a probe requires all artifacts
    test_args = [
        "check",
        "--probe=file://tests/resources/probes/python/passing.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    with caplog.at_level("WARNING"):
        result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the user is warned of their mistake
    assert re.search(r"No.*bundle.*provided", caplog.text)
    assert re.search(r"No.*show_unit.*provided", caplog.text)


def test_check_builtin_missing_required_artifacts(caplog):
    # GIVEN a RuleSet probe requires Status and Bundle artifacts
    test_args = [
        "check",
        "--probe=file://tests/resources/probes/ruleset/builtins.yaml",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    with caplog.at_level("WARNING"):
        result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the user is warned of their mistake
    assert re.search(r"No.*bundle.*provided", caplog.text)


def test_check_returns_valid_json():
    # GIVEN any probe
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/ruleset/all.yaml",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the result is valid JSON
    try:
        json.loads(result.output)
    except json.JSONDecodeError as e:
        assert False, f"Output is not valid JSON: {e}\nOutput:\n{result.output}"


def test_duplicate_file_probes_are_excluded():
    # GIVEN 2 duplicate file probes
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/failing.py",
        "--probe=file://tests/resources/probes/python/failing.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the second Probe overwrote the first, i.e. only 1 exists
    failing = json.loads(result.stdout)["Results"]["children"]
    assert len(failing) == 1


def test_duplicate_file_probes_warning(caplog):
    # GIVEN 2 duplicate file probes
    test_args = [
        "check",
        "--probe=file://tests/resources/probes/python/failing.py",
        "--probe=file://tests/resources/probes/python/failing.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    with caplog.at_level("WARNING"):
        result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the user is warned of their mistake
    assert "Duplicate probe arg" in caplog.text


@pytest.mark.github
def test_check_gh_probe_at_branch():
    # GIVEN a GitHub probe on the main branch
    test_args = [
        "check",
        "--format=json",
        "--probe=github://canonical/juju-doctor//tests/resources/probes/python/failing.py?main",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the Probe was correctly executed
    assert json.loads(result.stdout)["failed"] == 1
    assert json.loads(result.stdout)["passed"] == 0


@pytest.mark.github
def test_duplicate_gh_probes_are_excluded():
    # GIVEN two GitHub probes
    test_args = [
        "check",
        "--format=json",
        "--probe=github://canonical/juju-doctor//tests/resources/probes/python/failing.py?main",
        "--probe=github://canonical/juju-doctor//tests/resources/probes/python/failing.py?main",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the second Probe overwrote the first, i.e. only 1 exists
    failing = json.loads(result.stdout)["Results"]["children"]
    assert len(failing) == 1


def test_check_not_from_repo_root(tmp_path):
    # GIVEN the current working directory is not the repo root
    orig = os.getcwd()
    os.chdir(str(tmp_path))
    test_args = [
        "check",
        "--format",
        "json",
        f"--probe=file://{orig}/tests/resources/probes/ruleset/builtins.yaml",
        f"--status={orig}/tests/resources/artifacts/status.yaml",
        f"--bundle={orig}/tests/resources/artifacts/bundle.yaml",
    ]
    # WHEN juju-doctor check is executed on builtins
    # because builtins are not loaded from disk, rather they are loaded from the package
    result = CliRunner().invoke(app, test_args)
    # THEN they are all found
    assert json.loads(result.stdout)["failed"] == 0
    assert json.loads(result.stdout)["passed"] == 3
