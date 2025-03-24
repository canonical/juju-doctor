import tempfile
from pathlib import Path

from juju_doctor.probes import Probe


def test_parse_file():
    # GIVEN a local probe file
    probe_uri = "file://tests/resources/failing.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Probe.from_uri(uri=probe_uri, probes_root=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.uri == probe_uri
        assert probe.name == "tests_resources_failing.py"
        assert probe.original_path == Path("tests/resources/failing.py")
        assert probe.path == Path(tmpdir) / probe.name


def test_parse_dir():
    # GIVEN a local probe file with the file protocol
    probe_uri = "file://tests/resources"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Probe.from_uri(uri=probe_uri, probes_root=Path(tmpdir))
        # THEN 2 probes exist
        assert len(probes) == 2
        passing_probe = [probe for probe in probes if "passing.py" in probe.name][0]
        failing_probe = [probe for probe in probes if "failing.py" in probe.name][0]
        # AND the Probe was correctly parsed as passing
        assert passing_probe.uri == probe_uri
        assert passing_probe.name == "tests_resources/passing.py"
        assert passing_probe.original_path == Path("tests/resources")
        assert passing_probe.path == Path(tmpdir) / passing_probe.name
        # AND the Probe was correctly parsed as failing
        assert failing_probe.uri == probe_uri
        assert failing_probe.name == "tests_resources/failing.py"
        assert failing_probe.original_path == Path("tests/resources")
        assert failing_probe.path == Path(tmpdir) / failing_probe.name
