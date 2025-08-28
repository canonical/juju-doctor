"""Helper module to wrap and execute probes."""

import importlib.util
import inspect
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import ParseResult, urlparse
from uuid import UUID, uuid4

import fsspec
import yaml
from rich.logging import RichHandler
from treelib.tree import Tree

from juju_doctor.artifacts import Artifacts
from juju_doctor.builtins import Builtin, SupportedBuiltins
from juju_doctor.fetcher import FileExtensions, copy_probes, parse_terraform_notation
from juju_doctor.results import AssertionResult, AssertionStatus, OutputFormat

SUPPORTED_PROBE_FUNCTIONS = ["status", "bundle", "show_unit"]
ROOT_NODE_ID = "root"
ROOT_NODE_TAG = "Results"

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


def _read_file(filename: Path) -> Optional[Dict]:
    """Read a yaml probe file into a dict."""
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
class FileSystem:
    """Probe filesystem information."""

    fs: fsspec.AbstractFileSystem
    path: Path


@dataclass
class NodeResultInfo:
    """Probe result information for display in a Tree node.

    Args:
        node_tag: text for displaying the Probe's identity in a node of the Tree
        exception_msgs: a list of exception messages aggregated from the Probe's function results
    """

    node_tag: str = ""
    exception_msgs: List[str] = field(default_factory=list)


