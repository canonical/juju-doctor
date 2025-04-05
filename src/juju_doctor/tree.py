"""Helper module for displaying the result in a tree."""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from rich.console import Console
from rich.logging import RichHandler
from treelib.tree import Tree

from juju_doctor.probes import ProbeResult

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)
console = Console()


@dataclass
class OutputFormat:
    """Track the output format for the application."""

    verbose: bool
    exception_logging: bool
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

    def __init__(self, results: List[ProbeResult], output_fmt: OutputFormat):
        """Prepare the aggregated results and its tree representation."""
        self.results = results
        self.output_fmt = output_fmt
        self.exceptions = []
        self.tree = RichTree()
        self.tree.create_node("Results", "root")  # root node
        self.grouped_by_status = defaultdict(list)
        self._group_results()

    def _group_results(self):
        """Group results by status, and probe type."""
        for result in self.results:
            self.grouped_by_status[result.status].append(result)

    def _get_by_status(self, status: str) -> List[Dict]:
        return self.grouped_by_status.get(status, [])

    def _build_tree(self):
        # TODO Add doctsring
        for key, values in self.grouped_by_status.items():
            self.tree.create_node(str(key), key, parent="root")
            store = {}
            for probe_result in values:
                node_name, probe_exception = probe_result.get_text(self.output_fmt)
                if probe_exception:
                    self.exceptions.append(probe_exception)

                def sort_and_group_by_parent(store: Dict, probe_result: ProbeResult):
                    # TODO Maybe grouping with .split("/") for each lowest-level "children" in tree
                    #   sort the probe names and split for common parent paths
                    #   This assumes that the tree is already created, but we likely want to do this before
                    #   with the store variable below
                    # We can still get duplicate probes e.g. ruleset/all.yaml so we need a way to
                    #   show the origin of each by resolving the top-level probe (by UUID) next to each probe if there are duplicates
                    CONTINUE HERE
                    for part in probe_result.probe_name.split("/"):
                        store[part] = probe_result
                    return store

                store = sort_and_group_by_parent(store, probe_result)
                # To ensure the node ID is unique across all trees, we build a string including the
                # probe chain, grouping, and probe function
                self.tree.create_node(
                    node_name,
                    probe_result.probe.get_chain() + f"/{probe_result.func_name}",
                    parent=key,
                )

    def print_results(self):
        """Handle the formating and logging of probe results."""
        total_passed = len(self._get_by_status("pass"))
        total_failed = len(self._get_by_status("fail"))
        match self.output_fmt.format:
            case None:
                self._build_tree()
                self.tree.show()
                for e in self.exceptions:
                    console.print(e)
                console.print(f"\nTotal: 🟢 {total_passed} 🔴 {total_failed}")
            case "json":
                self._build_tree()
                tree_json = json.loads(self.tree.to_json())
                meta_json = {
                    "passed": total_passed,
                    "failed": total_failed,
                    "exceptions": self.exceptions,
                }
                tree_json.update(meta_json)
                print(json.dumps(tree_json))
            case _:
                raise NotImplementedError
