"""Universal assertions for deployments."""

import logging
from abc import ABC
from enum import Enum
from typing import Dict, List, Optional

import jsonschema
from referencing.jsonschema import Schema
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.results import AssertionResult

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


def build_unified_schema() -> Schema:
    """Unify the Builtin schemas to create a Ruleset schema."""
    schema: Schema = {"type": "object", "additionalProperties": False}
    properties: Dict = {"name": {"type": "string"}}
    for builtin in SupportedBuiltins.all():
        properties.update({builtin.name(): builtin.schema()})
    schema.update({"properties": properties})
    return schema


class Builtin(ABC):
    """Baseclass for builtin assertions.

    A builtin validates its assertions against a schema and the assertions against artifacts.
    """

    def __init__(self, probe_name: str, assertion: Dict):
        """Builtin context.

        Args:
            probe_name: the name of the probe
            assertion: the content to validate against
            valid_schema: whether the supplied assertion has a valid schema
            artifact_type: a string representing the artifact type of a Juju deployment
        """
        self.probe_name = probe_name
        self.assertion = assertion
        self.valid_schema: bool = True
        self.artifact_type: Optional[str] = None

    def validate_schema(self):
        """Check that the provided schema is valid."""
        try:
            jsonschema.validate(self.assertion, self.schema())
        except jsonschema.ValidationError as e:
            log.error(f"Failed to validate schema for {self.probe_name}: {e}")
            self.valid_schema = False

    @classmethod
    def schema(cls) -> Schema:
        """The Builtin's JSON schema."""
        raise NotImplementedError

    def validate(self, artifacts: Artifacts) -> List[AssertionResult]:
        """Builtin assertions against artifacts."""
        raise NotImplementedError

    @classmethod
    def name(cls) -> str:
        """Lowercase name of the class."""
        return cls.__name__.lower()


class Applications(Builtin):
    """A Builtin assertion which defines applications requirements."""

    def __init__(self, probe_name: str, assertion: Dict):  # noqa: D107
        super().__init__(probe_name, assertion)

    @classmethod
    def schema(cls) -> Schema:
        """The JSON schema for Applications."""
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "minimum": {"type": "integer"},
                    "maximum": {"type": "integer"},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        }

    def validate(self, artifacts: Artifacts) -> List[AssertionResult]:
        """Application assertions against artifacts."""
        results: List[AssertionResult] = []
        self.artifact_type = "status"
        artifact_obj = getattr(artifacts, self.artifact_type)
        if not self.assertion or not artifact_obj:
            log.warning(
                "No status artifact was provided for the Applications Builtin assertion."
            )
            return results

        app_assertion_names = [app["name"] for app in self.assertion]
        for status_name, status in artifact_obj.items():
            if not all(item in status["applications"] for item in app_assertion_names):
                exception = Exception(
                    f"Not all apps: {app_assertion_names} were found in {status_name}"
                )
                results.append(AssertionResult(None, False, exception))
            relevant_apps = dict(
                filter(lambda item: item[0] in app_assertion_names, status["applications"].items())
            )
            for name, app in relevant_apps.items():
                for app_assertion in self.assertion:
                    if app_assertion["name"] == name:
                        if "minimum" in app_assertion and app["scale"] < app_assertion["minimum"]:
                            exception = Exception(
                                f"{name} scale ({app['scale']}) "
                                f"is below the allowable limit: {app_assertion['minimum']}"
                            )
                            results.append(AssertionResult(None, False, exception))
                        if "maximum" in app_assertion and app["scale"] > app_assertion["maximum"]:
                            exception = Exception(
                                f"{name} scale ({app['scale']}) "
                                f"exceeds the allowable limit: {app_assertion['maximum']}"
                            )
                            results.append(AssertionResult(None, False, exception))

        if not results:
            results.append(AssertionResult(None, True))

        return results


