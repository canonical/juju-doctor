"""Helper module to represent the input artifacts for Juju doctor."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import sh
import yaml

# pyright: reportAttributeAccessIssue=false


def _read_file(filename: Optional[str]) -> Optional[Dict]:
    """Read a file into a string."""
    if not filename:
        return None
    with open(filename, "r") as f:
        contents = f.read()
        # Parse all YAML documents and return only the first one
        # https://github.com/canonical/juju-doctor/issues/10
        return list(yaml.safe_load_all(contents))[0]


@dataclass
class ModelArtifact:
    """Wrapper around multiple Juju artifacts for the same model."""

    status: Optional[Dict]
    bundle: Optional[Dict]
    show_units: Optional[Dict[str, Dict]]

    @staticmethod
    def from_live_model(model: str) -> "ModelArtifact":
        """Gather information from a live model."""
        juju_status = yaml.safe_load(sh.juju.status(model=model, format="yaml", _tty_out=False))
        bundle = yaml.safe_load(sh.juju("export-bundle", model=model, _tty_out=False))
        # Get unit data information
        units: List[str] = []
        show_units: Dict[str, Any] = {}  # List of show-unit results in dictionary form
        for app in juju_status["applications"]:
            # Subordinate charms don't have a "units" key, so the parsing is different
            app_status = juju_status["applications"][app]
            if "units" in app_status:  # if the app is not a subordinate
                units.extend(app_status["units"].keys())
                # Check for subordinates to each unit
                for unit in app_status["units"].keys():
                    unit_status = app_status["units"][unit]
                    if "subordinates" in unit_status:
                        units.extend(unit_status["subordinates"].keys())
        for unit in units:
            show_unit = yaml.safe_load(sh.juju("show-unit", unit, model=model, format="yaml", _tty_out=False))
            show_units.update(show_unit)

        return ModelArtifact(status=juju_status, bundle=bundle, show_units=show_units)

    @staticmethod
    def from_files(
        *,
        status_file: Optional[str] = None,
        bundle_file: Optional[str] = None,
        show_unit_file: Optional[str] = None,
    ) -> "ModelArtifact":
        """Gather information from static files."""
        return ModelArtifact(
            status=_read_file(status_file) or None,
            bundle=_read_file(bundle_file) or None,
            show_units=_read_file(show_unit_file) or None,
        )


@dataclass
class Artifacts:
    """Wrapper around all input artifacts."""

    artifacts: Dict[str, ModelArtifact]

    @property
    def status(self) -> Optional[Dict[str, Dict]]:
        """Get the Juju status for all the models."""
        result = {}
        for model, model_artifact in self.artifacts.items():
            result[model] = model_artifact.status
        return result

    @property
    def bundle(self) -> Optional[Dict[str, Dict]]:
        """Get the Juju bundle for all the models."""
        result = {}
        for model, model_artifact in self.artifacts.items():
            result[model] = model_artifact.bundle
        return result

    @property
    def show_unit(self) -> Optional[Dict[str, Dict]]:
        """Get the Juju show-units for all the models."""
        result = {}
        for model, model_artifact in self.artifacts.items():
            result[model] = model_artifact.show_units
        return result
