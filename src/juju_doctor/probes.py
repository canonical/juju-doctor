"""Helper module to wrap and execute probes."""

import importlib.util
import inspect
import logging
from dataclasses import dataclass
from pathlib import Path

from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts

SUPPORTED_PROBE_TYPES = ["status", "bundle", "show_unit"]

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


@dataclass
class Probe:
    """A probe that can be executed via juju-doctor."""

    name: str
    uri: str
    original_path: Path  # path in the source folder
    path: Path  # path in the temporary folder

    def run(self, artifacts: Artifacts):
        """Dynamically load a Python script from self.path, making its functions available.

        Execute each Probe function that matches the names: `status`, `bundle`, or `show_unit`.

        We need to import the module dynamically with the 'spec' mechanism because the path
        of the probe is only known at runtime.
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
        # Get the functions defined in the probe module
        functions = inspect.getmembers(module, inspect.isfunction)
        for name, func in functions:
            match name:
                case "status":
                    if not artifacts.statuses():
                        raise Exception("No 'juju status' artifacts have been provided.")
                    func(artifacts.statuses())
                case "bundle":
                    if not artifacts.bundles():
                        raise Exception("No 'juju bundle' artifacts have been provided.")
                    func(artifacts.bundles())
                case "show_unit":
                    if not artifacts.bundles():
                        raise Exception("No 'juju show-unit' artifacts have been provided.")
                    func(artifacts.show_units())
                case _:
                    continue
