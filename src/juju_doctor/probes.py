"""Helper module to wrap and execute probes."""

import importlib.util
import inspect
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from uuid import UUID, uuid4

import fsspec
import yaml
from rich.console import Console
from rich.logging import RichHandler
from treelib.tree import Tree

from juju_doctor.artifacts import Artifacts
from juju_doctor.fetcher import FileExtensions, copy_probes, parse_terraform_notation

SUPPORTED_PROBE_TYPES = ["status", "bundle", "show_unit"]

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

console = Console()


def _read_file(filename: Path) -> Optional[Dict]:
    """Read a file into a string."""
    try:
        with open(str(filename), "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        log.warning(f"Error: File '{filename}' not found.")
    except yaml.YAMLError as e:
        log.warning(f"Error: Failed to parse YAML in '{filename}': {e}")
    except Exception as e:
        log.warning(f"Unexpected error while reading '{filename}': {e}")
    return None


@dataclass
class Probe:
    """A probe that can be executed via juju-doctor.

    For example, instantiate a Probe with:
        Probe(
            path=PosixPath('/tmp/probes_passing.py')
            probes_root=PosixPath('/tmp')
        )
    """

    path: Path  # relative path in the temporary folder
    probes_root: Path  # temporary folder
    probes_chain: str = ""  # probe call chain with format /uuid/uuid/uuid
    uuid: UUID = field(default_factory=uuid4)

    @property
    def name(self) -> str:
        """Return the sanitized name of the probe by replacing `/` with `_`.

        This converts the probe's path relative to the root directory into a string format
        suitable for use in filenames or identifiers.
        """
        return self.path.relative_to(self.probes_root).as_posix()

    def get_chain(self) -> str:
        """Append the current probes uuid to the chain."""
        return f"{self.probes_chain}/{self.uuid}"

    @staticmethod
    def from_url(url: str, probes_root: Path, probes_chain: str = "") -> List["Probe"]:
        """Build a set of Probes from a URL.

        This function parses the URL to construct a generic 'filesystem' object,
        that allows us to interact with files regardless of whether they are on
        local disk or on GitHub.

        Then, it copies the parsed probes to a subfolder inside 'probes_root', and
        return a list of Probe items for each probe that was copied.

        Args:
            url: a string representing the Probe's URL.
            probes_root: the root folder for the probes on the local FS.
            probes_chain: the call chain of probes with format /uuid/uuid/uuid.
        """
        # Get the fsspec.AbstractFileSystem for the Probe's protocol
        parsed_url = urlparse(url)
        url_without_scheme = parsed_url.netloc + parsed_url.path
        url_flattened = url_without_scheme.replace("/", "_")
        match parsed_url.scheme:
            case "file":
                path = Path(url_without_scheme)
                filesystem = fsspec.filesystem(protocol="file")
            case "github":
                branch = parsed_url.query or "main"
                org, repo, path = parse_terraform_notation(url_without_scheme)
                path = Path(path)
                filesystem = fsspec.filesystem(
                    protocol="github", org=org, repo=repo, sha=f"refs/heads/{branch}"
                )
            case _:
                raise NotImplementedError

        probes = []
        probe_paths = copy_probes(filesystem, path, probes_destination=probes_root / url_flattened)
        for probe_path in probe_paths:
            probe = Probe(probe_path, probes_root, probes_chain)
            if probe.path.suffix.lower() in FileExtensions.ruleset:
                ruleset = RuleSet(probe)
                ruleset_probes = ruleset.aggregate_probes()
                log.info(f"Fetched probes: {ruleset_probes}")
                probes.extend(ruleset_probes)
            else:
                log.info(f"Fetched probe: {probe}")
                probes.append(probe)

        return probes

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
            if name in SUPPORTED_PROBE_TYPES
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
class OutputFormat:
    """Track the output format for the application."""
    verbose: bool
    format: Optional[str]
    grouping: List[str]
    exception_logging: bool


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

    def text(self, output_fmt: OutputFormat) -> str:
        """Probe results (formatted as Pretty-print) as a string."""
        green = EmojiTree.green
        red = EmojiTree.red
        if self.passed:
            return f"{green} {self.probe_name} passed"
        # If the probe failed
        if output_fmt.verbose:
            if output_fmt.exception_logging:
                console.print(f"[b]Exception[/b] ({self.probe_name}): {self.exception}")
            return f"{red} {self.probe_name} failed"
        msg = self.truncate_exception_msg(str(self.exception), width=40)
        return f"{red} {self.probe_name} failed ({msg})"


class RuleSet:
    """Represents a set of probes defined in a ruleset configuration file.

    Supports recursive aggregation of probes, handling scriptlets and nested rulesets.
    """

    def __init__(self, probe: Probe, name: Optional[str] = None):
        """Initialize a RuleSet instance.

        Args:
            probe: The Probe representing the ruleset configuration file.
            name: The name of the ruleset.
        """
        self.probe = probe
        self.name = name or self.probe.name

    def aggregate_probes(self) -> List[Probe]:
        """Obtain all the probes from the RuleSet.

        This method is recursive when it finds another RuleSet probe and returns
        a list of probes that were found after traversing all the probes in the ruleset.
        """
        content = _read_file(self.probe.path)
        if not content:
            return []
        ruleset_probes = content.get("probes", [])
        probes = []
        for ruleset_probe in ruleset_probes:
            match ruleset_probe["type"]:
                # TODO We currently do not handle file extension validation.
                #   i.e. we trust an author to put a ruleset if they specify type: ruleset
                case "directory" | "scriptlet":  # TODO Support a dir type since UX feels weird without?
                    probes.extend(
                        Probe.from_url(ruleset_probe["url"], self.probe.probes_root, self.probe.get_chain())
                    )
                case "ruleset":
                    if ruleset_probe.get("url", None):
                        nested_ruleset_probes = Probe.from_url(
                            ruleset_probe["url"],
                            self.probe.probes_root,
                            self.probe.get_chain(),
                        )
                        # If the probe is a directory of probes, append and continue to the next probe
                        if len(nested_ruleset_probes) > 1:
                            probes.extend(nested_ruleset_probes)
                            continue
                        # Recurses until we no longer have Ruleset probes
                        for nested_ruleset_probe in nested_ruleset_probes:
                            ruleset = RuleSet(nested_ruleset_probe)
                            derived_ruleset_probes = ruleset.aggregate_probes()
                            log.info(f"Fetched probes: {derived_ruleset_probes}")
                            probes.extend(derived_ruleset_probes)
                    else:
                        # TODO "built-in" directives, e.g. "apps/has-relation" or "apps/has-subordinate"
                        log.info(f"Found built-in probe config: \n{ruleset_probe.get('with', None)}")
                        raise NotImplementedError

                case _:
                    raise NotImplementedError

        return probes


class EmojiTree(Tree):
    """A subclass of treelib.Tree that renders emoji shortcodes."""
    red = ":red_circle:"
    green = ":green_circle:"
    EMOJI_MAP = {
        green: "🟢",
        red: "🔴",
    }

    def show(self, *args, **kwargs):
        """Overrides show to replace emoji shortcodes with actual emojis."""
        output = super().show(*args, stdout=False)  # Get tree output as string
        if output:
            for shortcode, emoji in self.EMOJI_MAP.items():
                output = output.replace(shortcode, emoji)  # Replace shortcodes with emojis
        else:
            output = "Error: No tree output available."
        if kwargs.get("stdout", True):
            console.print(output)


        output = super().show(*args, stdout=False)  # Get tree output as string

        # Check if output is None, and handle the case if it is
        if output is not None:
            for shortcode, emoji in self.EMOJI_MAP.items():
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
        self.tree = EmojiTree()
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
        grouping = self.groups if self.output_fmt.grouping == ["all"] else self.output_fmt.grouping
        for group in grouping:
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
