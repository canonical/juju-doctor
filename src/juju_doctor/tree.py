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
    }


class RichTree(Tree):
    """A subclass of treelib.Tree that renders styled text from shortcodes."""

    def show(self, *args, **kwargs):
        """Overrides Tree::show to replace shortcodes with styled text."""
        output = super().show(*args, stdout=False)  # Get tree output as string
        if output:
            for shortcode, styled_text in OutputFormat.rich_map.items():
                output = output.replace(shortcode, styled_text)
        else:
            output = "Error: No tree output available."
        if kwargs.get("stdout", True):
            console.print(output)


class ProbeResultAggregator:
    """Aggregate and group probe results based on metadata."""

    def __init__(
        self, probe_results: Dict[str, List[ProbeAssertionResult]], output_fmt: OutputFormat
    ):
        """Prepare the aggregated results and its tree representation."""
        self._output_fmt = output_fmt
        self._exceptions = []
        self._tree = RichTree()
        self._tree.create_node("Results", "root")  # root node
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
        for status, probe_results in self._grouped_by_status.items():
            self._tree.create_node(str(status), status, parent="root")
            for probe_result in probe_results:
                node_tag = ""
                function_statuses = {"pass": [], "fail": []}
                # gather failed assertions and exceptions
                assertion_result = None
                for assertion_result in probe_result:
                    node_tag, probe_exception = assertion_result.get_text(self._output_fmt)
                    results[assertion_result.status] += 1
                    if probe_exception:
                        self._exceptions.append(probe_exception)
                    function_statuses[assertion_result.status].append(assertion_result.func_name)
                    if not assertion_result.passed:
                        node_tag += f" ({', '.join(function_statuses[status])})"
                # The `probe` attribute for each `assertion_result` in a given `probe_result` will
                # be identical, so we can create the tree node with the last `assertion_result`
                if assertion_result:
                    self._tree.create_node(node_tag, assertion_result.probe.get_chain(), status)

        return results

    def print_results(self):
        """Handle the formating and logging of probe results."""
        results = self._build_tree()
        passed = results[AssertionStatus.PASS.value]
        failed = results[AssertionStatus.FAIL.value]
        total = passed + failed
        match self._output_fmt.format:
            case None:
                self._tree.show()
                for e in filter(None, self._exceptions):
                    console.print(e)
                console.print(
                    f"\nTotal: 🟢 {passed}/{total} 🔴 {failed}/{total}"
                )
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
