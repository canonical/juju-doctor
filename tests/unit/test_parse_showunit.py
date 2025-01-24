import tempfile
from pathlib import Path

from fetcher import ProbeCategory, fetch_probes


def test_parse_gh_file():
    # GIVEN
    # WHEN
    # THEN
    probe_uri = "github://canonical/grafana-k8s-operator//probes/show-unit/relation_dashboard_uid.py@feature/probes"
    with tempfile.TemporaryDirectory() as tmpdir:
        probes = fetch_probes(uri=probe_uri, destination=Path(tmpdir))
        assert len(probes) == 1
        assert probes[0].name == "canonical_grafana-k8s-operator__probes_show-unit_relation_dashboard_uid.py@feature_probes"
        # TODO We should strip the branch from the path
        assert probes[0].path == Path(
            tmpdir
            + "/canonical_grafana-k8s-operator__probes_show-unit_relation_dashboard_uid.py@feature_probes"
        )
        assert probes[0].category == ProbeCategory.SHOW_UNIT
        assert probes[0].uri == probe_uri
