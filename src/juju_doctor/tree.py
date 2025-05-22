"""Helper module for displaying the result in a tree."""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from rich.console import Console
from rich.logging import RichHandler
from treelib.tree import Tree

from juju_doctor.probes import AssertionStatus, ProbeAssertionResult

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)
console = Console()


@dataclass
class OutputFormat:
    """Track the output format for the application."""

    verbose: bool
    format: Optional[str]
    rich_map = {
        "green": "🟢",
        "red": "🔴",
        "check_mark": "✔️",
        "multiply": "✖️",
    }


class ProbeResultAggregator:
    """Aggregate and group probe results based on metadata."""

    def __init__(
        self, probe_results: Dict[str, List[ProbeAssertionResult]], output_fmt: OutputFormat, root_tree: Tree = None
    ):
        """Prepare the aggregated results and its tree representation.
        
        TODO root_tree docstring"""
        self._output_fmt = output_fmt
        self._exceptions = []
        # TODO We have to be careful to test this or we can be opinionated and say that we always accept an external root. Docstring this, but it will make ProbeResultAggregator less usable standalone
        if not root_tree:
            self._tree = Tree()
            self._tree.create_node("Results", "root")  # root node
        else:
            self._tree = root_tree
        self._grouped_by_status = defaultdict(list)
        self._group_results(probe_results)

    def _group_results(self, probe_results: Dict[str, List[ProbeAssertionResult]]):
        """Group each probe assertion result by pass/fail."""
        for probe_result in probe_results.values():
            status = (
                AssertionStatus.FAIL.value
                if any(p.status == AssertionStatus.FAIL.value for p in probe_result)
                else AssertionStatus.PASS.value
            )
            self._grouped_by_status[status].append(probe_result)

    def _build_tree(self) -> Dict[str, int]:
        """Create the tree structure for aggregated results.

        Create a new node in the tree once per defined probe with an assertion summary.
        """
        results = {AssertionStatus.PASS.value: 0, AssertionStatus.FAIL.value: 0}
        for probe_status, probe_results in self._grouped_by_status.items():
            for probe_result in probe_results:
                node_tag = ""
                func_statuses = []
                assertion_result = None
                # gather failed assertions and exceptions
                for assertion_result in probe_result:
                    node_tag, probe_exception = assertion_result.get_text(self._output_fmt)
                    results[assertion_result.status] += 1
                    if probe_exception:
                        self._exceptions.append(probe_exception)
                    symbol = (
                        self._output_fmt.rich_map["check_mark"]
                        if assertion_result.status == AssertionStatus.PASS.value
                        else self._output_fmt.rich_map["multiply"]
                    )
                    func_statuses.append(f"{symbol} {assertion_result.func_name}")


                if self._output_fmt.verbose:
                    node_tag += f" ({', '.join(func_statuses)})"
                # The `probe` attribute for each `assertion_result` in a given `probe_result` will
                # be identical, so we can create the tree node with the last `assertion_result`
                if assertion_result:
                    # TODO We need to check if the probe is already added before adding since it may be a root probe
                    if not assertion_result.probe.is_root:
                        self._tree.create_node(
                            node_tag, assertion_result.probe.get_chain(), assertion_result.probe.root_uuid
                        )
                    else:
                        self._tree.update_node(assertion_result.probe.get_chain(), tag=node_tag)

        return results

    def print_results(self):
        """Handle the formatting and logging of probe results."""
        results = self._build_tree()
        passed = results[AssertionStatus.PASS.value]
        failed = results[AssertionStatus.FAIL.value]
        total = passed + failed
        match self._output_fmt.format:
            case None:
                self._tree.show()
                for e in filter(None, self._exceptions):
                    console.print(e)
                pass_string = f"🟢 {passed}/{total}" if passed != 0 else ""
                fail_string = f"🔴 {failed}/{total}" if failed != 0 else ""
                console.print(f"\nTotal: {pass_string} {fail_string}")
            case "json":
                tree_json = json.loads(self._tree.to_json())
                # TODO see if treelib.Tree.to_json has an option to remove the "children" keys
                meta_json = {
                    "passed": passed,
                    "failed": failed,
                }
                if self._output_fmt.verbose:
                    tree_json["exceptions"] = self._exceptions
                tree_json.update(meta_json)
                print(json.dumps(tree_json))
            case _:
                raise NotImplementedError
