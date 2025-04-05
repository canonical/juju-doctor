# ruff: noqa: E501

import json
from pathlib import Path

from juju_doctor.probes import Probe, ProbeResult
from juju_doctor.tree import Group, OutputFormat, ProbeResultAggregator

# TODO Add a docstring to each tests file

def probe_results(tmp_path: str, flattened_path: str, passed: bool):
    results = []
    for func_name in ["status", "bundle", "show_unit"]:
        results.append(
            ProbeResult(
                probe=Probe(
                    path=Path(f"{tmp_path}/probes/{flattened_path}"),
                    probes_root=Path(f"{tmp_path}/probes"),
                ),
                func_name=func_name,
                passed=passed,
            )
        )
    return results


def test_assemble_tree_artifact_group():
    expected_json = {
        "Artifact": {
            "children": [
                {
                    "bundle": {
                        "children": [
                            "🔴 tests_resources_probes_python_failing.py/bundle failed (None)",
                            "🟢 tests_resources_probes_python_passing.py/bundle passed",
                        ]
                    }
                },
                {
                    "show_unit": {
                        "children": [
                            "🔴 tests_resources_probes_python_failing.py/show_unit failed (None)",
                            "🟢 tests_resources_probes_python_passing.py/show_unit passed",
                        ]
                    }
                },
                {
                    "status": {
                        "children": [
                            "🔴 tests_resources_probes_python_failing.py/status failed (None)",
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
    output_fmt = OutputFormat(False, False, "json", [Group.ARTIFACT.value])
    aggregator = ProbeResultAggregator(mocked_results, output_fmt)
    aggregator.assemble_trees()
    # THEN We get all the groupings
    actual_json = json.loads(aggregator.tree.to_json())["Results"]["children"]
    assert actual_json == [expected_json]


def test_assemble_tree_directory_group():
    # TODO Update this test to use ProbeResult from some directories
    pass


def test_assemble_tree_status_group():
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
    output_fmt = OutputFormat(False, False, "json", [Group.STATUS.value])
    aggregator = ProbeResultAggregator(mocked_results, output_fmt)
    aggregator.assemble_trees()
    # THEN We get all the groupings
    actual_json = json.loads(aggregator.tree.to_json())["Results"]["children"]
    assert actual_json == [expected_json]


if __name__ == "__main__":
    test_assemble_tree_artifact_group()
    test_assemble_tree_directory_group()
    test_assemble_tree_status_group()
