"""Universal assertions for deployments."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import jsonschema
from referencing.jsonschema import Schema
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts

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


class AssertionStatus(Enum):
    """Result of probe or builtin assertion."""

    PASS = "pass"
    FAIL = "fail"


class _Builtin(object):
    """Baseclass for builtin assertions.

    Each builtin validates its assertions against a schema and the assertions against artifacts.
    """

    # TODO How can I type hint here "Probe" without a circular dep
    def __init__(self, probe, assertion: Dict):
        self.probe = probe
        self.assertion = assertion

    def is_schema_valid(self) -> bool:
        """Check that the provided schema is valid."""
        valid = False
        try:
            jsonschema.validate(self.assertion, self.schema())
            valid = True
        except jsonschema.ValidationError as e:
            log.error(f"Failed to validate schema for {self.probe.name}: {e}")
        return valid

    @classmethod
    def schema(cls) -> Schema:
        """The Builtin's JSON schema."""
        raise NotImplementedError

    def validate(self, artifacts: Artifacts) -> List["AssertionResult"]:
        """Assert Builtins against artifacts or live models."""
        raise NotImplementedError

    @classmethod
    def name(cls) -> str:
        return cls.__name__.lower()


class Applications(_Builtin):
    """A Builtin assertion which defines applications requirements."""

    def __init__(self, probe, assertion: Dict):  # noqa: D107
        super().__init__(probe, assertion)

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

    def validate(self, artifacts: Artifacts) -> List["AssertionResult"]:
        """Assert Applications against artifacts or live models."""
        results: List[AssertionResult] = []
        if not self.assertion or not artifacts.status:
            log.warning(
                "The status artifact was not supplied for the Applications Builtin assertion."
            )
            return results

        passed = True
        func_name = f"builtin:{Builtins.APPLICATIONS.name.lower()}"

        app_assertion_names = [app["name"] for app in self.assertion]
        for status in artifacts.status.values():
            for name, app in status["applications"].items():
                if name not in app_assertion_names:
                    # FIXME If no names are in the apps, we have a false positive, passing probe
                    continue

                for app_assertion in self.assertion:
                    if app_assertion["name"] == name:
                        if "minimum" in app_assertion and app["scale"] < app_assertion["minimum"]:
                            passed = False
                            exception = Exception(
                                f"{name} scale ({app['scale']}) "
                                f"is below the allowable limit: {app_assertion['minimum']}"
                            )
                            results.append(
                                AssertionResult(self.probe, func_name, passed, exception)
                            )
                        if "maximum" in app_assertion and app["scale"] > app_assertion["maximum"]:
                            passed = False
                            exception = Exception(
                                f"{name} scale ({app['scale']}) "
                                f"exceeds the allowable limit: {app_assertion['maximum']}"
                            )
                            results.append(
                                AssertionResult(self.probe, func_name, passed, exception)
                            )

        if passed:
            results.append(AssertionResult(self.probe, func_name, passed))

        return results


class Relations(_Builtin):
    """A Builtin assertion which defines relation requirements."""

    def __init__(self, probe, assertion: Dict):  # noqa: D107
        super().__init__(probe, assertion)

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

    def validate(self, artifacts: Artifacts) -> List["AssertionResult"]:
        """Assert Relations against artifacts or live models."""
        results: List[AssertionResult] = []
        if not self.assertion or not artifacts.bundle:
            log.warning(
                "The bundle artifact was not supplied for the Relations Builtin assertion."
            )
            return results

        passed = True
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
                passed = False
                exception = Exception(f"Relation ({rel_pair}) not found in {bundle_relations}")
                results.append(AssertionResult(self.probe, func_name, passed, exception))
        if passed:
            results.append(AssertionResult(self.probe, func_name, passed))

        return results


