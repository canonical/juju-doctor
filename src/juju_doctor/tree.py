"""Helper module for displaying the result in a tree."""

import json
import logging
from typing import Dict, List, Optional

from rich.console import Console
from rich.logging import RichHandler
from treelib.tree import Tree

from juju_doctor.constants import ROOT_NODE_ID, ROOT_NODE_TAG
from juju_doctor.probes import AssertionStatus, Probe
from juju_doctor.results import CheckFormat, FormatTracker

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)
console = Console()


class ResultAggregator:
    """Build a tree representation of probe results and display it."""

    def __init__(
        self,
        probes: List[Probe],
        output_fmt: FormatTracker,
        tree: Optional[Tree] = None,
    ):
        """Receive probes and instantiate the tree representation.

        Leaf nodes will be created (per probe result) from the parent (calling) probes.
        """
        self._probes = probes
        self._output_fmt = output_fmt
        self._exceptions = []
        self._tree = tree if tree is not None else Tree()
        if not self._tree.nodes:
            self._tree.create_node(ROOT_NODE_TAG, ROOT_NODE_ID)

    def _build_tree(self) -> Dict[str, int]:
        """Create the tree structure for aggregated results.

        Create a new node in the tree per probe with an assertion summary.
        """
        pass_key = AssertionStatus.PASS.value
        fail_key = AssertionStatus.FAIL.value
        results = {pass_key: 0, fail_key: 0}
        for probe in self._probes:
            node_info = probe.result_text(self._output_fmt)
            self._exceptions.extend(node_info.exception_msgs)
            if probe.succeeded():
                results[pass_key] += 1
            else:
                results[fail_key] += 1

            if not probe.is_root_node:
                self._tree.create_node(
                    node_info.node_tag, str(probe.uuid), str(probe.get_parent()), probe
                )
            else:
                if str(probe.uuid) in self._tree:
                    self._tree.update_node(str(probe.uuid), tag=node_info.node_tag)
                else:
                    self._tree.create_node(
                        node_info.node_tag, str(probe.uuid), self._tree.root, probe
                    )
        return results

    def print_results(self):
        """Handle the formatting and logging of probe results."""
        results = self._build_tree()
        passed = results[AssertionStatus.PASS.value]
        failed = results[AssertionStatus.FAIL.value]
        total = passed + failed
        match self._output_fmt.format.lower():
            case CheckFormat.tree.value:
                self._tree.show()
                for e in filter(None, self._exceptions):
                    console.print(e)
                pass_string = f"🟢 {passed}/{total}" if passed != 0 else ""
                fail_string = f"🔴 {failed}/{total}" if failed != 0 else ""
                if pass_string or fail_string:
                    console.print(f"\nTotal: {pass_string} {fail_string}")
            case CheckFormat.json.value:
                tree_json = json.loads(self._tree.to_json())
                meta_json = {
                    "passed": passed,
                    "failed": failed,
                }
                if self._output_fmt.verbose:
                    tree_json["exceptions"] = self._exceptions
                tree_json.update(meta_json)
                print(json.dumps(tree_json))
