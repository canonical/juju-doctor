"""Universal assertions for deployments."""

# FIXME Bundles use app names not charm names. Consider switching to status

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.results import AssertionResult

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


def build_unified_schema() -> dict:
    """Unify the Builtin schemas to create a Ruleset schema."""
    return RuleSetModel.model_json_schema()


@dataclass
class Builtin:
    """A Builtin assertion which defines applications requirements.

    ApplicationsBuiltin(Validator(self.probe.name, self.assertion, ApplicationAssertion))
    """

    probe_name: str
    assertion: List[Dict]
    schema: "BaseAssertion"
    artifact_type: Optional[str] = None


@dataclass
class AssertionContext:
    """Context that the sanity check provides the validation function of a Builtin."""

    pydantic_objs: List["BaseAssertion"]
    artifact: Optional[Any] = None


class BaseAssertion(BaseModel):
    """Schema for a builtin definition in a RuleSet."""

    @classmethod
    def sanity_check(
        cls, builtin: Builtin, artifacts: Artifacts, artifact_type: Optional[str] = None
    ) -> AssertionContext:
        """Check if each assertion has a valid schema."""
        try:
            pydantic_objs = [cls(**app) for app in builtin.assertion]
        except ValidationError as e:
            pydantic_objs = None
            log.error(e)

        if not artifact_type:
            return AssertionContext(pydantic_objs, None)

        builtin.artifact_type = artifact_type
        artifact_obj = getattr(artifacts, artifact_type) or {}
        if not artifact_obj:
            log.warning(
                f"No {artifact_type} artifact was provided for the Applications Builtin assertion."
            )

        return AssertionContext(pydantic_objs, artifact_obj)


class ApplicationAssertion(BaseAssertion):
    """Schema for a builtin Application definition in a RuleSet."""

    name: str
    minimum: Optional[Annotated[int, Field(ge=0)]] = None
    maximum: Optional[Annotated[int, Field(ge=0)]] = None

    @classmethod
    def validate_assertions(cls, builtin: Builtin, artifacts: Artifacts) -> List[AssertionResult]:
        """Application assertions against artifacts.

        TODO: update this
        Any variables which refer to the application assertion will be private, whereas variables
        which refer to the artifact will be public.
        E.g. _app is an application in the assertion from the RuleSet
        E.g. app is an application in the artifact
        """
        assertion_context = cls.sanity_check(builtin, artifacts, "status")
        _apps = assertion_context.pydantic_objs
        _app_names = [app.name for app in _apps]

        results: List[AssertionResult] = []
        for status_name, status in assertion_context.artifact.items():
            app_names = [app["charm"] for app in status["applications"].values()]
            if not all(_app in app_names for _app in _app_names):
                exception = Exception(f"Not all apps: {_app_names} were found in {status_name}")
                results.append(AssertionResult(None, False, exception))
            apps_relevant = dict(
                filter(lambda item: item[0] in _app_names, status["applications"].items())
            )
            for name, app in apps_relevant.items():
                for _app in _apps:
                    if _app.name == name:
                        if _app.minimum and app["scale"] < _app.minimum:
                            exception = Exception(
                                f"{name} scale ({app['scale']}) "
                                f"is below the allowable limit: {_app.minimum}"
                            )
                            results.append(AssertionResult(None, False, exception))
                        if _app.maximum and app["scale"] > _app.maximum:
                            exception = Exception(
                                f"{name} scale ({app['scale']}) "
                                f"exceeds the allowable limit: {_app.maximum}"
                            )
                            results.append(AssertionResult(None, False, exception))

        if not results:
            results.append(AssertionResult(None, True))

        return results


