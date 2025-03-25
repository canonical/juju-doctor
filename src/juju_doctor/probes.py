"""Helper module to wrap and execute probes."""

import importlib.util
import inspect
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import fsspec
import yaml
from rich.console import Console
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.fetcher import FileExtensions, copy_probes, parse_terraform_notation

# TODO This is never used
SUPPORTED_PROBE_TYPES = ["status", "bundle", "show_unit"]

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

console = Console()

sys.setrecursionlimit(150)  # Protect against cirular RuleSet executions, increase if needed


@dataclass
class ProbeResults:
    """A helper class to wrap results for a Probe."""

    probe_name: str
    passed: bool
    exception: Optional[BaseException] = None

    def print(self, verbose: bool):
        """Pretty-print the Probe results."""
        if self.passed:
            console.print(f":green_circle: {self.probe_name} passed")
            return
        # or else, if the probe failed
        if verbose:
            console.print(f":red_circle: {self.probe_name} failed")
            console.print(f"[b]Exception[/b]: {self.exception}")
        else:
            console.print(f":red_circle: {self.probe_name} failed ", end="")
            console.print(
                f"({self.exception}",
                overflow="ellipsis",
                no_wrap=True,
                width=40,
                end="",
            )
            console.print(")")

@dataclass
class Probe:
    """A probe that can be executed via juju-doctor.

    For example, you can instantiate with:
        Probe(
            uri='file://resources/passing.py'
            probes_root=PosixPath('/probes')
            original_path=PosixPath('resources/passing.py')
            path=PosixPath('/probes/resources_passing.py')
        )
    """

    uri: str
    probes_root: Path
    original_path: Path  # path in the source folder
    path: Path  # path in the temporary folder

    @property
    def name(self) -> str:
        """The name of the probe sanitized by replacing `/` with `_`."""
        return self.original_path.as_posix()

    @staticmethod
    def from_uri(uri: str, probes_root: Path) -> List["Probe"]:
        """Build a set of Probes from a URI.

        This function parses the URI to construct a generic 'filesystem' object,
        that allows us to interact with files regardless of whether they are on
        local disk or on GitHub.

        Then, it copies the parsed probes to a subfolder inside 'probes_root', and
        return a list of Probe items for each probe that was copied.

        Args:
            uri: a string representing the Probe's URI.
            probes_root: the root folder for the probes on the local FS.
        """
        # Get the fsspec.AbstractFileSystem for the Probe's protocol
        parsed_uri = urlparse(uri)
        uri_without_scheme = parsed_uri.netloc + parsed_uri.path
        uri_flattened = uri_without_scheme.replace("/", "_")
        match parsed_uri.scheme:
            case "file":
                path = Path(uri_without_scheme)
                filesystem = fsspec.filesystem(protocol="file")
            case "github":
                branch = parsed_uri.query or "main"
                org, repo, path = parse_terraform_notation(uri_without_scheme)
                path = Path(path)
                filesystem = fsspec.filesystem(
                    protocol="github", org=org, repo=repo, sha=f"refs/heads/{branch}"
                )
            case _:
                raise NotImplementedError

        probes = []
        probe_paths = copy_probes(filesystem, path, probes_destination=probes_root / uri_flattened)
        for probe_path in probe_paths:
            probe = Probe(
                uri=uri,
                probes_root=probes_root,
                original_path=path,
                path=probe_path,
            )
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
            if name in ["status", "bundle", "show_unit"]
        }

    def run(self, artifacts: Artifacts) -> List[ProbeResults]:
        """Execute each Probe function that matches the names: `status`, `bundle`, or `show_unit`."""
        # Silence the result printing if needed
        results: List[ProbeResults] = []
        for func_name, func in self.get_functions().items():
            # Get the artifact needed by the probe, and fail if it's missing
            artifact = getattr(artifacts, func_name)
            if not artifact:
                results.append(
                    ProbeResults(
                        probe_name=f"{self.name}/{func_name}",
                        passed=False,
                        exception=Exception(f"No '{func_name}' artifacts have been provided."),
                    )
                )
                continue
            # Run the probe fucntion, and record its result
            try:
                func(artifact)
            except BaseException as e:
                results.append(ProbeResults(probe_name=f"{self.name}/{func_name}", passed=False, exception=e))
            else:
                results.append(ProbeResults(probe_name=f"{self.name}/{func_name}", passed=True))
        return results


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


class RuleSet:
    """Represents a set of probes defined in a ruleset configuration file.

    Supports recursive aggregation of probes, handling scriptlets and nested rulesets.
    Detects and prevents circular dependencies.
    """

    def __init__(self, probe: Probe, name: str = None):
        """Initialize a RuleSet instance.

        Args:
            probe (Probe): The Probe representing the ruleset configuration file.
            name (str): The name of the ruleset.
        """
        self.probe = probe
        self.name = name or self.probe.name

    def aggregate_probes(self) -> List[Probe]:
        """Obtain all the probes from the RuleSet.

        This method is recursive when it finds another RuleSet probe.

        Raises CircularRulesetError if a Ruleset execution chain contained more than 2 Rulesets.
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
                    probes.extend(Probe.from_uri(ruleset_probe["uri"], self.probe.probes_root))
                case "ruleset":
                    if ruleset_probe.get("uri", None):
                        nested_ruleset_probes = Probe.from_uri(ruleset_probe["uri"], self.probe.probes_root)
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
                        log.warning(f'Found built-in probe config: \n{ruleset_probe.get("with", None)}')
                        # TODO Change verbosity on raising for CLI tool, consider using:
                        # https://pypi.org/project/pretty-traceback/
                        # raise NotImplementedError

                case _:
                    raise NotImplementedError

        return probes
