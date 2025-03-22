import tempfile
from pathlib import Path

import pytest
from fetcher import CircularRulesetError, Fetcher


def test_ruleset_raise_circular():
    # GIVEN a ruleset probe file calls a circular chain of rulesets
    probe_uri = "file://tests/resources/probes/ruleset/circular.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        # THEN a CircularRulesetError is raised
        with pytest.raises(CircularRulesetError):
            Fetcher.fetch_probes(destination=Path(tmpdir), uri=probe_uri)

def test_ruleset_calls_ruleset():
    # GIVEN a ruleset probe file calls a directory of scriptlets
    probe_uri = "file://tests/resources/probes/ruleset/nested.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Fetcher.fetch_probes(destination=Path(tmpdir), uri=probe_uri)
        # THEN probes are found
        assert len(probes) > 0
