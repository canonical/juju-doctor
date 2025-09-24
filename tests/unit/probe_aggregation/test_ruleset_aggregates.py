import tempfile
from pathlib import Path
from typing import List

from juju_doctor.probes import Probe


def contains_only_one_passing_and_failing_probe(probes: List[Probe]):
    # Ensure that there are only 2 probes in the list
    assert len(probes) == 2
    passing_probe = next(
        (
            probe.name
            for probe in probes
            if "passing" in probe.name
        ),
        None,
    )
    failing_probe = next(
        (
            probe.name
            for probe in probes
            if "failing" in probe.name
        ),
        None,
    )

    # Ensure the probes match "passing.py" and "failing.py"
    assert passing_probe is not None
    assert failing_probe is not None


def test_ruleset_calls_scriptlet():
    # GIVEN a ruleset probe file calls scriptlet probes
    probe_url = "file://tests/resources/probes/ruleset/scriptlets.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probe is fetched to a local filesystem
        probe_tree = Probe.from_url(probe_url, Path(tmpdir))
        probes = probe_tree.probes
        # THEN probes are found
        contains_only_one_passing_and_failing_probe(probes)


def test_ruleset_calls_nested():
    # GIVEN a ruleset probe file calls another ruleset
    probe_url = "file://tests/resources/probes/ruleset/nested.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probe is fetched to a local filesystem
        probe_tree = Probe.from_url(probe_url, Path(tmpdir))
        probes = probe_tree.probes
        # THEN probes are found
        contains_only_one_passing_and_failing_probe(probes)


def test_ruleset_calls_dir():
    # GIVEN a ruleset probe file calls a directory of probes (scriptlet and/or ruleset)
    probe_url = "file://tests/resources/probes/ruleset/dir.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probe is fetched to a local filesystem
        probe_tree = Probe.from_url(probe_url, Path(tmpdir))
        # THEN probes are found
        contains_only_one_passing_and_failing_probe(probe_tree.probes)


def test_ruleset_finds_probes_and_builtins():
    # GIVEN a ruleset probe file defines probes and builtins
    probe_url = "file://tests/resources/probes/ruleset/scriptlets.yaml"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN the probe is fetched to a local filesystem
        probe_tree = Probe.from_url(probe_url, Path(tmpdir))
        # THEN probes are found
        contains_only_one_passing_and_failing_probe(probe_tree.probes)
