import tempfile
from pathlib import Path

from src.juju_doctor.probes import Probe


def get_assertions_count(builtins_groups: dict, key: str) -> int:
    count = 0
    for builtins in builtins_groups.values():
        value = builtins.get(key)
        if value is not None and hasattr(value, 'assertions'):
            count += len(value.assertions)
    return count


def test_probes_and_builtins():
    # GIVEN a Ruleset with scriptlets and builtins
    yaml_content = """
    name: Test scriptlets and builtins
    probes:
      - name: Scriptlet probe
        type: scriptlet
        url: file://tests/resources/probes/python/failing.py
      - name: Builtin probe
        type: builtin/application-exists
        with:
          - application-name: catalogue
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(Path(tmpdir) / "probes_and_builtins.yaml", "w") as temp_file:
            temp_file.write(yaml_content)
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(f"file://{temp_file.name}", Path(tmpdir))
    # THEN both the probe and builtin were aggregated
    assert len(probe_tree.probes) == 2


def test_nested_builtins():
    # GIVEN a Ruleset (with builtin assertions) executes another Ruleset with builtin assertions
    yaml_content = """
    name: Test nested builtins
    probes:
      - name: Local builtins
        type: ruleset
        url: file://tests/resources/probes/ruleset/builtins.yaml
      - name: Builtin application-exists
        type: builtin/application-exists
        with:
          - application-name: catalogue
      - name: Builtin app-relation-exists
        type: builtin/app-relation-exists
        with:
          - apps: [grafana:catalogue, catalogue:catalogue]
      - name: Builtin offer-exists
        type: builtin/offer-exists
        with:
          - offer-name: loki-logging
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(Path(tmpdir) / "nested-builtins.yaml", "w") as temp_file:
            temp_file.write(yaml_content)
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(f"file://{temp_file.name}", Path(tmpdir))
    # THEN both the top-level and nested builtin assertions were aggregated
    assert len(probe_tree.probes) > 3
