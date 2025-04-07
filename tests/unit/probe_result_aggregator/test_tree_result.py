# ruff: noqa: E501

import json
from pathlib import Path

from juju_doctor.probes import Probe, ProbeAssertionResult
from juju_doctor.tree import Group, OutputFormat, ProbeAssertionResultAggregator

# TODO Add a docstring to each tests file

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
    return results


def test_build_tree_status_group():
    # TODO replace "pass" and "fail" with AssertionStatus.FAIL.value
    expected_json = {
        "Status": {
            "children": [
                {
                    "fail": {
                        "children": [
                            "🔴 tests_resources_probes_python_failing.py/bundle failed (None)",
                            "🔴 tests_resources_probes_python_failing.py/show_unit failed (None)",
                            "🔴 tests_resources_probes_python_failing.py/status failed (None)",
                        ]
                    }
                },
                {
                    "pass": {
                        "children": [
                            "🟢 tests_resources_probes_python_passing.py/bundle passed",
                            "🟢 tests_resources_probes_python_passing.py/show_unit passed",
                            "🟢 tests_resources_probes_python_passing.py/status passed",
                        ]
                    }
                },
            ]
        }
    }

    # GIVEN The results for 2 python probes (passing and failing)
    mocked_results = []
    mocked_results.extend(
        probe_results("/fake/path", "tests_resources_probes_python_failing.py", False)
    )
    mocked_results.extend(
        probe_results("/fake/path", "tests_resources_probes_python_passing.py", True)
    )
    # WHEN the probe results are aggregated and placed in a tree with the `--verbose` option
    output_fmt = OutputFormat(False, False, "json")
    aggregator = ProbeAssertionResultAggregator(mocked_results, output_fmt)
    aggregator._build_tree()
    # THEN We get all the groupings
    actual_json = json.loads(aggregator.tree.to_json())["Results"]["children"]
    assert actual_json == [expected_json]


if __name__ == "__main__":
    test_build_tree_status_group()
