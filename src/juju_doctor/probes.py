"""Helper module to wrap and execute probes."""

import importlib.util
import inspect
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import URLError
from urllib.parse import urlparse

import fsspec
from rich.console import Console
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts

SUPPORTED_PROBE_TYPES = ["status", "bundle", "show_unit"]

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

console = Console()


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
    """A probe that can be executed via juju-doctor."""

    name: str
    uri: str
    original_path: Path  # path in the source folder
    path: Path  # path in the temporary folder

    @staticmethod
    def from_uri(self, uri: str, temp_dir: Path) -> List["Probe"]:
        """build probe from URI.

        Here we would do the protocol matching
        Return Probe or list of Probes

        Manage the relevant paths that a Probe or a Probe runner would require.
        Parse the URI to determine relative and local paths, ensuring proper formatting.
        # TODO update docstring
        Args:
            uri: a string representing the Probe's URI.
            temp_dir: the file path for the probes on the local FS.
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
                try:
                    branch = parsed_uri.query or "main"
                    # Extract the org and repository from the relative path
                    org_and_repo, path_str = uri_without_scheme.split("//")
                    org, repo = org_and_repo.split("/")
                    path = Path(path_str)  # Sanitize the TF dir notation `//` in the path
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

        try:
            # If path ends with a "/", it will be assumed to be a directory
            # Can submit a list of paths, which may be glob-patterns and will be expanded.
            # https://github.com/fsspec/filesystem_spec/blob/master/docs/source/copying.rst
            probe_destination = temp_dir / uri_flattened
            filesystem.get(
                path.as_posix(), probe_destination.as_posix(), recursive=True, auto_mkdir=True
            )
        except FileNotFoundError as e:
            log.warning(
                f"{e} file not found when attempting to copy "
                f"'{path.as_posix()}' to '{probe_destination.as_posix()}'"
            )
        if filesystem.isfile(path.as_posix()):
            probe_files = [probe_destination]
        else:
            probe_files: List[Path] = [
                f for f in probe_destination.rglob("*") if f.as_posix().endswith(".py")
            ]
            log.info(f"copying {path.as_posix()} to {probe_destination.as_posix()} recursively")
        probes = []
        for probe_path in probe_files:
            probe = Probe(
                name=probe_path.relative_to(temp_dir).as_posix(),
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
        for func_name, func in self.functions.items():
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
