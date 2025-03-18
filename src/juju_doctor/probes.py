"""Helper module to wrap and execute probes."""

import importlib.util
import inspect
from dataclasses import dataclass
from pathlib import Path

from src.juju_doctor.artifacts import Artifacts

SUPPORTED_PROBE_TYPES = ["status", "bundle", "show_unit"]


@dataclass
class Probe:
    """A probe that can be executed via juju-doctor."""

    name: str
    uri: str
    original_path: Path  # path in the source folder
    path: Path  # path in the temporary folder

    def run(self, artifacts: Artifacts):
        """Run the probe."""
        module_name = "probe"
        spec = importlib.util.spec_from_file_location(module_name, self.path.resolve())
        if not spec:
            raise ValueError(f"Probe not found at its 'path': {self}")
        module = importlib.util.module_from_spec(spec)
        # spec.loader.exec_module(module)
        functions = inspect.getmembers(module, inspect.isfunction)
        for name, func in functions:
            match name:
                case "status":
                    func(artifacts.statuses())
                case "bundle":
                    func(artifacts.bundles())
                case "show_unit":
                    func(artifacts.show_units())
                case _:
                    continue
