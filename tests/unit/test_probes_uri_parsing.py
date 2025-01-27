import tempfile
from pathlib import Path

from fetcher import ProbeCategory, fetch_probes


def test_parse_gh_file():
    # GIVEN a probe file specified in a Github remote for a specific branch
    probe_uri = "github://canonical/grafana-k8s-operator//probes/show-unit/relation_dashboard_uid.py?feature/probes"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.category == ProbeCategory.SHOW_UNIT
        assert probe.uri == probe_uri
        assert (
            probe.name
            == "canonical_grafana-k8s-operator__probes_show-unit_relation_dashboard_uid.py"
        )
        assert probe.original_path == Path("probes/show-unit/relation_dashboard_uid.py")
        assert probe.local_path == Path(tmpdir) / probe.name


def test_parse_gh_dir():
    # GIVEN a probe directory specified in a Github remote
    probe_uri = "github://canonical/grafana-agent-operator//probes"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN 2 probe exists
        assert len(probes) == 2
        bundle_probe = probes[0]
        status_probe = probes[1]
        # AND the "bundle" Probe was correctly parsed
        assert bundle_probe.category == ProbeCategory.BUNDLE
        assert bundle_probe.uri == probe_uri
        assert (
            bundle_probe.name == "canonical_grafana-agent-operator__probes/bundle/probe_bundle.py"
        )
        assert bundle_probe.original_path == Path("probes")
        assert bundle_probe.local_path == Path(tmpdir) / bundle_probe.name

        # AND the "status" Probe was correctly parsed
        assert status_probe.category == ProbeCategory.STATUS
        assert status_probe.uri == probe_uri
        assert (
            status_probe.name == "canonical_grafana-agent-operator__probes/status/probe_status.py"
        )
        assert status_probe.original_path == Path("probes")
        assert status_probe.local_path == Path(tmpdir) / status_probe.name


def test_parse_file_file():
    # GIVEN a local probe file
    probe_uri = "file://resources/show-unit/relation_dashboard_uid.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.category == ProbeCategory.SHOW_UNIT
        assert probe.uri == probe_uri
        assert probe.name == "resources_show-unit_relation_dashboard_uid.py"
        assert probe.original_path == Path("resources/show-unit/relation_dashboard_uid.py")
        assert probe.local_path == Path(tmpdir) / probe.name


def test_parse_file_dir():
    # GIVEN a local probe file with the file protocol
    probe_uri = "file://resources/show-unit"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 2
        failing_probe = probes[0]
        dashboard_probe = probes[1]
        # AND the "bundle" Probe was correctly parsed
        assert failing_probe.category == ProbeCategory.SHOW_UNIT
        assert failing_probe.uri == probe_uri
        assert failing_probe.name == "resources_show-unit/failing.py"
        assert failing_probe.original_path == Path("resources/show-unit")
        assert failing_probe.local_path == Path(tmpdir) / failing_probe.name

        # AND the "status" Probe was correctly parsed
        assert dashboard_probe.category == ProbeCategory.SHOW_UNIT
        assert dashboard_probe.uri == probe_uri
        assert dashboard_probe.name == "resources_show-unit/relation_dashboard_uid.py"
        assert dashboard_probe.original_path == Path("resources/show-unit")
        assert dashboard_probe.local_path == Path(tmpdir) / dashboard_probe.name
