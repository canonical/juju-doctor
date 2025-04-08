# ruff: noqa: E501

import json
from pathlib import Path

from juju_doctor.probes import AssertionStatus, Probe, ProbeAssertionResult
from juju_doctor.tree import OutputFormat, ProbeResultAggregator


def probe_results(tmp_path: str, flattened_path: str, passed: bool):
    results = []
    for func_name in ["status", "bundle", "show_unit"]:
        results.append(
            ProbeAssertionResult(
                probe=Probe(
                    path=Path(f"{tmp_path}/probes/{flattened_path}"),
                    probes_root=Path(f"{tmp_path}/probes"),
                ),
                func_name=func_name,
                passed=passed,
            )
        )
    return {flattened_path: results}


def test_build_tree_status_group():
    expected_json = [
        {
            AssertionStatus.FAIL.value: {
                "children": [
                    '🔴 tests_resources_probes_python_failing.py (status, bundle, show_unit)'
                ]
            }
        },
        {
            AssertionStatus.PASS.value: {
                "children": [
                    '🟢 tests_resources_probes_python_passing.py'
                ]
            }
        }
    ]

    # GIVEN The results for 2 python probes (passing and failing)
    mocked_results = {}
    mocked_results.update(
        probe_results("/fake/path", "tests_resources_probes_python_failing.py", False)
    )
    mocked_results.update(
        probe_results("/fake/path", "tests_resources_probes_python_passing.py", True)
    )
    # WHEN The probe results are aggregated and placed in a tree
    output_fmt = OutputFormat(False, "json")
    aggregator = ProbeResultAggregator(mocked_results, output_fmt)
    aggregator._build_tree()
    # THEN The tree result is correctly grouped and the probe assertions are displ
    actual_json = json.loads(aggregator._tree.to_json())["Results"]["children"]
    assert actual_json == expected_json


if __name__ == "__main__":
    test_build_tree_status_group()