class Relations(Builtin):
    """A Builtin assertion which defines relation requirements."""

    def __init__(self, probe_name: str, assertion: Dict):  # noqa: D107
        super().__init__(probe_name, assertion)

    @classmethod
    def schema(cls) -> Schema:
        """The JSON schema for Relations."""
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"provides": {"type": "string"}, "requires": {"type": "string"}},
                "required": ["provides", "requires"],
                "additionalProperties": False,
            },
        }

    def validate(self, artifacts: Artifacts) -> List[AssertionResult]:
        """Relation assertions against artifacts."""
        results: List[AssertionResult] = []
        self.artifact_type = "bundle"
        artifact_obj = getattr(artifacts, self.artifact_type)
        if not self.assertion or not artifact_obj:
            log.warning(
                "No bundle artifact was provided for the Relations Builtin assertion."
            )
            return results

        for relation in self.assertion:
            bundle_relations = [
                relation
                for bundle in artifact_obj.values()
                for relation in bundle["relations"]
            ]
            rel_pair = [relation["requires"], relation["provides"]]
            if (
                rel_pair not in bundle_relations
                and [rel_pair[1], rel_pair[0]] not in bundle_relations
            ):
                exception = Exception(f"Relation ({rel_pair}) not found in {bundle_relations}")
                results.append(AssertionResult(None, False, exception))

        if not results:
            results.append(AssertionResult(None, True))

        return results


class Offers(Builtin):
    """A Builtin assertion which defines model offer requirements."""

    def __init__(self, probe_name: str, assertion: Dict):  # noqa: D107
        super().__init__(probe_name, assertion)

    @classmethod
    def schema(cls) -> Schema:
        """The JSON schema for Offers."""
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "endpoint": {"type": "string"},
                    "interface": {"type": "string"},
                },
                "required": ["name", "endpoint", "interface"],
                "additionalProperties": False,
            },
        }

    def validate(self, artifacts: Artifacts) -> List[AssertionResult]:
        """Offer assertions against artifacts or live models."""
        results: List[AssertionResult] = []
        self.artifact_type = "status"
        artifact_obj = getattr(artifacts, self.artifact_type)
        if not self.assertion or not artifact_obj:
            log.warning("No status artifact was provided for the Offers Builtin assertion.")
            return results

        offer_assertion_names = [offer["name"] for offer in self.assertion]
        for status_name, status in artifact_obj.items():
            if not all(item in status["offers"] for item in offer_assertion_names):
                exception = Exception(
                    f"Not all offers: {offer_assertion_names} were found in {status_name}"
                )
                results.append(AssertionResult(None, False, exception))
            relevant_offers = dict(
                filter(lambda item: item[0] in offer_assertion_names, status["offers"].items())
            )
            for name, offer in relevant_offers.items():
                for offer_assertion in self.assertion:
                    if offer_assertion["name"] == name:
                        if offer_assertion["endpoint"] not in offer["endpoints"]:
                            exception = Exception(
                                f"{name}: endpoint ({offer_assertion['endpoint']}) "
                                f"not in ({offer['endpoints'].keys()})"
                            )
                            results.append(AssertionResult(None, False, exception))
                            continue
                        interface = offer["endpoints"][offer_assertion["endpoint"]]["interface"]
                        if offer_assertion["interface"] != interface:
                            exception = Exception(
                                f"{name}: interface ({offer_assertion['interface']}) "
                                f"!= ({interface})"
                            )
                            results.append(AssertionResult(None, False, exception))

        if not results:
            results.append(AssertionResult(None, True))

        return results


class Consumes(Builtin):
    """A Builtin assertion which defines cross-model relation requirements."""

    def __init__(self, probe_name: str, assertion: Dict):  # noqa: D107
        super().__init__(probe_name, assertion)

    @classmethod
    def schema(cls) -> Schema:
        """The JSON schema for Consumes."""
        return {}

    def validate(self, artifacts: Artifacts) -> List[AssertionResult]:
        """Consume assertions against artifacts or live models."""
        # TODO The artifacts were not generated with a CMR, so we are missing SAAS
        raise NotImplementedError


class Probes(Builtin):
    """Programmatic assertions against artifacts."""

    def __init__(self, probe_name: str, assertion: Dict):  # noqa: D107
        super().__init__(probe_name, assertion)
    """Programmatic assertions against artifacts."""

    @classmethod
    def schema(cls) -> Schema:
        """The JSON schema for Probes."""
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["name", "type", "url"],
                "additionalProperties": False,
            },
        }

    def validate(self, artifacts: Artifacts) -> List[AssertionResult]:
        """Programmatic assertions against artifacts or live models.

        Note: The validation is handled in probes.py so we return no AssertionResults
        """
        return []


class SupportedBuiltins(Enum):
    """Supported Builtin assertion classes.

    Note: Probes is an outlier here since its validation is handled in probes.py unlike the others.
          In some cases you may want to filter out Probes in the `all` method.
    """

    applications = Applications
    relations = Relations
    offers = Offers
    consumes = Consumes
    probes = Probes

    @staticmethod
    def all(filter: List = []):
        """Return all Builtin classes."""
        return [f.value for f in SupportedBuiltins if f.value not in filter]
