"""Universal assertions for deployments."""

import logging
from enum import Enum
from typing import Dict, List

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
    for builtin in Builtins.all():
        properties.update({builtin.name(): builtin.schema()})
    schema.update({"properties": properties})
    return schema


class _Builtin(object):
    """Baseclass for builtin assertions.

    Each builtin validates its assertions against a schema and the assertions against artifacts.
    """

    def __init__(self, probe_name: str, assertion: Dict):
        self.probe_name = probe_name
        self.assertion = assertion

    def is_schema_valid(self) -> bool:
        """Check that the provided schema is valid."""
        valid = False
        try:
            jsonschema.validate(self.assertion, self.schema())
            valid = True
        except jsonschema.ValidationError as e:
            log.error(f"Failed to validate schema for {self.probe_name}: {e}")
        return valid

    @classmethod
    def schema(cls) -> Schema:
        """The Builtin's JSON schema."""
        raise NotImplementedError

    def validate(self, artifacts: Artifacts) -> List[AssertionResult]:
        """Builtin assertions against artifacts."""
        raise NotImplementedError

    @classmethod
    def name(cls) -> str:
        return cls.__name__.lower()


class Applications(_Builtin):
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
        if not self.assertion or not artifacts.status:
            log.warning(
                "The status artifact was not supplied for the Applications Builtin assertion."
            )
            return results

        func_name = f"builtin:{Builtins.APPLICATIONS.name.lower()}"

        app_assertion_names = [app["name"] for app in self.assertion]
        for status_name, status in artifacts.status.items():
            names_found = False
            for name, app in status["applications"].items():
                if name not in app_assertion_names:
                    # TODO try to filter out all the apps beforehand instead of using continue
                    # apps = dict(filter(lambda n, a: n not in app_assertion_names,
                    # -> status["applications"].items()))
                    continue

                # FIXME this only checks if all names are wrong, fix for if 1 name is wrong
                names_found = True
                for app_assertion in self.assertion:
                    if app_assertion["name"] == name:
                        if "minimum" in app_assertion and app["scale"] < app_assertion["minimum"]:
                            exception = Exception(
                                f"{name} scale ({app['scale']}) "
                                f"is below the allowable limit: {app_assertion['minimum']}"
                            )
                            results.append(AssertionResult(func_name, False, exception))
                        if "maximum" in app_assertion and app["scale"] > app_assertion["maximum"]:
                            exception = Exception(
                                f"{name} scale ({app['scale']}) "
                                f"exceeds the allowable limit: {app_assertion['maximum']}"
                            )
                            results.append(AssertionResult(func_name, False, exception))
            if not names_found:
                exception = Exception(
                    f"Application names: {app_assertion_names} were not found "
                    f"in the artifact: {status_name}."
                )
                results.append(AssertionResult(func_name, False, exception))

        if not results:
            results.append(AssertionResult(func_name, True))

        return results


class Relations(_Builtin):
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
        if not self.assertion or not artifacts.bundle:
            log.warning(
                "The bundle artifact was not supplied for the Relations Builtin assertion."
            )
            return results

        func_name = f"builtin:{Builtins.RELATIONS.name.lower()}"

        for relation in self.assertion:
            bundle_relations = [
                relation
                for bundle in artifacts.bundle.values()
                for relation in bundle["relations"]
            ]
            rel_pair = [relation["requires"], relation["provides"]]
            if (
                rel_pair not in bundle_relations
                and [rel_pair[1], rel_pair[0]] not in bundle_relations
            ):
                exception = Exception(f"Relation ({rel_pair}) not found in {bundle_relations}")
                results.append(AssertionResult(func_name, False, exception))

        if not results:
            results.append(AssertionResult(func_name, True))

        return results


class Offers(_Builtin):
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
        if not self.assertion or not artifacts.status:
            log.warning("The status artifact was not supplied for the Offers Builtin assertion.")
            return results

        func_name = f"builtin:{Builtins.OFFERS.name.lower()}"

        offer_assertion_names = [offer["name"] for offer in self.assertion]
        for status_name, status in artifacts.status.items():
            names_found = False
            for name, offer in status["offers"].items():
                if name not in offer_assertion_names:
                    # TODO try to filter out all the offers beforehand instead of using continue
                    continue

                # FIXME this only checks if all names are wrong, fix for if 1 name is wrong
                names_found = True
                for offer_assertion in self.assertion:
                    if offer_assertion["name"] == name:
                        if offer_assertion["endpoint"] not in offer["endpoints"]:
                            exception = Exception(
                                f"{name}: endpoint ({offer_assertion['endpoint']}) "
                                f"not in ({offer['endpoints'].keys()})"
                            )
                            results.append(AssertionResult(func_name, False, exception))
                            continue
                        interface = offer["endpoints"][offer_assertion["endpoint"]]["interface"]
                        if offer_assertion["interface"] != interface:
                            exception = Exception(
                                f"{name}: interface ({offer_assertion['interface']}) "
                                f"!= ({interface})"
                            )
                            results.append(AssertionResult(func_name, False, exception))

            if not names_found:
                exception = Exception(
                    f"Offer names: {offer_assertion_names} were not found "
                    f"in the artifact: {status_name}."
                )
                results.append(AssertionResult(func_name, False, exception))

        if not results:
            results.append(AssertionResult(func_name, True))

        return results


class Consumes(_Builtin):
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


class Builtins(Enum):
    """Supported Builtin assertion classes."""

    APPLICATIONS = Applications
    RELATIONS = Relations
    OFFERS = Offers
    CONSUMES = Consumes

    @staticmethod
    def all():
        """Return all Builtin classes."""
        return [f.value for f in Builtins]
