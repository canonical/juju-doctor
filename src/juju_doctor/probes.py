"""Helper module to wrap and execute probes."""

import inspect
import logging
import sys
import types
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import ParseResult, urlparse
from uuid import UUID, uuid4

import fsspec
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from rich.logging import RichHandler
from treelib.tree import Tree

from juju_doctor.artifacts import Artifacts, read_file
from juju_doctor.constants import (
    ROOT_NODE_ID,
    ROOT_NODE_TAG,
    SUPPORTED_PROBE_FUNCTIONS,
)
from juju_doctor.fetcher import FileExtensions, copy_probes, parse_terraform_notation
from juju_doctor.results import AssertionResult, AssertionStatus, CheckFormat, FormatTracker

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


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

    def summarize_results(self):
        """Iterate over all probes and summarize their function name results."""
        for probe in self.probes:
            self._summarize_probe_results(probe)

    @staticmethod
    def _summarize_probe_results(probe: "Probe"):
        """Summarize the results for each executed function name (if multiple exist) of a Probe.

        For example, this:
        🟢 Foo (✔️ bundle, ✔️ status, ✖️ bundle, ✔️ status, ✔️ bundle, ✔️ status)
        becomes this:
        🟢 Foo (✖️ bundle (2/3), ✔️ status (3/3))
        """
        if len([r.func_name for r in probe.results]) == len({r.func_name for r in probe.results}):
            return  # if there are no duplicates

        # Generate the score (passed/total) among duplicates
        summary = {}
        for probe_result in probe.results:
            func_name = probe_result.func_name
            summary.setdefault(func_name, {"score": [0, 0], "exceptions": []})
            summary[func_name]["score"][0] += 1 if probe_result.passed else 0
            summary[func_name]["score"][1] += 1
            summary[func_name]["exceptions"].extend(probe_result.exceptions)

        probe.results = []
        for func_name, func_summary in summary.items():
            passed = func_summary["score"][0]
            total = func_summary["score"][1]
            new_name = f"{func_name} ({passed}/{total})"
            probe.results.append(
                AssertionResult(new_name, passed == total, summary[func_name]["exceptions"])
            )


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
    probes_root: Optional[Path] = None
    probes_chain: str = ""
    probe_definition: Optional["ProbeDefinition"] = None
    results: List[AssertionResult] = field(default_factory=list)
    uuid: UUID = field(default_factory=uuid4)

    @property
    def name(self) -> str:
        """Return the sanitized name of the probe by replacing `/` with `_`.

        This converts the probe's path relative to the root directory into a string format
        suitable for use in filenames or identifiers.
        """
        default = (
            self.path.relative_to(self.probes_root).as_posix()
            if self.probes_root
            else str(self.path)
        )
        if not self.probe_definition:
            return default
        if not self.probe_definition.name:
            return default
        return self.probe_definition.name

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
        url: str,
        probes_root: Path,
        probes_chain: str = "",
        probe_definition: Optional["ProbeDefinition"] = None,
        probe_tree: Optional[ProbeTree] = None,
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
            probe_definition: context provided as input to the probe, e.g. url, name, etc.
            probe_tree: a ProbeTree representing the discovered probes in a treelib.Tree format.
        """
        if probe_tree is None:
            probe_tree = ProbeTree()
        if not probe_tree.tree.nodes:
            probe_tree.tree.create_node(ROOT_NODE_TAG, ROOT_NODE_ID)

        parsed_url = urlparse(url)
        url_without_scheme = parsed_url.netloc + parsed_url.path
        url_flattened = url_without_scheme.replace("/", "_")
        fs = Probe._get_fs_from_protocol(parsed_url, url_without_scheme)

        probe_paths = copy_probes(fs.fs, fs.path, probes_destination=probes_root / url_flattened)
        for probe_path in probe_paths:
            if probe_definition and probe_definition.is_dir():
                probe_definition.name = None
            probe = Probe(probe_path, probes_root, probes_chain, probe_definition)

            is_ruleset = probe.path.suffix.lower() in FileExtensions.RULESET.value
            if is_ruleset:
                ruleset = RuleSet(probe)
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

        We import the module dynamically because the path of the probe is only known at runtime.
        Only returns the supported 'status', 'bundle', and 'show_unit' functions (if present).
        """
        # module from filesystem path
        if self.probes_root:
            package_name = ""
            source_path = Path(self.path).resolve()
            src_text = source_path.read_text()
            origin = str(source_path)
        # module from package resources (wheel or source)
        else:
            package_name = "juju_doctor"
            resource = resources.files(package_name).joinpath(str(self.path))
            src_text = resource.read_text()
            origin = f"{package_name}/{self.path}"

        # create the module, set context, register and execute
        module_name = "probe"
        module = types.ModuleType(module_name)
        module.__file__ = origin
        # ff the probe is inside the package, set a package context so relative imports work
        module.__package__ = package_name or None
        sys.modules[module_name] = module

        exec(compile(src_text, origin, "exec"), module.__dict__)

        # Return the functions defined in the probe module
        return {
            name: func
            for name, func in inspect.getmembers(module, inspect.isfunction)
            if name in SUPPORTED_PROBE_FUNCTIONS
        }

    def run(self, artifacts: Artifacts, **kwargs):
        """Execute each Probe function that matches the supported probe types.

        The results of each function are aggregated and assigned to the probe itself
        """
        for func_name, func in self.get_functions().items():
            # Get the artifact needed by the probe, and fail if it's missing
            artifact = getattr(artifacts, func_name)
            if not artifact:
                log.warning(f"No {func_name} artifact was provided for probe: {self.path}.")
                continue
            # Run the probe function, and record its result
            try:
                func(artifact, **kwargs)
            except BaseException as e:
                self.results.append(AssertionResult(func_name, passed=False, exceptions=[e]))
            else:
                self.results.append(AssertionResult(func_name, passed=True))

    def succeeded(self) -> bool:
        """Return the probe's status.

        For a probe to succeed, it must have been executed, i.e. have results, and have no failing
        function results.
        """
        if not self.results:
            return False
        if all(result.passed for result in self.results):
            return True
        return False

    def result_text(self, output_fmt: FormatTracker) -> NodeResultInfo:
        """Probe results (formatted with Pretty-print) as text."""
        func_statuses = []
        exception_msgs = []
        red = output_fmt.rich_map["red"]
        green = output_fmt.rich_map["green"]
        for result in self.results:
            if not result.passed:
                for exception in result.exceptions:
                    exception_suffix = f"({self.name}/{result.func_name}): {exception}"
                    if output_fmt and output_fmt.format.lower() == CheckFormat.json.value:
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

        if self.succeeded():
            node_tag = f"{green} {self.name}"
        else:
            node_tag = f"{red} {self.name}"
        if output_fmt.verbose:
            if func_statuses:
                node_tag += f" ({', '.join(func_statuses)})"

        return NodeResultInfo(node_tag, exception_msgs)