@dataclass
class ProbeTree:
    """A collection of Probes in a tree format.

    Args:
        probes: a list of scriptlet probes in the tree
        tree: a treelib.Tree containing a probe per node
        builtins: a dict mapping builtin types to their calling rulesets and assertions
    """

    probes: List["Probe"] = field(default_factory=list)
    tree: Tree = field(default_factory=Tree)
    # TODO: Add a type hint like I had before Dict[str, Builtin]
    builtins: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class Probe:
    """A probe that can be executed via juju-doctor.

    Since a Python probe can be executed multiple times, we need a way to differentiate between
    the call paths. Each probe is instantiated with a UUID which is appended to the `probes_chain`
    to identify the top-level probe (and subsequent probes) that lead to this probe's execution.

    For example, for 2 probes: A and B inside a directory which is executed by probe C, their
    probe chains would be
        UUID(C)/UUID(A)
        UUID(C)/UUID(B)

    Alternatively, for 2 probes: D and E which both call probe F, their probe chains would be
        UUID(D)/UUID(F)
        UUID(E)/UUID(F)

    The probe chain ends when the probe does not call another probe.

    Args:
        path: relative file path in the temporary probes folder
        probes_root: temporary directory for all fetched probes
        probes_chain: a chain of UUIDs identifying the probe's call path
        uuid: a unique identifier for this probe among others in a treelib.Tree
        results: aggregated results for the probe's functions
    """

    path: Path
    probes_root: Path
    probes_chain: str = ""  # probe call chain with format UUID/UUID/UUID
    uuid: UUID = field(default_factory=uuid4)
    results: List[AssertionResult] = field(default_factory=list)

    @property
    def name(self) -> str:
        """Return the sanitized name of the probe by replacing `/` with `_`.

        This converts the probe's path relative to the root directory into a string format
        suitable for use in filenames or identifiers.
        """
        return self.path.relative_to(self.probes_root).as_posix()

    @property
    def is_root_node(self) -> bool:
        """A root node is a probe in a tree which was not called by another probe."""
        return self.uuid == self.root_node_uuid

    @property
    def root_node_uuid(self) -> UUID:
        """Unique identifier of this probe's original caller."""
        return UUID(self.get_chain().split("/")[0])

    def get_chain(self) -> str:
        """Get the current probe's call path with itself at the end of the chain."""
        if self.probes_chain:
            return f"{self.probes_chain}/{self.uuid}"
        return str(self.uuid)

    def get_parent(self) -> Optional[UUID]:
        """Unique identifier of this probe's parent."""
        chain = self.get_chain().split("/")
        if len(chain) > 1:
            return UUID(self.get_chain().split("/")[-2])
        return None

    @staticmethod
    def from_url(
        url: str, probes_root: Path, probes_chain: str = "", probe_tree: ProbeTree = ProbeTree()
    ) -> ProbeTree:
        """Build a set of Probes from a URL.

        This function parses the URL to construct a generic 'filesystem' object, that allows us to
        interact with files regardless of whether they are on local disk or on GitHub.

        Then, it copies the parsed probes to a subfolder inside 'probes_root', and return a list of
        Probe items for each probe that was copied.

        While traversing, a record of probes are stored in a tree. Leaf nodes will be created from
        the root of the tree for each probe result.

        Args:
            url: a string representing the Probe's URL.
            probes_root: the root folder for the probes on the local FS.
            probes_chain: the call chain of probes with format /uuid/uuid/uuid.
            probe_tree: a ProbeTree representing the discovered probes in a treelib.Tree format.
        """
        # Create a root node if it does not exist
        if not probe_tree.tree:
            probe_tree.tree.create_node(ROOT_NODE_TAG, ROOT_NODE_ID)

        parsed_url = urlparse(url)
        url_without_scheme = parsed_url.netloc + parsed_url.path
        url_flattened = url_without_scheme.replace("/", "_")
        fs = Probe._get_fs_from_protocol(parsed_url, url_without_scheme)

        probe_paths = copy_probes(fs.fs, fs.path, probes_destination=probes_root / url_flattened)
        for probe_path in probe_paths:
            probe = Probe(probe_path, probes_root, probes_chain)
            is_ruleset = probe.path.suffix.lower() in FileExtensions.RULESET.value
            if is_ruleset:
                ruleset = RuleSet(probe)

                # Gather builtins from the Ruleset and map the ruleset to builtins
                for name, ruleset_builtin in ruleset.builtins.items():
                    probe_tree.builtins.setdefault(name, {})
                    probe_tree.builtins[name].setdefault(
                        ruleset.probe.get_chain(), ruleset_builtin
                    )

                probe_tree = ruleset.aggregate_probes(probe_tree)

            else:
                if probe.is_root_node:
                    probe_tree.tree.create_node(
                        probe.name, str(probe.uuid), probe_tree.tree.root, probe
                    )
                log.info(f"Fetched probe(s) for {probe.name}: {probe}")
                probe_tree.probes.append(probe)

        return probe_tree

    @staticmethod
    def _get_fs_from_protocol(parsed_url: ParseResult, url_without_scheme: str) -> FileSystem:
        """Get the fsspec::AbstractFileSystem for the Probe's protocol."""
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

        return FileSystem(fs=filesystem, path=path)

    def get_functions(self) -> Dict:
        """Dynamically load a Python script from self.path, making its functions available.

        We need to import the module dynamically with the 'spec' mechanism because the path of the
        probe is only known at runtime.

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
            if name in SUPPORTED_PROBE_FUNCTIONS
        }

    def run(self, artifacts: Artifacts):
        """Execute each Probe function that matches the supported probe types.

        The results of each function are aggregated and assigned to the probe itself
        """
        for func_name, func in self.get_functions().items():
            # Get the artifact needed by the probe, and fail if it's missing
            artifact = getattr(artifacts, func_name)
            if not artifact:
                log.warning(
                    f"No {func_name} artifact was provided for probe: {self.path}."
                )
                continue
            # Run the probe function, and record its result
            try:
                func(artifact)
            except BaseException as e:
                self.results.append(AssertionResult(func_name, passed=False, exception=e))
            else:
                self.results.append(AssertionResult(func_name, passed=True))

    def result_text(self, output_fmt: OutputFormat) -> NodeResultInfo:
        """Probe results (formatted with Pretty-print) as text."""
        failed = False
        func_statuses = []
        exception_msgs = []
        red = output_fmt.rich_map["red"]
        green = output_fmt.rich_map["green"]
        for result in self.results:
            if not result.passed:
                failed = True
                exception_suffix = f"({self.name}/{result.func_name}): {result.exception}"
                if output_fmt.format.lower() == "json":
                    exception_msgs.append(f"Exception {exception_suffix}")
                else:
                    if output_fmt.verbose:
                        exception_msgs.append(f"[b]Exception[/b] {exception_suffix}")

            symbol = (
                output_fmt.rich_map["check_mark"]
                if result.status == AssertionStatus.PASS.value
                else output_fmt.rich_map["multiply"]
            )
            if result.func_name:
                func_statuses.append(f"{symbol} {result.func_name}")

        if failed or not self.results:
            node_tag = f"{red} {self.name}"
        else:
            node_tag = f"{green} {self.name}"
        if output_fmt.verbose:
            if func_statuses:
                node_tag += f" ({', '.join(func_statuses)})"

        return NodeResultInfo(node_tag, exception_msgs)


class RuleSet:
    """Represents a set of probes defined in a declarative configuration file.

    Supports recursive aggregation of probes, nested rulesets, and builtin assertions.
    """

    def __init__(self, probe: Probe, name: Optional[str] = None):
        """Initialize a RuleSet instance.

        Args:
            probe: The Probe representing the ruleset configuration file.
            name: The name of the ruleset.
        """
        self.probe = probe
        self.name = name or self.probe.name

    @property
    # TODO: Add a type hint like I had before Dict[str, Builtin]
    def builtins(self) -> Dict:
        """Obtain all the builtin assertions from the RuleSet.

        Returns a mapping of builtin name to builtin assertion for the Ruleset.
        """
        content = _read_file(self.probe.path)
        if content is None:
            return {}

        builtin_objs = {}
        for builtin in SupportedBuiltins:
            if builtin.name not in content.keys():
                continue
                # TODO: We do not warn if they specify a builtin we do not support
                # Since Probes are also builtins we could take each top-level key and create a builtin out of it?
            builtin_objs[builtin.name] = Builtin(self.probe.name, content[builtin.name], builtin.value)

        return builtin_objs

    def aggregate_probes(self, probe_tree: ProbeTree = ProbeTree()) -> ProbeTree:
        """Obtain all the probes from the RuleSet.

        This method is recursive when it finds another RuleSet. It returns a list of probes that
        were found after traversing all the probes in the ruleset.

        While traversing, a record of probes are stored in a tree. Leaf nodes will be created from
        the root of the tree for each probe result.
        """
        content = _read_file(self.probe.path)
        if not content:
            return probe_tree

        # Create a root node if it does not exist
        if not probe_tree.tree:
            probe_tree.tree.create_node(ROOT_NODE_TAG, ROOT_NODE_ID)

        ruleset_name = content.get("name", None)
        # Only add the source ruleset probe to the tree's root node
        if self.probe.is_root_node:
            probe_tree.tree.create_node(
                ruleset_name, str(self.probe.uuid), probe_tree.tree.root, self.probe
            )
        else:
            probe_tree.tree.create_node(
                ruleset_name, str(self.probe.uuid), str(self.probe.get_parent()), self.probe
            )

        ruleset_probes = content.get("probes", [])
        for ruleset_probe in ruleset_probes:
            match ruleset_probe["type"]:
                # If the probe URL is not a directory and the path's suffix does not match the
                # expected type, warn and return no probes
                case "scriptlet":
                    if (
                        Path(ruleset_probe["url"]).suffix.lower()
                        and Path(ruleset_probe["url"]).suffix.lower()
                        not in FileExtensions.PYTHON.value
                    ):
                        log.warning(
                            f"{ruleset_probe['url']} is not a scriptlet but was specified as such."
                        )
                        return probe_tree
                    probe_tree = Probe.from_url(
                        ruleset_probe["url"],
                        self.probe.probes_root,
                        self.probe.get_chain(),
                        probe_tree,
                    )
                case "ruleset":
                    if (
                        Path(ruleset_probe["url"]).suffix.lower()
                        and Path(ruleset_probe["url"]).suffix.lower()
                        not in FileExtensions.RULESET.value
                    ):
                        log.warning(
                            f"{ruleset_probe['url']} is not a ruleset but was specified as such."
                        )
                        return probe_tree
                    if ruleset_probe.get("url", None):
                        probe_tree = Probe.from_url(
                            ruleset_probe["url"],
                            self.probe.probes_root,
                            self.probe.get_chain(),
                            probe_tree,
                        )
                        # If the probe is a directory of probes, capture it and continue to the
                        # next probe since it's not actually a Ruleset
                        if len(probe_tree.probes) > 1:
                            continue
                        # Recurses until we no longer have Ruleset probes
                        for nested_ruleset_probe in probe_tree.probes:
                            ruleset = RuleSet(nested_ruleset_probe)
                            derived_ruleset_probe_tree = ruleset.aggregate_probes(probe_tree)
                            log.info(f"Fetched probes: {derived_ruleset_probe_tree.probes}")
                            probe_tree.probes.extend(derived_ruleset_probe_tree.probes)
                    else:
                        log.info(
                            f"Found built-in probe config: \n{ruleset_probe.get('with', None)}"
                        )
                        raise NotImplementedError

                case _:
                    raise NotImplementedError

        return probe_tree
