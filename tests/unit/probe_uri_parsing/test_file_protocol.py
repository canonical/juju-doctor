import tempfile
from pathlib import Path

import pytest
from fetcher import ProbeCategory, fetch_probes


@pytest.mark.parametrize("category", ["status", "bundle", "show-unit"])
def test_parse_file_file(category):
    # GIVEN a local probe file
    probe_uri = f"file://tests/resources/{category}/failing.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.category.value == category
        assert probe.uri == probe_uri
        assert probe.name == f"tests_resources_{category}_failing.py"
        assert probe.original_path == Path(f"tests/resources/{category}/failing.py")
        assert probe.local_path == Path(tmpdir) / probe.name


def test_parse_file_dir():
    # GIVEN a local probe file with the file protocol
    probe_uri = "file://tests/resources/show-unit"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN 2 probes exist
        assert len(probes) == 2
        failing_probe = [probe for probe in probes if "failing.py" in probe.name][0]
        dashboard_probe = [probe for probe in probes if "grafana-probe.py" in probe.name][0]
        # AND the Probe was correctly parsed
        assert failing_probe.category == ProbeCategory.SHOW_UNIT
        assert failing_probe.uri == probe_uri
        assert failing_probe.name == "tests_resources_show-unit/failing.py"
        assert failing_probe.original_path == Path("tests/resources/show-unit")
        assert failing_probe.local_path == Path(tmpdir) / failing_probe.name

        # AND the Probe was correctly parsed
        assert dashboard_probe.category == ProbeCategory.SHOW_UNIT
        assert dashboard_probe.uri == probe_uri
        assert dashboard_probe.name == "tests_resources_show-unit/grafana-probe.py"
        assert dashboard_probe.original_path == Path("tests/resources/show-unit")
        assert dashboard_probe.local_path == Path(tmpdir) / dashboard_probe.name
