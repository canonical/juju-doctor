import tempfile
from pathlib import Path

import pytest
from fetcher import Fetcher


@pytest.mark.parametrize("category", ["status", "bundle", "show-unit"])
def test_parse_gh_file(category):
    # GIVEN a probe file specified in a Github remote on the main branch
    probe_uri = f"github://canonical/juju-doctor//tests/resources/{category}/failing.py?main"
    with tempfile.TemporaryDirectory() as tmpdir:
        fetcher = Fetcher(Path(tmpdir))
        # WHEN the probes are fetched to a local filesystem
        probes = fetcher.fetch_probes(uri=probe_uri)
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
    # GIVEN a probe directory specified in a Github remote on the main branch
    probe_uri = f"github://canonical/juju-doctor//tests/resources/{category}?main"
    with tempfile.TemporaryDirectory() as tmpdir:
        fetcher = Fetcher(Path(tmpdir))
        # WHEN the probes are fetched to a local filesystem
        probes = fetcher.fetch_probes(uri=probe_uri)
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
