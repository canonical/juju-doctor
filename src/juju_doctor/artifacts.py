"""Helper module to represent the input artifacts for Juju doctor."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import sh
import yaml
from jubilant import ModelInfo, Status, UnitInfo
from rich.logging import RichHandler

# pyright: reportAttributeAccessIssue=false

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


def read_file(filename: Optional[str]) -> Optional[Dict]:
    """Read a file into a string."""
    if not filename:
        return None
    try:
        with open(filename, "r") as f:
            contents = f.read()
            # Parse all YAML documents and return only the first one
            # https://github.com/canonical/juju-doctor/issues/10
            return list(yaml.safe_load_all(contents))[0]
    except Exception as e:
        log.error(e)
    return None


def _from_status(status_data: Optional[Dict[str, Any]]) -> Optional[Status]:
    """Parse a ``juju status`` artifact into a :class:`jubilant.Status`."""
    if not status_data:
        return None
    try:
        return Status._from_dict(status_data)
    except Exception as e:
        log.error(e)
        return None


def _parse_show_units(show_units: Optional[Dict[str, Any]]) -> Dict[str, UnitInfo]:
    """Parse a ``juju show-unit`` artifact into :class:`jubilant.UnitInfo` objects."""
    units: Dict[str, UnitInfo] = {}
    for unit_name, unit_data in (show_units or {}).items():
        try:
            units[unit_name] = UnitInfo._from_dict(unit_data)
        except Exception as e:
            log.error(e)
    return units


def _from_show_model(model_data: Optional[Dict[str, Any]]) -> Optional[ModelInfo]:
    """Parse a ``juju show-model`` artifact into a :class:`jubilant.ModelInfo`.

    The Juju CLI wraps the model information in a single-key mapping
    (``{<model-name>: {...}}``); unwrap it when present.
    """
    if not model_data:
        return None
    try:
        if len(model_data) == 1:
            only_value = next(iter(model_data.values()))
            if isinstance(only_value, dict) and "model-uuid" in only_value:
                model_data = only_value
        return ModelInfo._from_dict(model_data)
    except Exception as e:
        log.error(e)
        return None


@dataclass
class ModelArtifact:
    """Wrapper around multiple Juju artifacts for the same model."""

    status: Optional[Status]
    bundle: Optional[Dict]
    show_units: Optional[Dict[str, UnitInfo]]
    show_model: Optional[ModelInfo] = None
    model_dump: Optional[Dict] = None

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
            show_unit = yaml.safe_load(
                sh.juju("show-unit", unit, model=model, format="yaml", _tty_out=False)
            )
            show_units.update(show_unit)

        # Model information, e.g. the model UUID, users, and secret backends
        show_model = yaml.safe_load(
            sh.juju("show-model", model=model, format="yaml", _tty_out=False)
        )

        # Full model dump, which contains the charm metadata and relation graph
        try:
            model_dump = yaml.safe_load(
                sh.juju("dump-model", model=model, format="yaml", _tty_out=False)
            )
        except Exception as e:  # dump-model is deprecated on newer Juju versions
            log.warning(f"Unable to gather the model dump for {model}: {e}")
            model_dump = None

        return ModelArtifact(
            status=_from_status(juju_status),
            bundle=bundle,
            show_units=_parse_show_units(show_units),
            show_model=_from_show_model(show_model),
            model_dump=model_dump or None,
        )

    @staticmethod
    def from_files(
        *,
        status_file: Optional[str] = None,
        bundle_file: Optional[str] = None,
        show_unit_file: Optional[str] = None,
        show_model_file: Optional[str] = None,
        model_dump_file: Optional[str] = None,
    ) -> "ModelArtifact":
        """Gather information from static files."""
        return ModelArtifact(
            status=_from_status(read_file(status_file)),
            bundle=read_file(bundle_file) or None,
            show_units=_parse_show_units(read_file(show_unit_file)) or None,
            show_model=_from_show_model(read_file(show_model_file)),
            model_dump=read_file(model_dump_file) or None,
        )


@dataclass
class Artifacts:
    """Wrapper around all input artifacts."""

    artifacts: Dict[str, ModelArtifact]

    @property
    def status(self) -> Dict[str, Status]:
        """Get the Juju status for all the models."""
        result: Dict[str, Status] = {}
        for model, model_artifact in self.artifacts.items():
            if model_artifact.status:
                result[model] = model_artifact.status
        return result

    @property
    def bundle(self) -> Dict[str, Dict]:
        """Get the Juju bundle for all the models."""
        result: Dict[str, Dict] = {}
        for model, model_artifact in self.artifacts.items():
            if model_artifact.bundle:
                result[model] = model_artifact.bundle
        return result

    @property
    def show_unit(self) -> Dict[str, Dict[str, UnitInfo]]:
        """Get the Juju show-units for all the models."""
        result: Dict[str, Dict[str, UnitInfo]] = {}
        for model, model_artifact in self.artifacts.items():
            if model_artifact.show_units:
                result[model] = model_artifact.show_units
        return result

    @property
    def show_model(self) -> Dict[str, ModelInfo]:
        """Get the Juju show-model information for all the models."""
        result: Dict[str, ModelInfo] = {}
        for model, model_artifact in self.artifacts.items():
            if model_artifact.show_model:
                result[model] = model_artifact.show_model
        return result

    @property
    def model_dump(self) -> Dict[str, Dict]:
        """Get the Juju dump-model information for all the models."""
        result: Dict[str, Dict] = {}
        for model, model_artifact in self.artifacts.items():
            if model_artifact.model_dump:
                result[model] = model_artifact.model_dump
        return result
