import tempfile
from pathlib import Path

import pytest
from fetcher import fetch_probes


@pytest.mark.parametrize("category", ["status", "bundle", "show-unit"])
def test_parse_gh_file(category):
    # GIVEN a probe file specified in a Github remote for a specific branch
    probe_uri = f"github://canonical/juju-doctor//tests/resources/{category}/failing.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.category.value == category
        assert probe.uri == probe_uri
        assert probe.name == f"canonical_juju-doctor__tests_resources_{category}_failing.py"
        assert probe.original_path == Path(f"tests/resources/{category}/failing.py")
        assert probe.local_path == Path(tmpdir) / probe.name


@pytest.mark.parametrize("category", ["status", "bundle", "show-unit"])
def test_parse_gh_dir(category):
    # GIVEN a probe directory specified in a Github remote
    probe_uri = f"github://canonical/juju-doctor//tests/resources/{category}"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN 2 probe exists
        assert len(probes) == 2
        passing_probe = [probe for probe in probes if "passing.py" in probe.name][0]
        failing_probe = [probe for probe in probes if "failing.py" in probe.name][0]
        # AND the Probe was correctly parsed as passing
        assert passing_probe.category.value == category
        assert passing_probe.uri == probe_uri
        assert passing_probe.name == f"canonical_juju-doctor__tests_resources_{category}/passing.py"
        assert passing_probe.original_path == Path(f"tests/resources/{category}")
        assert passing_probe.local_path == Path(tmpdir) / passing_probe.name
        # AND the Probe was correctly parsed as failing
        assert failing_probe.category.value == category
        assert failing_probe.uri == probe_uri
        assert failing_probe.name == f"canonical_juju-doctor__tests_resources_{category}/failing.py"
        assert failing_probe.original_path == Path(f"tests/resources/{category}")
        assert failing_probe.local_path == Path(tmpdir) / failing_probe.name
