import tempfile
from pathlib import Path

from juju_doctor.probes import Probe


def test_nested_builtins():
    # GIVEN a Ruleset (with builtin assertions) executes another Ruleset with builtin assertions
    yaml_content = """
    name: Test nested builtins
    applications:
      - name: catalogue
    relations:
      - provides: grafana:catalogue
        requires: catalogue:catalogue
    probes:
      - name: Local builtins
        type: ruleset
        url: file://tests/resources/probes/ruleset/builtins.yaml
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(Path(tmpdir) / "nested-builtins.yaml", 'w') as temp_file:
            temp_file.write(yaml_content)
        # WHEN the probes are fetched to a local filesystem
        probe_tree = Probe.from_url(url=f"file://{temp_file.name}", probes_root=Path(tmpdir))
    # THEN both the top-level and nested builtin assertions were aggregated
    assert len(probe_tree.builtins["applications"]) == 2
    assert len(probe_tree.builtins["relations"]) == 2
