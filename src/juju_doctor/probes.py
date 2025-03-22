"""Helper module to wrap and execute probes."""

import importlib.util
import inspect
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import fsspec
from rich.console import Console
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.fetcher import copy_probes, parse_terraform_notation

SUPPORTED_PROBE_TYPES = ["status", "bundle", "show_unit"]

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

console = Console()


def probe_name_as_posix(destination: Path, rel_path: Path) -> str:
    """Return the relative path of the Probe to use as its name."""
    return rel_path.relative_to(destination).as_posix()


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


@dataclass
class Probe:
    """A probe that can be executed via juju-doctor."""

    name: str
    uri: str
    original_path: Path  # path in the source folder
    path: Path  # path in the temporary folder

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
        for probe_path in copy_probes(
            filesystem=filesystem, path=path, probes_destination=probes_root / uri_flattened
        ):
            probe = Probe(
                name=probe_path.relative_to(probes_root).as_posix(),
                uri=uri,
                original_path=path,
                path=probe_path,
            )
            log.info(f"Fetched probe: {probe}")
            probes.append(probe)

        return probes

    @property
    def functions(self) -> Dict:
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
