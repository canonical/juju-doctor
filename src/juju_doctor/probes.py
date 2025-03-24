"""Helper module to wrap and execute probes."""

import importlib.util
import inspect
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.error import URLError
from urllib.parse import ParseResult, urlparse
from uuid import uuid4

import fsspec
from rich.console import Console
from rich.logging import RichHandler
from treelib import Tree

from juju_doctor.artifacts import Artifacts

SUPPORTED_PROBE_TYPES = ["status", "bundle", "show_unit"]

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

console = Console()


def probe_name_as_posix(destination: Path, rel_path: Path) -> str:
    """Return the relative path of the Probe to use as its name."""
    return rel_path.relative_to(destination).as_posix()


@dataclass
class Probe:
    """A probe that can be executed via juju-doctor."""

    name: str
    uri: str
    original_path: Path  # path in the source folder
    path: Path  # path in the temporary folder

    @property
    def uuid(self):
        """Unique probe identifier in UUID4 format."""
        return uuid4()

    def get_functions(self) -> Dict:
        """Dynamically load a Python script from self.path, making its functions available.

        We need to import the module dynamically with the 'spec' mechanism because the path
        of the probe is only known at runtime.

        Only returns the supported 'status', 'bundle', and 'show_unit' functions (if present).
        """
        module_name = "probe"
        # Get the spec (metadata) for Python to be able to import the probe as a module
        spec = importlib.util.spec_from_file_location(module_name, self.path.resolve())
        if not spec:
            raise ValueError(f"Probe not found at its 'path': {self}")
        # Import the module dynamically
        module = importlib.util.module_from_spec(spec)
        if spec.loader:
            spec.loader.exec_module(module)
        # Return the functions defined in the probe module
        return {
            name: func
            for name, func in inspect.getmembers(module, inspect.isfunction)
            if name in ["status", "bundle", "show_unit"]
        }

    def run(self, artifacts: Artifacts) -> List["ProbeResults"]:
        """Execute each Probe function that matches the names: `status`, `bundle`, or `show_unit`."""
        # Silence the result printing if needed
        results: List[ProbeResults] = []
        for func_name, func in self.get_functions().items():
            # Get the artifact needed by the probe, and fail if it's missing
            artifact = getattr(artifacts, func_name)
            if not artifact:
                results.append(
                    ProbeResults(
                        probe=self,
                        func_name=func_name,
                        passed=False,
                        exception=Exception(f"No '{func_name}' artifacts have been provided."),
                    )
                )
                continue
            # Run the probe fucntion, and record its result
            try:
                func(artifact)
            except BaseException as e:
                results.append(ProbeResults(probe=self, func_name=func_name, passed=False, exception=e))
            else:
                results.append(ProbeResults(probe=self, func_name=func_name, passed=True))
        return results


@dataclass
class ProbeResults:
    """A helper class to wrap results for a Probe."""

    probe: Probe
    func_name: str
    passed: bool
    exception: Optional[BaseException] = None

    @property
    def probe_name(self) -> str:
        """Probe name and the function name, matching a supported artifact."""
        return f"{self.probe.name}/{self.func_name}"

    @property
    def status(self) -> str:
        """Result of the probe."""
        return "pass" if self.passed else "fail"

    def truncate_exception_msg(self, msg: str, width: int = 40) -> str:
        """Truncate the exception message to fit within the specified width."""
        if len(msg) > width - 3:  # -3 for "..."
            return msg[: width - 3] + "..."
        return msg

    def print(self, verbose: bool):
        """Pretty-print the Probe results."""
        if self.passed:
            console.print(f"🟢 {self.probe_name} passed")
            return
        # or else, if the probe failed
        if verbose:
            console.print(f"🔴 {self.probe_name} failed")
            console.print(f"[b]Exception[/b]: {self.exception}")
        else:
            console.print(f"🔴 {self.probe_name} failed ", end="")
            console.print(
                f"({self.exception}",
                overflow="ellipsis",
                no_wrap=True,
                width=40,
                end="",
            )
            console.print(")")

    def text(self, verbose: bool) -> str:
        """Probe results (formatted as Pretty-print) as a string."""
        if self.passed:
            return f"🟢 {self.probe_name} passed"

        # If the probe failed
        if verbose:
            console.print(f"[b]Exception[/b] ({self.probe_name}): {self.exception}")
            return f"🔴 {self.probe_name} failed"

        msg = self.truncate_exception_msg(str(self.exception), width=40)
        return f"🔴 {self.probe_name} failed ({msg})"


