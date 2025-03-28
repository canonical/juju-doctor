# ruff: noqa: E501

import json
import tempfile
from pathlib import Path

from juju_doctor.probes import OutputFormat, Probe, ProbeResultAggregator, ProbeResults


def probe_results(tmp_path: str, flattened_path: str, passed: bool):
    results = []
    for func_name in ["status", "bundle", "show_unit"]:
        results.append(
            ProbeResults(
                probe=Probe(
                    path=Path(f"{tmp_path}/probes/{flattened_path}"), probes_root=Path(f"{tmp_path}/probes")
                ),
                func_name=func_name,
                passed=passed,
            )
        )
    return results


def test_assemble_tree():
    expected_json = {
        "Results": {
            "children": [
                {
                    "Status": {
                        "children": [
                            {
                                "fail": {
                                    "children": [
                                        ":red_circle: tests_resources_probes_python_failing.py/bundle failed (None)",
                                        ":red_circle: tests_resources_probes_python_failing.py/show_unit failed (None)",
                                        ":red_circle: tests_resources_probes_python_failing.py/status failed (None)",
                                    ]
                                }
                            },
                            {
                                "pass": {
                                    "children": [
                                        ":green_circle: tests_resources_probes_python_passing.py/bundle passed",
                                        ":green_circle: tests_resources_probes_python_passing.py/show_unit passed",
                                        ":green_circle: tests_resources_probes_python_passing.py/status passed",
                                    ]
                                }
                            },
                        ]
                    }
                }
            ]
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        # GIVEN The results for 2 python probes (passing and failing)
        mocked_results = []
        mocked_results.extend(probe_results(tmpdir, "tests_resources_probes_python_failing.py", False))
        mocked_results.extend(probe_results(tmpdir, "tests_resources_probes_python_passing.py", True))
        # WHEN the probe results are aggregated and placed in a tree
        output_fmt = OutputFormat(False, "json", ["status"], exception_logging=False)
        aggregator = ProbeResultAggregator(mocked_results, output_fmt)
        aggregator.assemble_trees()
        # THEN We get all the groupings
        assert json.loads(aggregator.tree.to_json()) == expected_json


def test_assemble_tree_verbose():
    expected_json = {
        "Results": {
            "children": [
                {
                    "Artifact": {
                        "children": [
                            {
                                "bundle": {
                                    "children": [
                                        ":green_circle: tests_resources_probes_python_passing.py/bundle passed",
                                        ":red_circle: tests_resources_probes_python_failing.py/bundle failed (None)",
                                    ]
                                }
                            },
                            {
                                "show_unit": {
                                    "children": [
                                        ":green_circle: tests_resources_probes_python_passing.py/show_unit passed",
                                        ":red_circle: tests_resources_probes_python_failing.py/show_unit failed (None)",
                                    ]
                                }
                            },
                            {
                                "status": {
                                    "children": [
                                        ":green_circle: tests_resources_probes_python_passing.py/status passed",
                                        ":red_circle: tests_resources_probes_python_failing.py/status failed (None)",
                                    ]
                                }
                            },
                        ]
                    }
                },
                {
                    "Directory": {
                        "children": [
                            {
                                "/fake/path/probes": {
                                    "children": [
                                        ":green_circle: tests_resources_probes_python_passing.py/bundle passed",
                                        ":green_circle: tests_resources_probes_python_passing.py/show_unit passed",
                                        ":green_circle: tests_resources_probes_python_passing.py/status passed",
                                        ":red_circle: tests_resources_probes_python_failing.py/bundle failed (None)",
                                        ":red_circle: tests_resources_probes_python_failing.py/show_unit failed (None)",
                                        ":red_circle: tests_resources_probes_python_failing.py/status failed (None)",
                                    ]
                                }
                            }
                        ]
                    }
                },
                {
                    "Status": {
                        "children": [
                            {
                                "fail": {
                                    "children": [
                                        ":red_circle: tests_resources_probes_python_failing.py/bundle failed (None)",
                                        ":red_circle: tests_resources_probes_python_failing.py/show_unit failed (None)",
                                        ":red_circle: tests_resources_probes_python_failing.py/status failed (None)",
                                    ]
                                }
                            },
                            {
                                "pass": {
                                    "children": [
                                        ":green_circle: tests_resources_probes_python_passing.py/bundle passed",
                                        ":green_circle: tests_resources_probes_python_passing.py/show_unit passed",
                                        ":green_circle: tests_resources_probes_python_passing.py/status passed",
                                    ]
                                }
                            },
                        ]
                    }
                },
            ]
        }
    }

    # GIVEN The results for 2 python probes (passing and failing)
    mocked_results = []
    mocked_results.extend(probe_results("/fake/path", "tests_resources_probes_python_failing.py", False))
    mocked_results.extend(probe_results("/fake/path", "tests_resources_probes_python_passing.py", True))
    # WHEN the probe results are aggregated and placed in a tree with the `--verbose` option
    output_fmt = OutputFormat(False, "json", ["all"], exception_logging=False)
    aggregator = ProbeResultAggregator(mocked_results, output_fmt)
    aggregator.assemble_trees()
    # THEN We get all the groupings
    assert json.loads(aggregator.tree.to_json()) == expected_json


if __name__ == "__main__":
    test_assemble_tree_verbose()
