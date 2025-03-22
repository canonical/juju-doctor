import tempfile
from pathlib import Path

from fetcher import Fetcher


def test_parse_file():
    # GIVEN a python probe file
    probe_uri = "file://tests/resources/probes/python/failing.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Fetcher.fetch_probes(destination=Path(tmpdir), uri=probe_uri)
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.uri == probe_uri
        assert probe.name == "tests_resources_probes_python_failing.py"
        assert probe.original_path == Path("tests/resources/probes/python/failing.py")
        assert probe.path == Path(tmpdir) / probe.name


def test_parse_dir():
    # GIVEN a python probe dir
    probe_uri = "file://tests/resources/probes/python"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Fetcher.fetch_probes(destination=Path(tmpdir), uri=probe_uri)
        # THEN 2 probes exist
        assert len(probes) == 2
        passing_probe = [probe for probe in probes if "passing.py" in probe.name][0]
        failing_probe = [probe for probe in probes if "failing.py" in probe.name][0]
        # AND the Probe was correctly parsed as passing
        probes_path = "tests/resources/probes/python"
        assert passing_probe.uri == probe_uri
        assert passing_probe.name == "tests_resources_probes_python/passing.py"
        assert passing_probe.original_path == Path(probes_path)
        assert passing_probe.path == Path(tmpdir) / passing_probe.name
        # AND the Probe was correctly parsed as failing
        assert failing_probe.uri == probe_uri
        assert failing_probe.name == "tests_resources_probes_python/failing.py"
        assert failing_probe.original_path == Path(probes_path)
        assert failing_probe.path == Path(tmpdir) / failing_probe.name
