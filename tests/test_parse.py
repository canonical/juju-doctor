
import fetcher
# urllib.parse
# TODO I can use fsspec behind the scenes


def test_parse():
    # GIVEN
    # WHEN
    # THEN
    sample_url = "https://example.com/network.git//modules/vpc"
    # Without branch
    assert fetcher.parse_tf_notation_into_components(url) == {
        "repo_url": "https://example.com/network.git",
        "ref": "",
        "sub-dir": "modules/vpc",
    }
    # With branch
    assert fetcher.parse_tf_notation_into_components(sample_url + "?ref=v1.2.0") == {
        "repo_url": "https://example.com/network.git",
        "ref": "v1.2.0",
        "sub-dir": "modules/vpc",
    }
    # Specific file
    # ... I have the contents in local FS /tmp/fake so I can check in there if its a file or dir
    path = Path("something")
    if p.is_file()

    # AFTER check URL or local Path:
    # Local path
    # 