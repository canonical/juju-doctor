# ruff: noqa: E501

import json
from pathlib import Path
from typing import Dict, List

from juju_doctor.probes import (
    SUPPORTED_PROBE_FUNCTIONS,
    AssertionStatus,
    Probe,
    ProbeAssertionResult,
)
from juju_doctor.tree import OutputFormat, ProbeResultAggregator


def probe_results(tmp_path: str, probe_name: str, passed: bool):
    results = []
    for func_name in SUPPORTED_PROBE_FUNCTIONS:
        results.append(
            ProbeAssertionResult(
                probe=Probe(
                    path=Path(f"{tmp_path}/probes/{probe_name}"),
                    probes_root=Path(f"{tmp_path}/probes"),
                ),
                func_name=func_name,
                passed=passed,
            )
        )
    return {probe_name: results}


def test_build_tree_status_group():
    expected_json = [
        {
            AssertionStatus.FAIL.value: {
                "children": ["🔴 probes_python_failing.py (✖️ status, ✖️ bundle, ✖️ show_unit)"]
            }
        },
        {AssertionStatus.PASS.value: {"children": ["🟢 probes_python_passing.py (✔️ status, ✔️ bundle, ✔️ show_unit)"]}},
    ]

    # GIVEN The results for 2 python probes (passing and failing)
    mocked_results: Dict[str, List[ProbeAssertionResult]] = {}
    mocked_results.update(probe_results("/fake/path", "probes_python_failing.py", False))
    mocked_results.update(probe_results("/fake/path", "probes_python_passing.py", True))
    # WHEN The probe results are aggregated and placed in a tree
    output_fmt = OutputFormat(False, "json")
    aggregator = ProbeResultAggregator(mocked_results, output_fmt)
    aggregator._build_tree()
    # THEN The tree result is correctly grouped and the probe assertions are displ
    actual_json = json.loads(aggregator._tree.to_json())["Results"]["children"]
    assert actual_json == expected_json
