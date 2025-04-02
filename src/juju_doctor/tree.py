"""Helper module for displaying the result in a tree."""

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.logging import RichHandler
from treelib.tree import Tree

from juju_doctor.probes import EMOJI_MAP, OutputFormat, ProbeResults

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)
console = Console()


class RichTree(Tree):
    # TODO Update with RichHandler comment
    """A subclass of treelib.Tree that renders emoji shortcodes."""
    red = ":red_circle:"
    green = ":green_circle:"

    def show(self, *args, **kwargs):
        """Overrides show to replace emoji shortcodes with actual emojis."""
        output = super().show(*args, stdout=False)  # Get tree output as string
        if output:
            for shortcode, emoji in EMOJI_MAP.items():
                output = output.replace(shortcode, emoji)  # Replace shortcodes with emojis
        else:
            output = "Error: No tree output available."
        if kwargs.get("stdout", True):
            console.print(output)

        output = super().show(*args, stdout=False)  # Get tree output as string

        # Check if output is None, and handle the case if it is
        if output is not None:
            for shortcode, emoji in EMOJI_MAP.items():
                output = output.replace(shortcode, emoji)  # Replace shortcodes with emojis
        else:
            # Handle the case where output is None, maybe log an error or set a default value
            output = "Error: No tree output available."

        if kwargs.get("stdout", False):
            console.print(output)


class ProbeResultAggregator:
    """Aggregates and groups probe results based on metadata."""

    groups = ["status", "artifact", "directory"]

    def __init__(self, results: List[ProbeResults], output_fmt: OutputFormat):
        """Prepare the aggregated results and its tree representation."""
        self.results = results
        self.output_fmt = output_fmt
        self.tree = RichTree()
        self.tree.create_node("Results", "root")  # root node
        self.grouped_by_status = defaultdict(list)
        self.grouped_by_artifact = defaultdict(list)
        self.grouped_by_directory = defaultdict(list)
        self._group_results()

    def _group_results(self):
        """Groups results by status, parent directory, and probe type."""
        for result in self.results:
            self.grouped_by_status[result.status].append(result)
            self.grouped_by_artifact[result.func_name].append(result)
            self.grouped_by_directory[result.probe.path.parent].append(result)

    def _get_by_status(self, status: str) -> List[Dict]:
        return self.grouped_by_status.get(status, [])

    def _get_by_artifact(self, probe_type: str) -> List[Dict]:
        return self.grouped_by_artifact.get(probe_type, [])

    def _get_by_parent(self, parent: Path) -> List[Dict]:
        return self.grouped_by_directory.get(parent, [])

    def _build_tree(self, group: str) -> Tree:
        tree = Tree()
        tree.create_node(group.capitalize(), group)  # sub-tree root node
        grouped_attr = getattr(self, f"grouped_by_{group}")
        for key, values in grouped_attr.items():
            tree.create_node(str(key), f"{group}-{key}", parent=group)
            for probe_result in values:
                tree.create_node(
                    probe_result.text(self.output_fmt),
                    f"{group}|{probe_result.func_name}" + probe_result.probe.get_chain(),
                    parent=f"{group}-{key}",
                )
        return tree

    def assemble_trees(self):
        """For each group, build a sub-tree which gets pasted to the root tree of results.

        Optionally display the exception logs and the tree result.
        """
        for group in self.output_fmt.grouping:
            tree = self._build_tree(group)
            self.output_fmt.exception_logging = False  # only log Exceptions once when grouping
            self.tree.paste("root", tree)  # inserts the grouping's subtree into the aggregated tree

    def print_results(self):
        """Handle the formating and logging of probe results."""
        total_passed = len(self._get_by_status("pass"))
        total_failed = len(self._get_by_status("fail"))
        match self.output_fmt.format:
            case None:
                self.assemble_trees()
                self.tree.show(line_type="ascii-exr")
                console.print(f"\nTotal: 🟢 {total_passed} 🔴 {total_failed}")
            case "json":
                self.assemble_trees()
                tree_json = json.loads(self.tree.to_json())
                tree_json.update({"passed": total_passed, "failed": total_failed})
                print(json.dumps(tree_json))
            case _:
                raise NotImplementedError
