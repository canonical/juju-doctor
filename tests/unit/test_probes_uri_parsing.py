import tempfile
from pathlib import Path

from fetcher import ProbeCategory, fetch_probes


def test_parse_gh_file():
    # GIVEN a probe file specified in a Github remote for a specific branch
    probe_uri = "github://canonical/grafana-k8s-operator//probes/show-unit/relation_dashboard_uid.py@feature/probes"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        branch = "@feature_probes"
        assert probe.name == "relation_dashboard_uid.py"
        assert probe.original_path == Path("probes/show-unit/relation_dashboard_uid.py")
        assert probe.local_path == Path(
            tmpdir
            + "/canonical_grafana-k8s-operator__probes_show-unit_relation_dashboard_uid.py"
            + branch
        )
        assert probe.category == ProbeCategory.SHOW_UNIT
        assert probe.uri == probe_uri


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
        assert bundle_probe.name == "probe_bundle.py"
        assert bundle_probe.original_path == Path("probes/bundle/probe_bundle.py")
        assert bundle_probe.local_path == Path(
            tmpdir + "/canonical_grafana-agent-operator__probes"
        )
        assert bundle_probe.category == ProbeCategory.BUNDLE
        assert bundle_probe.uri == probe_uri

        # AND the "status" Probe was correctly parsed
        assert status_probe.name == "probe_status.py"
        assert status_probe.original_path == Path("probes/status/probe_status.py")
        assert status_probe.local_path == Path(
            tmpdir + "/canonical_grafana-agent-operator__probes"
        )
        assert status_probe.category == ProbeCategory.STATUS
        assert status_probe.uri == probe_uri


def test_parse_file():
    # GIVEN a local probe file
    probe_uri = "file://resources/show-unit/relation_dashboard_uid.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.name == "relation_dashboard_uid.py"
        assert probe.original_path == Path("resources/show-unit/relation_dashboard_uid.py")
        assert probe.local_path == Path(tmpdir + "/resources_show-unit_relation_dashboard_uid.py")
        assert probe.category == ProbeCategory.SHOW_UNIT
        assert probe.uri == probe_uri


def test_parse_dir():
    pass
    # GIVEN a local probe directory
    # WHEN the probes are fetched to a local filesystem
    # THEN only 2 probe exists
    # AND the Probe was correctly parsed