class ProbeDefinition(BaseModel):
    """Schema for a builtin Probe definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None)
    type: str
    url: Optional[str] = Field(None)
    with_: Optional[Any] = Field(None, alias="with")

    def is_dir(self) -> bool:
        """Is the url a directory-like path, i.e. it does not need to exist on disk."""
        if not self.url:
            return False
        assertion_path = Path(str(urlparse(self.url).path))
        return (
            assertion_path.name.endswith("/") or not assertion_path.suffix
        ) and self.get_type() != "builtin"

    def get_type(self):
        """Convert the user input into a base type."""
        return self.type.split("/")[0]


class RuleSetModel(BaseModel):
    """A pydantic model of a declarative YAML RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str
    probes: List[ProbeDefinition] = Field(...)


class RuleSet:
    """Represents a set of probes defined in a declarative configuration file.

    Supports recursive aggregation of probes, nested rulesets, and builtin assertions.
    """

    def __init__(self, probe: Probe):
        """Initialize a RuleSet instance.

        Args:
            probe: The Probe representing the ruleset configuration file.
        """
        self.probe = probe
        if not (contents := read_file(str(self.probe.path))):
            self.content = None
        else:
            try:
                self.content = RuleSetModel(**contents)
            except ValidationError as e:
                self.content = None
                log.error(e)

    def aggregate_probes(self, probe_tree: Optional[ProbeTree] = None) -> ProbeTree:
        """Obtain all the probes from the RuleSet.

        This method is recursive when it finds another RuleSet. It returns a list of probes that
        were found after traversing all the probes in the ruleset.

        While traversing, a record of probes are stored in a tree. Leaf nodes will be created from
        the root of the tree for each probe result.
        """
        if probe_tree is None:
            probe_tree = ProbeTree()
        if not self.content:
            return probe_tree

        # Create a root node if it does not exist
        if not probe_tree.tree.nodes:
            probe_tree.tree.create_node(ROOT_NODE_TAG, ROOT_NODE_ID)

        # Only add the source ruleset probe to the tree's root node
        if self.probe.is_root_node:
            probe_tree.tree.create_node(
                self.content.name, str(self.probe.uuid), probe_tree.tree.root, self.probe
            )
        else:
            probe_tree.tree.create_node(
                self.content.name, str(self.probe.uuid), str(self.probe.get_parent()), self.probe
            )

        for ruleset_probe in self.content.probes:
            match ruleset_probe.get_type():
                # If the probe URL is not a directory and the path's suffix does not match the
                # expected type, warn and return no probes
                case "scriptlet":
                    if ruleset_probe.url is None:
                        raise Exception('"url" must be defined for scriptlet probes')
                    if (
                        Path(ruleset_probe.url).suffix.lower()
                        and Path(ruleset_probe.url).suffix.lower()
                        not in FileExtensions.PYTHON.value
                    ):
                        log.warning(
                            f"{ruleset_probe.url} is not a scriptlet but was specified as such."
                        )
                        return probe_tree
                    if not self.probe.probes_root:
                        log.error(f"{self.probe.name} does not have a probes_root.")
                        return probe_tree
                    probe_tree = Probe.from_url(
                        ruleset_probe.url,
                        self.probe.probes_root,
                        self.probe.get_chain(),
                        ruleset_probe,
                        probe_tree,
                    )
                case "ruleset":
                    if ruleset_probe.url is None:
                        raise Exception('"url" must be defined for scriptlet probes')
                    if (
                        Path(ruleset_probe.url).suffix.lower()
                        and Path(ruleset_probe.url).suffix.lower()
                        not in FileExtensions.RULESET.value
                    ):
                        log.warning(
                            f"{ruleset_probe.url} is not a ruleset but was specified as such."
                        )
                        return probe_tree
                    if ruleset_probe.url:
                        if not self.probe.probes_root:
                            log.error(f"{self.probe.name} does not have a probes_root.")
                            return probe_tree
                        probe_tree = Probe.from_url(
                            ruleset_probe.url,
                            self.probe.probes_root,
                            self.probe.get_chain(),
                            ruleset_probe,
                            probe_tree,
                        )
                        # If there are multiple probes, capture them and continue to the next probe
                        # since it's not actually a Ruleset
                        if len(probe_tree.probes) > 1:
                            continue
                        # Recurses until we no longer have Ruleset probes
                        for nested_ruleset_probe in probe_tree.probes:
                            ruleset = RuleSet(nested_ruleset_probe)
                            derived_ruleset_probe_tree = ruleset.aggregate_probes(probe_tree)
                            log.info(f"Fetched probes: {derived_ruleset_probe_tree.probes}")
                            probe_tree.probes.extend(derived_ruleset_probe_tree.probes)
                    else:
                        raise NotImplementedError
                case "builtin":
                    type_parts = ruleset_probe.type.split("/")
                    if not (builtin_type := type_parts[1] if len(type_parts) == 2 else None):
                        raise NotImplementedError
                    probe_tree.probes.append(
                        Probe(
                            Path(f"builtin/{builtin_type}.py"),
                            probes_chain=self.probe.get_chain(),
                            probe_definition=ruleset_probe,
                        )
                    )
                case _:
                    raise NotImplementedError

        return probe_tree