class ProbeResultAggregator:
    """Aggregates and groups probe results based on metadata such as status, parent path, and type."""

    def __init__(self, grouping: str, results: List[ProbeResults]):
        """Prepare the aggregated results and its tree representation."""
        self.tree = Tree()
        self.tree.create_node("Results", "root")  # root node
        self.grouping = grouping  # TODO Make grouping a Dataclass or Enum so we dont allow unsupported ones
        self.results = results
        self.grouped_by_status = defaultdict(list)
        self.grouped_by_artifact = defaultdict(list)
        self.grouped_by_parent = defaultdict(list)
        self._group_results()

    def _group_results(self):
        """Groups results by status, parent directory, and probe type."""
        for result in self.results:
            self.grouped_by_status[result.status].append(result)
            self.grouped_by_artifact[result.func_name].append(result)
            self.grouped_by_parent[result.probe.original_path.parent].append(result)

    def _get_by_status(self, status: str) -> List[Dict]:
        return self.grouped_by_status.get(status, [])

    def _get_by_artifact(self, probe_type: str) -> List[Dict]:
        return self.grouped_by_artifact.get(probe_type, [])

    def _get_by_parent(self, parent: Path) -> List[Dict]:
        return self.grouped_by_parent.get(parent, [])

    def _build_tree(self, grouping: str, verbose: bool) -> Tree:
        # TODO tree.show() has powerful filter options:
        #     filter: Optional[Callable[[Node], bool]] = None,
        #     key: Optional[Callable[[Node], Node]] = None,
        #     reverse: bool = False,
        #     line_type: str = "ascii-ex",
        #     data_property: Optional[str] = None,
        #     sorting: bool = True,
        # ):
        # TODO We can use the `data_property` arg to specify what we want to show. For example:
        #   tree.create_node(..., data=ProbeResult)
        #   tree.show(data_property=text)  -> Would require `verbose` to be an attribute of ProbeResult
        # This would allow us to switch between what we want to show in the tree, e.g. `text` vs. `text_bold`
        tree = Tree()
        tree.create_node(grouping.capitalize(), grouping)  # root node
        grouped_attr = getattr(self, f"grouped_by_{grouping}")
        for key, values in grouped_attr.items():
            tree.create_node(key, f"{grouping}-{key}", parent=grouping)
            for probe_result in values:
                tree.create_node(
                    probe_result.text(verbose=verbose), probe_result.probe.uuid, parent=f"{grouping}-{key}"
                )
        return tree

    def print_results(self, format: Optional[str], verbose: bool):
        """Handle the formating and logging of probe results."""
        total_passed = len(self._get_by_status("pass"))
        total_failed = len(self._get_by_status("fail"))
        match format:
            case "json":
                json_result = {"passed": total_passed, "failed": total_failed}
                # self.tree.to_json(with_data=True)
                console.print(json.dumps(json_result))
            case "tree":
                # self.tree.save2file('archive.txt')
                for grouping in ["status", "artifact", "parent"]:
                    tree = self._build_tree(grouping, verbose)
                    self.tree.paste("root", tree)  # inserts the grouping's subtree into the aggregated tree
                self.tree.show(line_type="ascii-exr")  # 'ascii', 'ascii-ex', 'ascii-exr', 'ascii-em', 'ascii-emv', 'ascii-emh'
                console.print(f"\nTotal: 🟢 {total_passed} 🔴 {total_failed}")
            case _:
                for r in self.results:
                    if not format:
                        r.print(verbose=verbose)
                console.print(f"\nTotal: 🟢 {total_passed} 🔴 {total_failed}")


class ProbeFS:
    """Manage the relevant paths that a Probe or a Probe runner would require."""

    def __init__(self, destination: Path, uri: str):
        """Parse the URI to determine relative and local paths, ensuring proper formatting.

        Args:
            destination (Path): the file path for the probes on the local FS.
            uri (str): a string representing the Probe's URI.
        """
        self.destination: Path = destination
        self.uri: str = uri
        self.parsed_uri: ParseResult = urlparse(uri)
        self._rel_path: str = self.parsed_uri.netloc + self.parsed_uri.path
        self.rel_path: Path = Path(self._rel_path)  # Sanitize the TF dir notation `//` in the path
        self.subfolder: str = self._rel_path.replace("/", "_")
        self.local_path: Path = self.destination / self.subfolder

    @property
    def filesystem(self) -> fsspec.AbstractFileSystem:
        """Return an fsspec.AbstractFileSystem for the Probe's protocol."""
        # Extract the branch name if present
        if self.parsed_uri.query:
            branch = self.parsed_uri.query
        else:
            branch = "main"

        match self.parsed_uri.scheme:
            case "file":
                filesystem = fsspec.filesystem(protocol="file")
            case "github":
                try:
                    # Extract the org and repository from the relative path
                    org_and_repo, path = self._rel_path.split("//")
                    self.rel_path = Path(path)
                    org, repo = org_and_repo.split("/")
                except ValueError:
                    raise URLError(
                        f"Invalid URI format: {self.uri}. Use '//' to define 1 sub-directory "
                        "and specify at most 1 branch."
                    )
                filesystem = fsspec.filesystem(
                    protocol="github", org=org, repo=repo, sha=f"refs/heads/{branch}"
                )
            case _:
                raise NotImplementedError

        return filesystem

    def probe_name_as_posix(self) -> str:
        """Return the relative path of the Probe to use as its name."""
        return probe_name_as_posix(self.destination, self.rel_path)
