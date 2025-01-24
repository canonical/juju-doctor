import tempfile
from pathlib import Path
from types import SimpleNamespace

from fetcher import Fetcher


def test_parse_url_probe():
    # GIVEN
    # WHEN
    # THEN
    sample_url = "https://example.com/network.git//modules/vpc"
    fetcher = Fetcher(Path())
    fetcher.parse_tf_notation_into_components(sample_url)
    assert fetcher.meta == SimpleNamespace(
        path=Path("modules/vpc"),
        ref="",
        org="network.git",
        repo="",
        url="https://example.com/network.git/",
        protocol="unknown",
    )

def test_parse_url_probe_with_branch():
    # GIVEN
    # WHEN
    # THEN
    sample_url = "https://example.com/network.git//modules/vpc"
    fetcher = Fetcher(Path())
    fetcher.parse_tf_notation_into_components(sample_url + "?ref=v1.2.0")
    assert fetcher.meta == SimpleNamespace(
        path=Path("modules/vpc"),
        ref="v1.2.0",
        org="network.git",
        repo="",
        url="https://example.com/network.git/",
        protocol="unknown",
    )

def test_parse_file_probe():
    # GIVEN
    # WHEN
    # THEN
    fetcher = Fetcher(Path())
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmpfile:
        fetcher.parse_tf_notation_into_components(tmpfile.name)
        assert fetcher.meta == SimpleNamespace(
            path=Path(tmpfile.name),
            ref="",
            org="",
            repo="",
            url="",
            protocol="file",
        )

def test_download_remote_to_fs():
    sample_url = "https://raw.githubusercontent.com/canonical/grafana-k8s-operator//probes/external/show-unit/relation_dashboard_uid.py?ref=feature/probes"

    with tempfile.TemporaryDirectory() as tmpdir:
        fetcher = Fetcher(Path(tmpdir))
        fetcher.run(sample_url)
        assert (Path(tmpdir) / "relation_dashboard_uid.py").exists()
