from src.fetcher import Fetcher
from pathlib import Path
import tempfile
from types import SimpleNamespace


def test_parse_url():
    # GIVEN
    # WHEN
    # THEN
    sample_url = "https://example.com/network.git//modules/vpc"

    with tempfile.TemporaryDirectory() as tmpdir:
        fetcher = Fetcher(Path(tmpdir))

        # Without branch
        fetcher.parse_tf_notation_into_components(sample_url)
        assert fetcher.meta == SimpleNamespace(
            is_file=False,
            path=Path("modules/vpc"),
            ref="",
            org="network.git",
            repo="",
            url="https://example.com/network.git/",
            protocol="unknown",
        )

        # With branch
        fetcher = Fetcher(Path(tmpdir))
        fetcher.parse_tf_notation_into_components(sample_url + "?ref=v1.2.0")
        assert fetcher.meta == SimpleNamespace(
            is_file=False,
            path=Path("modules/vpc"),
            ref="v1.2.0",
            org="network.git",
            repo="",
            url="https://example.com/network.git/",
            protocol="unknown",
        )

def test_download_to_dir():
    sample_url = "https://raw.githubusercontent.com/MichaelThamm/juju-doctor//resources/relation_dashboard_uid.py?ref=feature/fetcher-2"

    with tempfile.TemporaryDirectory() as tmpdir:
        fetcher = Fetcher(Path(tmpdir))
        fetcher.run(sample_url)
        assert (Path(tmpdir) / "relation_dashboard_uid.py").exists()
