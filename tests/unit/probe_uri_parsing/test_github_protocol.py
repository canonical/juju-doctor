import tempfile
from pathlib import Path

from fetcher import ProbeCategory, fetch_probes


def test_parse_gh_file():
    # GIVEN a probe file specified in a Github remote for a specific branch
    probe_uri = "github://canonical/juju-doctor//tests/resources/show-unit/relation_dashboard_uid.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN only 1 probe exists
        assert len(probes) == 1
        probe = probes[0]
        # AND the Probe was correctly parsed
        assert probe.category == ProbeCategory.SHOW_UNIT
        assert probe.uri == probe_uri
        assert probe.name == "canonical_juju-doctor__tests_resources_show-unit_relation_dashboard_uid.py"
        assert probe.original_path == Path("tests/resources/show-unit/relation_dashboard_uid.py")
        assert probe.local_path == Path(tmpdir) / probe.name


def test_parse_gh_dir():
    # GIVEN a probe directory specified in a Github remote
    probe_uri = "github://canonical/juju-doctor//tests/resources/show-unit"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        # THEN 2 probe exists
        assert len(probes) == 2
        failing_probe = [probe for probe in probes if "failing.py" in probe.name][0]
        dashboard_probe = [probe for probe in probes if "relation_dashboard_uid.py" in probe.name][0]
        # AND the Probe was correctly parsed
        assert failing_probe.category == ProbeCategory.SHOW_UNIT
        assert failing_probe.uri == probe_uri
        assert failing_probe.name == "canonical_juju-doctor__tests_resources_show-unit/failing.py"
        assert failing_probe.original_path == Path("tests/resources/show-unit")
        assert failing_probe.local_path == Path(tmpdir) / failing_probe.name

        # AND the Probe was correctly parsed
        assert dashboard_probe.category == ProbeCategory.SHOW_UNIT
        assert dashboard_probe.uri == probe_uri
        assert (
            dashboard_probe.name
            == "canonical_juju-doctor__tests_resources_show-unit/relation_dashboard_uid.py"
        )
        assert dashboard_probe.original_path == Path("tests/resources/show-unit")
        assert dashboard_probe.local_path == Path(tmpdir) / dashboard_probe.name
