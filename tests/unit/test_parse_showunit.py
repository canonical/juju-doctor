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
        gh_probe = probes[0]
        # AND the Probe was correctly parsed
        assert gh_probe.name == "canonical_grafana-k8s-operator__probes_show-unit_relation_dashboard_uid.py@feature_probes"
        # TODO We should strip the branch from the path
        assert gh_probe.path == Path(
            tmpdir
            + "/canonical_grafana-k8s-operator__probes_show-unit_relation_dashboard_uid.py@feature_probes"
        )
        assert gh_probe.category == ProbeCategory.SHOW_UNIT
        assert gh_probe.uri == probe_uri
