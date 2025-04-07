"""Helper module to wrap and execute probes."""

import importlib.util
import inspect
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from uuid import UUID, uuid4

import fsspec
import yaml
from rich.console import Console
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.fetcher import FileExtensions, copy_probes, parse_terraform_notation

SUPPORTED_PROBE_FUNCTIONS = ["status", "bundle", "show_unit"]

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

console = Console()


class AssertionStatus(Enum):
    """Result of the probe's assertion."""

    PASS = "pass"
    FAIL = "fail"


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
class Probe:
    """A probe that can be executed via juju-doctor.

    Since a Python probe can be executed multiple times, we need a way to differentiate between
    the call paths. Each probe is instantiated with a UUID which is appended to the `probes_chain`
    to identify the top-level probe (and subsequent probes) that lead to this probe's execution.

    For example, for 2 probes: A and B inside a directory which is executed by probe C, their
    probe chains would be
        /UUID(C)/UUID(A)
        /UUID(C)/UUID(B)

    Alternatively, for 2 probes: D and E which both call probe F, their probe chains would be
        /UUID(D)/UUID(F)
        /UUID(E)/UUID(F)

    The probe chain ends when the probe does not call another probe.
    """

    path: Path  # relative path in the temporary folder
    probes_root: Path  # temporary folder for all probes
    probes_chain: str = ""  # probe call chain with format /UUID/UUID/UUID
    uuid: UUID = field(default_factory=uuid4)

    @property
    def name(self) -> str:
        """Return the sanitized name of the probe by replacing `/` with `_`.

        This converts the probe's path relative to the root directory into a string format
        suitable for use in filenames or identifiers.
        """
        return self.path.relative_to(self.probes_root).as_posix()

    def get_chain(self) -> str:
        """Append the current probe's UUID to the chain."""
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
            if probe.path.suffix.lower() in FileExtensions.RULESET.value:
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
            if name in SUPPORTED_PROBE_FUNCTIONS
        }

    def run(self, artifacts: Artifacts) -> List["ProbeAssertionResult"]:
        """Execute each Probe function that matches the supported probe types."""
        # Silence the result printing if needed
        results: List[ProbeAssertionResult] = []
        for func_name, func in self.get_functions().items():
            # Get the artifact needed by the probe, and fail if it's missing
            artifact = getattr(artifacts, func_name)
            if not artifact:
                results.append(
                    ProbeAssertionResult(
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
                results.append(
                    ProbeAssertionResult(
                        probe=self, func_name=func_name, passed=False, exception=e
                    )
                )
            else:
                results.append(ProbeAssertionResult(probe=self, func_name=func_name, passed=True))
        return results


@dataclass
class ProbeAssertionResult:
    """A helper class to wrap results for a Probe's functions."""

    probe: Probe
    func_name: str
    passed: bool
    exception: Optional[BaseException] = None

    @property
    def status(self) -> str:
        """Result of the probe."""
        return AssertionStatus.PASS.value if self.passed else AssertionStatus.FAIL.value

    def get_text(self, output_fmt) -> Tuple[str, Optional[str]]:
        """Probe results (formatted as Pretty-print) as a string."""
        exception_msg = None
        green = output_fmt.rich_map["green"]
        red = output_fmt.rich_map["red"]
        if self.passed:
            return f"{green} {self.probe.name}", exception_msg
        # If the probe failed
        exception_suffix = f"({self.probe.name}/{self.func_name}): {self.exception}"
        if output_fmt.format == "json":
            exception_msg = f"Exception {exception_suffix}"
        else:
            if output_fmt.verbose:
                exception_msg = f"[b]Exception[/b] {exception_suffix}"
        return f"{red} {self.probe.name}", exception_msg


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
                case "scriptlet":
                    probes.extend(
                        Probe.from_url(
                            ruleset_probe["url"], self.probe.probes_root, self.probe.get_chain()
                        )
                    )
                case "ruleset":
                    if ruleset_probe.get("url", None):
                        nested_ruleset_probes = Probe.from_url(
                            ruleset_probe["url"],
                            self.probe.probes_root,
                            self.probe.get_chain(),
                        )
                        # If the probe is a directory of probes, capture it and continue to the
                        # next probe since it's not actually a Ruleset
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
                        # TODO "built-in" directives, e.g. "apps/has-relation"
                        log.info(
                            f"Found built-in probe config: \n{ruleset_probe.get('with', None)}"
                        )
                        raise NotImplementedError

                case _:
                    raise NotImplementedError

        return probes