class RelationAssertion(BaseAssertion):
    """Schema for a builtin Relation definition in a RuleSet."""

    provides: str
    requires: str

    @classmethod
    def validate_assertions(cls, builtin: Builtin, artifacts: Artifacts) -> List[AssertionResult]:
        """Relation assertions against artifacts.

        TODO: update this
        Any variables which refer to the relation assertion will be private, whereas variables
        which refer to the artifact will be public.
        E.g. _rel is a relation in the assertion from the RuleSet
        E.g. rel is a relation in the artifact
        """
        # TODO: Builtin is only needed for sanity_check, maybe I can abstract that
        assertion_context = cls.sanity_check(builtin, artifacts, "bundle")
        _rels = assertion_context.pydantic_objs

        results: List[AssertionResult] = []
        # TODO Bundle:relations only show charm names, not app names.
        # Either switch to Status assertion or cross-reference to Bundle:applications:charm
        for _rel in _rels:
            rels = [
                rel
                for bundle in assertion_context.artifact.values()
                for rel in bundle["relations"]
            ]
            # TODO I think the API requires/provides is a lie
            _rel_pair = [_rel.requires, _rel.provides]
            if _rel_pair not in rels and [_rel_pair[1], _rel_pair[0]] not in rels:
                exception = Exception(f"Relation ({_rel_pair}) not found in {rels}")
                results.append(AssertionResult(None, False, exception))

        if not results:
            results.append(AssertionResult(None, True))

        return results


class OfferAssertion(BaseAssertion):
    """Schema for a builtin Offer definition in a RuleSet."""

    name: str
    endpoint: str = None
    interface: str = None

    @classmethod
    def validate_assertions(cls, builtin: Builtin, artifacts: Artifacts) -> List[AssertionResult]:
        """Offer assertions against artifacts.

        TODO: update this
        Any variables which refer to the relation assertion will be private, whereas variables
        which refer to the artifact will be public.
        E.g. _rel is a relation in the assertion from the RuleSet
        E.g. rel is a relation in the artifact
        """
        assertion_context = cls.sanity_check(builtin, artifacts, "status")
        _offers = assertion_context.pydantic_objs
        _offer_names = [_offer.name for _offer in _offers]

        results: List[AssertionResult] = []
        for status_name, status in assertion_context.artifact.items():
            if not all(_offer in status["offers"] for _offer in _offer_names):
                exception = Exception(
                    f"Not all offers: {_offer_names} were found in {status_name}"
                )
                results.append(AssertionResult(None, False, exception))
            relevant_offers = dict(
                filter(lambda item: item[0] in _offer_names, status["offers"].items())
            )
            for name, offer in relevant_offers.items():
                for _offer in _offers:
                    if _offer.name == name:
                        if _offer.endpoint not in offer["endpoints"]:
                            exception = Exception(
                                f"{name}: endpoint ({_offer.endpoint}) "
                                f"not in ({offer['endpoints'].keys()})"
                            )
                            results.append(AssertionResult(None, False, exception))
                            continue
                        interface = offer["endpoints"][_offer.endpoint]["interface"]
                        if _offer.interface != interface:
                            exception = Exception(
                                f"{name}: interface ({_offer.interface}) != ({interface})"
                            )
                            results.append(AssertionResult(None, False, exception))

        if not results:
            results.append(AssertionResult(None, True))

        return results


class ProbeAssertion(BaseAssertion):
    """Schema for a builtin Probe definition in a RuleSet."""

    name: str
    type: str
    url: str

    @classmethod
    def validate_assertions(cls, builtin: Builtin, artifacts: Artifacts) -> List[AssertionResult]:
        """Programmatic assertions against artifacts.

        Note: ProbeAssertion is an outlier since its validation is handled in probes.py unlike the
        other BaseAssertions. We still validate each probe definition against the schema.
        """
        cls.sanity_check(builtin, artifacts)
        return []


class RuleSetModel(BaseModel):
    applications: Optional[List[ApplicationAssertion]] = None
    relations: Optional[List[RelationAssertion]] = None
    offers: Optional[List[OfferAssertion]] = None
    probes: Optional[List[ProbeAssertion]] = None


class SupportedBuiltins(Enum):
    """Supported Builtin assertion classes.

    Note: Probes is an outlier here since its validation is handled in probes.py unlike the others.
          In some cases you may want to filter out Probes in the `all` method.
    """

    applications = ApplicationAssertion
    relations = RelationAssertion
    offers = OfferAssertion
    probes = ProbeAssertion

    # TODO: Is this needed?
    # TODO: Create a unified schema, likely with BaseModel.model_dump_json()
    @staticmethod
    def all(filter: List = []):
        """Return all Builtin classes."""
        return [f.value for f in SupportedBuiltins if f.value not in filter]
