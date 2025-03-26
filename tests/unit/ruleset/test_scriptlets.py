import tempfile
from pathlib import Path

import pytest

from juju_doctor.probes import Probe


def test_ruleset_calls_scriptlet_file():
    # GIVEN a ruleset probe file calls scriptlets
    probe_url = "file://tests/resources/probes/ruleset/scriptlet.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Probe.from_url(url=probe_url, probes_root=Path(tmpdir))
        # THEN 2 python probes exist
        assert len(probes) == 2
        passing_probe = [probe for probe in probes if "passing.py" in probe.name][0]
        failing_probe = [probe for probe in probes if "failing.py" in probe.name][0]
        # AND the Probe was correctly parsed as passing
        assert passing_probe.name == "tests_resources_probes_python_passing.py"
        assert passing_probe.path == Path(tmpdir) / passing_probe.name
        # AND the Probe was correctly parsed as failing
        assert failing_probe.name == "tests_resources_probes_python_failing.py"
        assert failing_probe.path == Path(tmpdir) / failing_probe.name


@pytest.mark.parametrize("extension", [("yaml"), ("YAML"), ("yml"), ("YML")])
def test_ruleset_extensions(extension):
    # GIVEN a ruleset probe file
    probe_url = f"file://tests/resources/probes/ruleset/extensions/scriptlet.{extension}"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probes are fetched to a local filesystem
        probes = Probe.from_url(url=probe_url, probes_root=Path(tmpdir))
        # THEN probes are found
        assert len(probes) > 0
