import tempfile
from pathlib import Path

import pytest
from fetcher import Fetcher


# TODO Find a good dir structure or make the probe paths dynamic (lot of work to update paths on changes)
def test_ruleset_calls_scriptlet_file():
    # TODO We should cover the probe naming in a test for:
    #   1. nested (once and twice) in ruleset
    #   2. direct python probe
    #   Then never check the naming semantics again in tests.

    # GIVEN a ruleset probe file calls scriptlets
    probe_uri = "file://tests/resources/probes/ruleset/scriptlet.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Fetcher.fetch_probes(destination=Path(tmpdir), uri=probe_uri)
        # THEN 2 python probes exist
        assert len(probes) == 2
        passing_probe = [probe for probe in probes if "passing.py" in probe.name][0]
        failing_probe = [probe for probe in probes if "failing.py" in probe.name][0]
        # AND the Probe was correctly parsed as passing
        probes_path = "tests/resources/probes/python"
        assert passing_probe.uri == f"file://{probes_path}/passing.py"
        assert passing_probe.name == "tests_resources_probes_python_passing.py"
        assert passing_probe.original_path == Path(f"{probes_path}/passing.py")
        assert passing_probe.path == Path(tmpdir) / passing_probe.name
        # AND the Probe was correctly parsed as failing
        assert failing_probe.uri == f"file://{probes_path}/failing.py"
        assert failing_probe.name == "tests_resources_probes_python_failing.py"
        assert failing_probe.original_path == Path(f"{probes_path}/failing.py")
        assert failing_probe.path == Path(tmpdir) / failing_probe.name


def test_ruleset_calls_scriptlet_dir():
    # GIVEN a ruleset probe file calls a directory of scriptlets
    probe_uri = "file://tests/resources/probes/ruleset/dir.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Fetcher.fetch_probes(destination=Path(tmpdir), uri=probe_uri)
        # THEN probes are found
        assert len(probes) > 0


@pytest.mark.parametrize("extension", [("yaml"), ("YAML"), ("yml"), ("YML")])
def test_ruleset_extensions(extension):
    # GIVEN a ruleset probe file
    probe_uri = f"file://tests/resources/probes/ruleset/extensions/scriptlet.{extension}"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Fetcher.fetch_probes(destination=Path(tmpdir), uri=probe_uri)
        # THEN probes are found
        assert len(probes) > 0
