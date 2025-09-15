import tempfile
from pathlib import Path

import pytest

from juju_doctor.probes import Probe


@pytest.mark.parametrize("extension", [("yaml"), ("YAML"), ("yml"), ("YML")])
def test_ruleset_extensions(extension):
    # GIVEN a ruleset probe file
    probe_url = f"file://tests/resources/probes/ruleset/extensions/scriptlet.{extension}"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(probe_url, Path(tmpdir))
        # THEN probes are found
        assert len(probe_tree.probes) > 0
