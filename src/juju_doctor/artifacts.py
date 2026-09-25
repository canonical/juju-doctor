"""Helper module to represent the input artifacts for Juju doctor."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import yaml
from jubilant import Juju, ModelInfo, Status, UnitInfo
from rich.logging import RichHandler

# pyright: reportAttributeAccessIssue=false

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class ArtifactError(Exception):
    """Raised when an artifact cannot be read or parsed."""


def _load_yaml(filename: str) -> Any:
    """Load the first YAML document of a file."""
    with open(filename, "r") as f:
        documents = list(yaml.safe_load_all(f.read()))
    return documents[0] if documents else None


def read_file(filename: Optional[str]) -> Optional[Dict]:
    """Read a YAML file into a dict, leniently.

    This is the lenient reader used by probes and RuleSets: a missing file is
    logged and returned as ``None``. Use :func:`read_artifact_file` when the
    artifact was explicitly requested and must fail loudly if it is missing.
    """
    if not filename:
        return None
    try:
        return _load_yaml(filename)
    except Exception as e:
        log.error(e)
    return None


def read_artifact_file(filename: str) -> Dict:
    """Read an artifact file, raising :class:`ArtifactError` if it cannot be read.

    Artifacts that were explicitly requested (e.g. via ``--status``) must never
    silently turn into an empty artifact, so this reader fails loudly.
    """
    try:
        contents = _load_yaml(filename)
    except Exception as e:
        raise ArtifactError(f"Unable to read artifact file '{filename}': {e}") from e
    if contents is None:
        raise ArtifactError(f"Artifact file '{filename}' is empty")
    return contents


def _parse_status(status_data: Dict[str, Any]) -> Status:
    """Parse a ``juju status`` artifact into a :class:`jubilant.Status`."""
    try:
        return Status._from_dict(status_data)
    except Exception as e:
        raise ArtifactError(f"Invalid Juju status artifact: {e}") from e


def _parse_show_units(show_units: Dict[str, Any]) -> Dict[str, UnitInfo]:
    """Parse a ``juju show-unit`` artifact into :class:`jubilant.UnitInfo` objects.

    ``show-unit`` is a collection of independent units, so a single unit that
    does not match the Jubilant schema is skipped with a warning rather than
    failing the whole artifact. If none of the entries can be parsed, the
    artifact is considered invalid.
    """
    if not isinstance(show_units, Mapping):
        raise ArtifactError("Invalid show-unit artifact: expected a mapping of unit names")
    units: Dict[str, UnitInfo] = {}
    for unit_name, unit_data in show_units.items():
        try:
            units[unit_name] = UnitInfo._from_dict(unit_data)
        except Exception as e:
            log.warning(f"Skipping show-unit artifact for '{unit_name}': {e}")
    if show_units and not units:
        raise ArtifactError("None of the show-unit entries could be parsed")
    return units


def _parse_show_model(model_data: Dict[str, Any]) -> ModelInfo:
    """Parse a ``juju show-model`` artifact into a :class:`jubilant.ModelInfo`.

    The Juju CLI wraps the model information in a single-key mapping
    (``{<model-name>: {...}}``); unwrap it when present.
    """
    if not isinstance(model_data, Mapping):
        raise ArtifactError("Invalid show-model artifact: expected a mapping")
    if len(model_data) == 1:
        only_value = next(iter(model_data.values()))
        if isinstance(only_value, dict) and "model-uuid" in only_value:
            model_data = only_value
    try:
        return ModelInfo._from_dict(model_data)
    except Exception as e:
        raise ArtifactError(f"Invalid show-model artifact: {e}") from e


def _gather_live(model: str, artifact: str, command: Callable[[], Any]) -> Optional[Any]:
    """Run a Jubilant command, tolerating failures.

    Different Juju versions expose different commands (for example,
    ``export-bundle`` was removed in Juju 4), so gathering an optional artifact
    must not abort the whole run when a single command is unavailable.
    """
    try:
        return command()
    except Exception as e:
        log.warning(f"Unable to gather the {artifact} artifact for model '{model}': {e}")
        return None


def _unit_names(status: Status) -> List[str]:
    """Return the principal and subordinate unit names of a status artifact."""
    units: List[str] = []
    for app_status in status.apps.values():
        units.extend(app_status.units.keys())
        for unit_status in app_status.units.values():
            units.extend(unit_status.subordinates.keys())
    return units


@dataclass
class ModelArtifact:
    """Wrapper around multiple Juju artifacts for the same model.

    ``status``, ``show_units``, and ``show_model`` are parsed into the
    dataclasses that Jubilant provides for those commands. ``bundle`` and
    ``model_dump`` are intentionally left as opaque mappings: Jubilant does not
    model them (``export-bundle`` was removed in Juju 4 and ``dump-model`` is an
    internal database representation), so juju-doctor does not guess at their
    schema.
    """

    status: Optional[Status]
    bundle: Optional[Mapping[str, Any]]
    show_units: Optional[Dict[str, UnitInfo]]
    show_model: Optional[ModelInfo] = None
    model_dump: Optional[Mapping[str, Any]] = None

    @staticmethod
    def from_live_model(model: str) -> "ModelArtifact":
        """Gather information from a live model.

        This uses Jubilant's public methods, which run the Juju CLI and return
        parsed objects. The ``status`` artifact is required and raises if it
        cannot be gathered. The remaining artifacts are gathered on a
        best-effort basis so that a command that is missing or removed in a
        given Juju version does not fail the whole run.
        """
        juju = Juju(model=model)

        status = _gather_live(model, "status", juju.status)
        if status is None:
            raise ArtifactError(f"Unable to gather the status artifact for model '{model}'")

        bundle = _gather_live(
            model, "bundle", lambda: yaml.safe_load(juju.cli("export-bundle"))
        )
        show_model = _gather_live(model, "show-model", juju.show_model)
        model_dump = _gather_live(
            model, "dump-model", lambda: yaml.safe_load(juju.cli("dump-model"))
        )

        # Gather the show-unit information for every principal and subordinate unit
        show_units: Dict[str, UnitInfo] = {}
        for unit in _unit_names(status):
            unit_info = _gather_live(
                model, f"show-unit ({unit})", lambda unit=unit: juju.show_unit(unit)
            )
            if unit_info:
                show_units[unit] = unit_info

        return ModelArtifact(
            status=status,
            bundle=bundle,
            show_units=show_units or None,
            show_model=show_model,
            model_dump=model_dump,
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
        """Gather information from static files.

        Files that were explicitly provided are read strictly: a missing or
        malformed file raises :class:`ArtifactError` instead of being silently
        ignored.
        """
        status = read_artifact_file(status_file) if status_file else None
        bundle = read_artifact_file(bundle_file) if bundle_file else None
        show_units = read_artifact_file(show_unit_file) if show_unit_file else None
        show_model = read_artifact_file(show_model_file) if show_model_file else None
        model_dump = read_artifact_file(model_dump_file) if model_dump_file else None

        return ModelArtifact(
            status=_parse_status(status) if status is not None else None,
            bundle=bundle,
            show_units=_parse_show_units(show_units) if show_units is not None else None,
            show_model=_parse_show_model(show_model) if show_model is not None else None,
            model_dump=model_dump,
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
    def bundle(self) -> Dict[str, Mapping[str, Any]]:
        """Get the Juju bundle for all the models (opaque mapping)."""
        result: Dict[str, Mapping[str, Any]] = {}
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
    def model_dump(self) -> Dict[str, Mapping[str, Any]]:
        """Get the Juju dump-model information for all the models (opaque mapping)."""
        result: Dict[str, Mapping[str, Any]] = {}
        for model, model_artifact in self.artifacts.items():
            if model_artifact.model_dump:
                result[model] = model_artifact.model_dump
        return result
