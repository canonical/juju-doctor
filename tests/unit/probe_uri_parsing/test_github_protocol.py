import tempfile
from pathlib import Path

from juju_doctor.probes import Probe


def test_parse_file():
    # GIVEN a python probe file specified in a Github remote on the main branch
    # FIXME: switch probe back to main branch
    probe_uri = "github://canonical/juju-doctor//tests/resources/probes/python/failing.py?feat/ruleset"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Probe.from_uri(uri=probe_uri, probes_root=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.uri == probe_uri
        assert probe.name == "canonical_juju-doctor__tests_resources_probes_python_failing.py"
        assert probe.original_path == Path("tests/resources/probes/python/failing.py")
        assert probe.path == Path(tmpdir) / probe.name


def test_parse_dir():
    # GIVEN a python probe directory specified in a Github remote on the main branch
    # FIXME: switch probe back to main branch
    probe_uri = "github://canonical/juju-doctor//tests/resources/probes/python?feat/ruleset"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Probe.from_uri(uri=probe_uri, probes_root=Path(tmpdir))
        # THEN 2 probe exists
        assert len(probes) == 2
        passing_probe = [probe for probe in probes if "passing.py" in probe.name][0]
        failing_probe = [probe for probe in probes if "failing.py" in probe.name][0]
        # AND the Probe was correctly parsed as passing
        assert passing_probe.uri == probe_uri
        assert passing_probe.name == "canonical_juju-doctor__tests_resources_probes_python/passing.py"
        assert passing_probe.original_path == Path("tests/resources/probes/python")
        assert passing_probe.path == Path(tmpdir) / passing_probe.name
        # AND the Probe was correctly parsed as failing
        assert failing_probe.uri == probe_uri
        assert failing_probe.name == "canonical_juju-doctor__tests_resources_probes_python/failing.py"
        assert failing_probe.original_path == Path("tests/resources/probes/python")
        assert failing_probe.path == Path(tmpdir) / failing_probe.name
