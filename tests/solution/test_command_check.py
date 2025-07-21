import json
import re

import pytest
from typer.testing import CliRunner

from juju_doctor.main import app
from juju_doctor.probes import ROOT_NODE_TAG, AssertionStatus


def test_no_probes():
    # GIVEN no probes were supplied
    # WHEN `juju-doctor check` is executed
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command fails
    assert result.exit_code == 2
    # AND the command fails
    assert "No probes were specified" in result.output


def test_no_artifacts():
    # GIVEN no artifacts were supplied
    # WHEN `juju-doctor check` is executed
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/mixed.py",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command fails
    assert result.exit_code == 2
    # AND the command fails
    assert "No artifacts were specified" in result.output


def test_check_multiple_artifacts(caplog):
    # GIVEN a file probe, missing the Status artifact
    # AND all artifacts are supplied
    # WHEN `juju-doctor check` is executed
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/mixed.py",
        "--status=tests/resources/artifacts/status.yaml",
        "--bundle=tests/resources/artifacts/bundle.yaml",
        "--show-unit=tests/resources/artifacts/show-unit.yaml",
    ]
    with caplog.at_level("WARNING"):
        result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND only the functions with artifacts are executed
    assert json.loads(result.stdout)["passed"] == 1
    assert json.loads(result.stdout)["failed"] == 1
    # AND the user is warned of their mistake
    assert re.search(r"status.*not used", caplog.text)


def test_check_multiple_file_probes(caplog):
    # GIVEN multiple file probes and a Status artifact
    # WHEN `juju-doctor check` is executed
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/passing.py",
        "--probe=file://tests/resources/probes/python/failing.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    with caplog.at_level("WARNING"):
        result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND only the status functions are executed
    assert json.loads(result.stdout)["failed"] == 1
    assert json.loads(result.stdout)["passed"] == 1
    # AND the user is warned of their mistake
    assert re.search(r"No 'bundle'.*provided", caplog.text)
    assert re.search(r"No 'show_unit'.*provided", caplog.text)


def test_check_returns_valid_json():
    # GIVEN any probe
    # WHEN `juju-doctor check` is executed
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/ruleset/all.yaml",
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


def test_duplicate_file_probes_are_excluded(caplog):
    # GIVEN 2 duplicate file probes
    # WHEN `juju-doctor check` is executed
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/failing.py",
        "--probe=file://tests/resources/probes/python/failing.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    with caplog.at_level("WARNING"):
        result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the second Probe overwrote the first, i.e. only 1 exists
    failing = json.loads(result.stdout)["Results"]["children"][0][AssertionStatus.FAIL.value]
    assert len(failing["children"]) == 1
    # AND the user is warned of their mistake
    assert re.search(r"Duplicate probe arg", caplog.text)


@pytest.mark.github
def test_check_gh_probe_at_branch():
    # GIVEN a GitHub probe on the main branch
    # WHEN `juju-doctor check` is executed
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--probe=github://canonical/juju-doctor//tests/resources/probes/python/failing.py?main",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the Probe was correctly executed
    assert json.loads(result.stdout)["failed"] == 1
    assert json.loads(result.stdout)["passed"] == 0


@pytest.mark.github
def test_duplicate_gh_probes_are_excluded():
    # GIVEN two GitHub probes
    # WHEN `juju-doctor check` is executed
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--probe=github://canonical/juju-doctor//tests/resources/probes/python/failing.py?main",
        "--probe=github://canonical/juju-doctor//tests/resources/probes/python/failing.py?main",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the second Probe overwrote the first, i.e. only 1 exists
    failing = json.loads(result.stdout)["Results"]["children"][0][AssertionStatus.FAIL.value]
    assert len(failing["children"]) == 1


# TODO These tests are not isolated: check_result = json.loads(result.output)
# has context from previous tests
def test_check_groups_by_parent():
    # GIVEN multiple Ruleset probes
    # WHEN `juju-doctor check` is executed
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/ruleset/dir.yaml",
        "--probe=file://tests/resources/probes/ruleset/scriptlet.yaml",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    check_result = json.loads(result.output)
    # AND there is one parent node (with children nodes) per Ruleset
    probes = check_result[ROOT_NODE_TAG]["children"]
    assert any(
        " - dir" in key and len(probe.values()) > 0
        for probe in probes
        if isinstance(probe, dict)
        for key in probe.keys()
    )
    assert any(
        " - scriptlet" in key and len(probe.values()) > 0
        for probe in probes
        if isinstance(probe, dict)
        for key in probe.keys()
    )
