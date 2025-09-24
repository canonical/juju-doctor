import tempfile
from pathlib import Path

from juju_doctor.probes import Probe


def test_parse_python_file():
    # GIVEN a local Python probe file
    path_str = "tests/resources/probes/python/failing.py"
    probe_url = f"file://{path_str}"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(probe_url, Path(tmpdir))
        probes = probe_tree.probes
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.name == "tests_resources_probes_python_failing.py"
        assert probe.path == Path(tmpdir) / probe.name


def test_parse_dir():
    # GIVEN a local probe file with the file protocol
    path_str = "tests/resources/probes/python"
    probe_url = f"file://{path_str}"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(probe_url, Path(tmpdir))
        probes = probe_tree.probes
        # THEN 3 probes exist
        assert len(probes) == 3
        passing_probe = [probe for probe in probes if "passing.py" in probe.name][0]
        failing_probe = [probe for probe in probes if "failing.py" in probe.name][0]
        # AND the Probe was correctly parsed as passing
        assert passing_probe.name == "tests_resources_probes_python/passing.py"
        assert passing_probe.path == Path(tmpdir) / passing_probe.name
        # AND the Probe was correctly parsed as failing
        assert failing_probe.name == "tests_resources_probes_python/failing.py"
        assert failing_probe.path == Path(tmpdir) / failing_probe.name


def test_parse_ruleset_file():
    # GIVEN a local RuleSet probe file
    path_str = "tests/resources/probes/ruleset/scriptlets.yaml"
    probe_url = f"file://{path_str}"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(probe_url, Path(tmpdir))
        probes = probe_tree.probes
        # THEN probes are found
        assert len(probes) > 0
        # AND the Probe does not leak information about which RuleSet called it
        for probe in probes:
            assert all("ruleset" not in value for value in [probe.name, str(probe.path)])
