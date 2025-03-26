import tempfile
from pathlib import Path
from typing import List

from juju_doctor.probes import Probe


def contains_only_passing_and_failing_probes(probes: List[Probe]):
    # Ensure that there are only 2 probes in the list
    assert len(probes) == 2
    passing_probe = next((probe.name for probe in probes if "passing.py" in probe.name), None)
    failing_probe = next((probe.name for probe in probes if "failing.py" in probe.name), None)

    # Ensure the probes match "passing.py" and "failing.py"
    assert passing_probe is not None
    assert failing_probe is not None


def test_ruleset_calls_scriptlet():
    # GIVEN a ruleset probe file calls scriptlet probes
    probe_url = "file://tests/resources/probes/ruleset/scriptlet.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probe is fetched to a local filesystem
        found_probes = Probe.from_url(url=probe_url, probes_root=Path(tmpdir))
        # THEN probes are found
        contains_only_passing_and_failing_probes(found_probes)


def test_ruleset_calls_nested():
    # GIVEN a ruleset probe file calls another ruleset
    probe_url = "file://tests/resources/probes/ruleset/nested.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probe is fetched to a local filesystem
        found_probes = Probe.from_url(url=probe_url, probes_root=Path(tmpdir))
        # THEN probes are found
        contains_only_passing_and_failing_probes(found_probes)


def test_ruleset_calls_dir():
    # GIVEN a ruleset probe file calls a directory of probes (scriptlet and/or ruleset)
    probe_url = "file://tests/resources/probes/ruleset/dir.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probe is fetched to a local filesystem
        found_probes = Probe.from_url(url=probe_url, probes_root=Path(tmpdir))
        # THEN probes are found
        contains_only_passing_and_failing_probes(found_probes)