class Offers(_Builtin):
    """A Builtin assertion which defines model offer requirements."""

    def __init__(self, probe, assertion: Dict):  # noqa: D107
        super().__init__(probe, assertion)

    @classmethod
    def schema(cls) -> Schema:
        """The JSON schema for Offers."""
        return {}

    def validate(self, artifacts: Artifacts) -> List["AssertionResult"]:
        """Assert Offers against artifacts or live models."""
        results: List[AssertionResult] = []
        if not self.assertion or not artifacts.status:
            log.warning("The status artifact was not supplied for the Offers Builtin assertion.")
            return results

        passed = True
        func_name = f"builtin:{Builtins.OFFERS.name.lower()}"

        offer_assertion_names = [offer["name"] for offer in self.assertion]
        for status in artifacts.status.values():
            for name, offer in status["offers"].items():
                if name not in offer_assertion_names:
                    # FIXME If no names are in the apps, we have a false positive, passing probe
                    continue

                for offer_assertion in self.assertion:
                    if offer_assertion["name"] == name:
                        if offer_assertion["endpoint"] not in offer["endpoints"]:
                            passed = False
                            exception = Exception(
                                f"{name}: endpoint ({offer_assertion['endpoint']}) "
                                f"not in ({offer['endpoints'].keys()})"
                            )
                            results.append(
                                AssertionResult(self.probe, func_name, passed, exception)
                            )
                            continue
                        interface = offer["endpoints"][offer_assertion["endpoint"]]["interface"]
                        if offer_assertion["interface"] != interface:
                            passed = False
                            exception = Exception(
                                f"{name}: interface ({offer_assertion['interface']}) "
                                f"!= ({interface})"
                            )
                            results.append(
                                AssertionResult(self.probe, func_name, passed, exception)
                            )

        if passed:
            results.append(AssertionResult(self.probe, func_name, passed))

        return results


class Consumes(_Builtin):
    """A Builtin assertion which defines cross-model relation requirements."""

    def __init__(self, probe, assertion: Dict):  # noqa: D107
        super().__init__(probe, assertion)

    @classmethod
    def schema(cls) -> Schema:
        """The JSON schema for Consumes."""
        return {}

    def validate(self, artifacts: Artifacts) -> List["AssertionResult"]:
        """Assert Consumes against artifacts or live models."""
        # TODO The artifacts were not generated with a CMR, so we are missing SAAS
        raise NotImplementedError


class Builtins(Enum):
    """Supported Probe file extensions."""

    APPLICATIONS = Applications
    RELATIONS = Relations
    OFFERS = Offers
    CONSUMES = Consumes

    @staticmethod
    def all():
        """Return all Builtin classes."""
        return [f.value for f in Builtins]


@dataclass
class ResultInfo:
    """Class for gathering information needed to display assertions results."""

    node_tag: str = ""
    exception_msg: str = ""


# TODO AssertionResult is identical to ProbeAssertionResult, but we have circular import
@dataclass
class AssertionResult:
    """A helper class to wrap results for a Probe's functions."""

    probe: Any  # TODO Fix type hinting due to circular module imports
    func_name: str
    passed: bool
    exception: Optional[BaseException] = None

    @property
    def status(self) -> str:
        """Result of the probe."""
        return AssertionStatus.PASS.value if self.passed else AssertionStatus.FAIL.value

    def get_text(self, output_fmt) -> ResultInfo:
        """Probe results (formatted as Pretty-print) as a string."""
        exception_msg = ""
        green = output_fmt.rich_map["green"]
        red = output_fmt.rich_map["red"]
        if self.passed:
            return ResultInfo(f"{green} {self.probe.name}", exception_msg)
        # If the probe failed
        exception_suffix = f"({self.probe.name}/{self.func_name}): {self.exception}"
        if output_fmt.format.lower() == "json":
            exception_msg = f"Exception {exception_suffix}"
        else:
            if output_fmt.verbose:
                exception_msg = f"[b]Exception[/b] {exception_suffix}"
        return ResultInfo(f"{red} {self.probe.name}", exception_msg)
