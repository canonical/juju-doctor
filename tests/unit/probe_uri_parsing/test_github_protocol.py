import tempfile
from pathlib import Path

from juju_doctor.probes import Probe


def test_parse_file():
    # GIVEN a probe file specified in a Github remote on the main branch
    path_str = "tests/resources/probes/python/failing.py"
    probe_url = f"github://canonical/juju-doctor//{path_str}?main"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Probe.from_url(url=probe_url, probes_root=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.name == "canonical_juju-doctor__tests_resources_probes_python_failing.py"
        assert probe.path == Path(tmpdir) / probe.name


def test_parse_dir():
    # GIVEN a probe directory specified in a Github remote on the main branch
    path_str = "tests/resources/probes/python"
    probe_url = f"github://canonical/juju-doctor//{path_str}?main"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Probe.from_url(url=probe_url, probes_root=Path(tmpdir))
        # THEN 2 probe exists
        assert len(probes) == 2
        passing_probe = [probe for probe in probes if "passing.py" in probe.name][0]
        failing_probe = [probe for probe in probes if "failing.py" in probe.name][0]
        # AND the Probe was correctly parsed as passing
        assert passing_probe.name == "canonical_juju-doctor__tests_resources_probes_python/passing.py"
        assert passing_probe.path == Path(tmpdir) / passing_probe.name
        # AND the Probe was correctly parsed as failing
        assert failing_probe.name == "canonical_juju-doctor__tests_resources_probes_python/failing.py"
        assert failing_probe.path == Path(tmpdir) / failing_probe.name
