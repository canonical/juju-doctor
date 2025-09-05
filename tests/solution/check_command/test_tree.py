import json
from typing import Dict, List

from typer.testing import CliRunner

from juju_doctor.main import app
from juju_doctor.probes import ROOT_NODE_TAG


def assert_tree_structure(
    actual_tree: List[Dict[str, Dict]], expected_tree: List[Dict[str, Dict]]
):
    """Iterate through each node in the expected_tree and compare to the actual_tree."""
    for expected in expected_tree:
        for key, value in expected.items():
            node_found = False
            for node in actual_tree:
                if key not in node:
                    continue
                node_found = True
                if "children" not in value:
                    continue
                expected_children = value["children"]
                actual_children = node[key]["children"]
                assert len(actual_children) == len(expected_children), (
                    f"Child count mismatch for '{key}'."
                )
                for expected_child in expected_children:
                    for child_key in expected_child.keys():
                        child_found = any(
                            child_key in actual_child for actual_child in actual_children
                        )
                        assert child_found, f"Child '{child_key}' not found in '{key}'."
                break

            assert node_found, f"Key '{key}' not found in nodes."


def test_check_groups_by_parent():
    # GIVEN multiple Ruleset probes
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/ruleset/dir.yaml",
        "--probe=file://tests/resources/probes/ruleset/nested.yaml",
        "--probe=file://tests/resources/probes/ruleset/scriptlet.yaml",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    check_result = json.loads(result.output)
    # AND there is one parent node (with children nodes) per Ruleset
    nodes = check_result[ROOT_NODE_TAG]["children"]
    expected_tree = [
        {
            "RuleSet - test directory of probes": {
                "children": [
                    {
                        "RuleSet - test failing probe": {
                            "children": [{"🔴 tests_resources_probes_python_failing.py": {}}]
                        }
                    },
                    {"🟢 tests_resources_probes_ruleset_small-dir/passing.py": {}},
                ]
            }
        },
        {
            "RuleSet - test nested rulesets": {
                "children": [
                    {
                        "RuleSet - test scriptlet": {
                            "children": [
                                {"🔴 tests_resources_probes_python_failing.py": {}},
                                {"🟢 tests_resources_probes_python_passing.py": {}},
                            ]
                        }
                    }
                ]
            }
        },
        {
            "RuleSet - test scriptlet": {
                "children": [
                    {"🔴 tests_resources_probes_python_failing.py": {}},
                    {"🟢 tests_resources_probes_python_passing.py": {}},
                ]
            }
        },
    ]
    assert_tree_structure(nodes, expected_tree)


def test_check_probes_and_builtins():
    # GIVEN a Ruleset with probes and builtins
    runner = CliRunner()
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/failing.py",
        "--probe=file://tests/resources/probes/ruleset/builtins.yaml",
        "--status=tests/resources/artifacts/status.yaml",
        "--bundle=tests/resources/artifacts/bundle.yaml",
        "--show-unit=tests/resources/artifacts/show-unit.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    check_result = json.loads(result.output)
    # AND there are nodes for both probes and builtins
    nodes = check_result[ROOT_NODE_TAG]["children"]
    expected_tree = [
        {
            "RuleSet - test builtins": {
                "children": [
                    {"🟢 tests_resources_probes_ruleset_builtins.yaml@builtins:applications": {}},
                    {"🟢 tests_resources_probes_ruleset_builtins.yaml@builtins:offers": {}},
                    {"🟢 tests_resources_probes_ruleset_builtins.yaml@builtins:relations": {}},
                ]
            }
        },
        {"🔴 tests_resources_probes_python_failing.py": {}},
    ]
    assert_tree_structure(nodes, expected_tree)
