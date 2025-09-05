import tempfile
from pathlib import Path

from juju_doctor.probes import Probe


def test_probes_and_builtins():
    # GIVEN a Ruleset with probes and builtins
    yaml_content = """
    name: Test probes and builtins
    builtins:
        applications:
          - name: catalogue
    probes:
      - name: Foo
        type: scriptlet
        url: file://tests/resources/probes/python/failing.py
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(Path(tmpdir) / "probes_and_builtins.yaml", "w") as temp_file:
            temp_file.write(yaml_content)
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(url=f"file://{temp_file.name}", probes_root=Path(tmpdir))
    # THEN both the probe and builtin were aggregated
    assert len(probe_tree.builtins) == 1
    assert len(probe_tree.probes) == 1


def test_nested_builtins():
    # GIVEN a Ruleset (with builtin assertions) executes another Ruleset with builtin assertions
    yaml_content = """
    name: Test nested builtins
    builtins:
        applications:
          - name: catalogue
        relations:
          - apps: [grafana:catalogue, catalogue:catalogue]
        offers:
          - name: loki-logging
    probes:
      - name: Local builtins
        type: ruleset
        url: file://tests/resources/probes/ruleset/builtins.yaml
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(Path(tmpdir) / "nested-builtins.yaml", "w") as temp_file:
            temp_file.write(yaml_content)
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(url=f"file://{temp_file.name}", probes_root=Path(tmpdir))
    # THEN both the top-level and nested builtin assertions were aggregated
    assert len(probe_tree.builtins) == 2
    total_applications = len(
        [a for b in probe_tree.builtins.values() for a in b.get("applications").assertions]
    )
    total_relations = len(
        [a for b in probe_tree.builtins.values() for a in b.get("relations").assertions]
    )
    total_offers = len(
        [a for b in probe_tree.builtins.values() for a in b.get("offers").assertions]
    )
    assert total_applications > 1
    assert total_relations > 1
    assert total_offers > 1
