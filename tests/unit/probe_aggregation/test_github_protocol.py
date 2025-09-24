import tempfile
from pathlib import Path

import pytest

from juju_doctor.probes import Probe


@pytest.mark.github
def test_parse_file():
    # GIVEN a probe file specified in a Github remote on the main branch
    path_str = "tests/resources/probes/python/failing.py"
    probe_url = f"github://canonical/juju-doctor//{path_str}?main"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(probe_url, Path(tmpdir))
        probes = probe_tree.probes
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.name == "canonical_juju-doctor__tests_resources_probes_python_failing.py"
        assert probe.path == Path(tmpdir) / probe.name


@pytest.mark.github
def test_parse_dir():
    # GIVEN a probe directory specified in a Github remote on the main branch
    path_str = "tests/resources/probes/python"
    probe_url = f"github://canonical/juju-doctor//{path_str}?main"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(probe_url, Path(tmpdir))
        probes = probe_tree.probes
        # THEN each Probe is correctly parsed
        for probe in probes:
            file_name = probe.name.split("/")[-1]
            url_flattened = f"{'tests/resources/probes/python'.replace('/', '_')}/{file_name}"
            assert probe.name == f"canonical_juju-doctor__{url_flattened}"
            assert probe.path == Path(tmpdir) / probe.name
