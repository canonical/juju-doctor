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

    red = ":red_circle:"
    green = ":green_circle:"

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
        for probe_result in probe_results:
            status = (
                AssertionStatus.FAIL.value
                if any(p.status == AssertionStatus.FAIL.value for p in probe_result)
                else AssertionStatus.PASS.value
            )
            self._grouped_by_status[status].append(probe_result)

    def _get_total_by_status(self, status: AssertionStatus) -> List[List[ProbeAssertionResult]]:
        # TODO This is unnecessary computation when we could just track the results within the loop in _build_tree
        # TODO It is also incorrect and should count the total assertions pass/fail regardless of the overall probe's success
        results = [
            [assertion_result.status for assertion_result in probe_result]
            for probe_result in self._grouped_by_status.get(status, [])
        ]
        return sum(entry.count(status) for entry in results)

    def _build_tree(self):
        # TODO Add doctsring
        for status, probe_results in self._grouped_by_status.items():
            self._tree.create_node(str(status), status, parent="root")
            # create a new node once per defined probe instead of per function name
            for probe_result in probe_results:
                function_statuses = {"pass": [], "fail": []}
                for assertion_result in probe_result:
                    node_tag, probe_exception = assertion_result.get_text(self._output_fmt)
                    if probe_exception:
                        self._exceptions.append(probe_exception)
                    status = "pass" if assertion_result.passed else "fail"
                    function_statuses[status].append(assertion_result.func_name)
                node_tag = node_tag + f" ({', '.join(function_statuses[status])})"
                self._tree.create_node(node_tag, assertion_result.probe.get_chain(), status)

    def print_results(self):
        """Handle the formating and logging of probe results."""
        total_passed = self._get_total_by_status(AssertionStatus.PASS.value)
        total_failed = self._get_total_by_status(AssertionStatus.FAIL.value)
        match self._output_fmt.format:
            case None:
                self._build_tree()
                self._tree.show()
                for e in filter(None, self._exceptions):
                    console.print(e)
                console.print(f"\nTotal: 🟢 {total_passed} 🔴 {total_failed}")
            case "json":
                self._build_tree()
                tree_json = json.loads(self._tree.to_json())
                # TODO see if treelib.Tree.to_json has an option to remove the "children" keys
                meta_json = {
                    "passed": total_passed,
                    "failed": total_failed,
                }
                if self._output_fmt.verbose:
                    meta_json.update({"exceptions": self._exceptions})
                tree_json.update(meta_json)
                print(json.dumps(tree_json))
            case _:
                raise NotImplementedError
