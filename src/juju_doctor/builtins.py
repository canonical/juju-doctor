"""Universal assertions for deployments."""

# FIXME Bundles use app names not charm names. Consider switching to status

import logging
from typing import Annotated, Dict, List, Optional, TypeVar

from pydantic import BaseModel, Field, model_validator
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.results import SUPPORTED_PROBE_FUNCTIONS, AssertionResult

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)
T = TypeVar("T")


class ApplicationAssertion(BaseModel):
    """Schema for a builtin Application definition in a RuleSet."""

    name: str
    minimum: Optional[Annotated[int, Field(ge=0)]] = None
    maximum: Optional[Annotated[int, Field(ge=0)]] = None

    class Config:
        """Disallow extra attributes."""

        extra = "forbid"


class RelationAssertion(BaseModel):
    """Schema for a builtin Relation definition in a RuleSet."""

    provides: str
    requires: str

    class Config:
        """Disallow extra attributes."""

        extra = "forbid"


class OfferAssertion(BaseModel):
    """Schema for a builtin Offer definition in a RuleSet."""

    name: str
    endpoint: Optional[str] = None
    interface: Optional[str] = None

    class Config:
        """Disallow extra attributes."""

        extra = "forbid"


class ProbeAssertion(BaseModel):
    """Schema for a builtin Probe definition in a RuleSet."""

    name: str
    type: str
    url: str

    class Config:
        """Disallow extra attributes."""

        extra = "forbid"


# TODO: I don't like this, but it works
class BuiltinArtifacts:
    """Track the artifacts used by builtin assertions."""

    artifacts: Dict = dict.fromkeys(SUPPORTED_PROBE_FUNCTIONS, 0)


class BuiltinModel(BaseModel):
    """A pydantic model of all Builtin types in a RuleSet(RuleSetModel)."""

    applications: Optional[List[ApplicationAssertion]] = None
    relations: Optional[List[RelationAssertion]] = None
    offers: Optional[List[OfferAssertion]] = None

    def validate_applications(
        self, artifacts: Artifacts, probe_path: str
    ) -> List[AssertionResult]:
        """Application assertions against artifacts.

        Iterate through the statuses of applications in an artifact, checking if all
        required application names are present and validate their scale against specified
        minimum and maximum limits. If any assertions fail, append an AssertionResult
        indicating the failure; otherwise, return a success result if no issues are found.

        NOTE: Any variables which refer to the application assertion will be private, whereas
        variables which refer to the artifact will be public.
        E.g. _app is an application in the assertion from the RuleSet
        E.g. app is an application in the artifact
        """
        _apps = self.applications
        if not _apps:
            return []

        BuiltinArtifacts.artifacts["status"] += 1
        if not artifacts.status:
            log.warning(f'No "status" artifact was provided for probe: {probe_path}.')
            return []

        _app_names = [app.name for app in _apps]

        results: List[AssertionResult] = []
        for status_name, status in artifacts.status.items():
            if not all(_app in status["applications"].keys() for _app in _app_names):
                exception = Exception(f'Not all apps: {_app_names} were found in "{status_name}"')
                results.append(AssertionResult(None, False, exception))
            apps_relevant = dict(
                filter(lambda item: item[0] in _app_names, status["applications"].items())
            )
            for name, app in apps_relevant.items():
                for _app in _apps:
                    if _app.name != name:
                        continue
                    if _app.minimum is not None and app["scale"] < _app.minimum:
                        exception = Exception(
                            f"{name} scale ({app['scale']}) "
                            f"is below the allowable limit: {_app.minimum}"
                        )
                        # FIXME: Exception (builtins:applications/None): Why is there /None?
                        results.append(AssertionResult(None, False, exception))
                    if _app.maximum is not None and app["scale"] > _app.maximum:
                        exception = Exception(
                            f"{name} scale ({app['scale']}) "
                            f"exceeds the allowable limit: {_app.maximum}"
                        )
                        results.append(AssertionResult(None, False, exception))

        if not results:
            results.append(AssertionResult(None, True))

        return results

    def validate_relations(
        self, artifacts: Artifacts, probe_path: str
    ) -> List[AssertionResult]:
        """Relation assertions against artifacts.

        Check for the presence of specified relations in a given artifact by iterating through the
        relations of each bundle and verifying if the required relation pairs exist. If any
        relation is missing, append an AssertionResult indicating failure; otherwise, return a
        success result if all relations are found.

        NOTE: Any variables which refer to the relation assertion will be private, whereas
        variables which refer to the artifact will be public.
        E.g. _rel is a relation in the assertion from the RuleSet
        E.g. rel is a relation in the artifact
        """
        _rels = self.relations
        if not _rels:
            return []

        BuiltinArtifacts.artifacts["bundle"] += 1
        if not artifacts.bundle:
            log.warning(f'No "bundle" artifact was provided for probe: {probe_path}.')
            return []

        results: List[AssertionResult] = []
        # TODO Bundle:relations only show charm names, not app names.
        # Either switch to Status assertion or cross-reference to Bundle:applications:charm
        for _rel in _rels:
            rels = [rel for bundle in artifacts.bundle.values() for rel in bundle["relations"]]
            # TODO I think the API requires/provides is a lie
            _rel_pair = [_rel.requires, _rel.provides]
            if _rel_pair not in rels and [_rel_pair[1], _rel_pair[0]] not in rels:
                exception = Exception(f"Relation ({_rel_pair}) not found in {rels}")
                results.append(AssertionResult(None, False, exception))

        if not results:
            results.append(AssertionResult(None, True))

        return results

    def validate_offers(
        self, artifacts: Artifacts, probe_path: str
    ) -> List[AssertionResult]:
        """Offer assertions against artifacts.

        Verify that all specified offers are present in the artifact's status and check if the
        corresponding endpoints (and interfaces) match the expected values. If there is a diff,
        append an AssertionResult indicating failure; otherwise, it returns a success
        result if all checks pass.

        NOTE: Any variables which refer to the relation assertion will be private, whereas
        variables which refer to the artifact will be public.
        E.g. _rel is a relation in the assertion from the RuleSet
        E.g. rel is a relation in the artifact
        """
        _offers = self.offers
        if not _offers:
            return []

        BuiltinArtifacts.artifacts["status"] += 1
        if not artifacts.status:
            log.warning(f'No "status" artifact was provided for probe: {probe_path}.')
            return []

        _offer_names = [_offer.name for _offer in _offers]

        results: List[AssertionResult] = []
        for status_name, status in artifacts.status.items():
            if not all(_offer in status["offers"] for _offer in _offer_names):
                exception = Exception(
                    f'Not all offers: {_offer_names} were found in "{status_name}"'
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


class RuleSetModel(BuiltinModel):
    """A pydantic model of a RuleSet."""

    name: str
    probes: Optional[List[ProbeAssertion]] = None

    class Config:
        """Disallow extra attributes."""

        extra = "forbid"

    @model_validator(mode="after")
    # FIXME: In Python 3.11+ we can replace "RuleSetModel[T]" with typing.Self
    def at_least_one_assertion_is_defined(self) -> "RuleSetModel[T]":
        """Check if at least one of the optional fields is present."""
        expected_fields = {"probes"} | set(BuiltinModel.model_fields.keys())
        if not any(getattr(self, f) for f in expected_fields):
            raise ValueError(
                f'At least one of the assertion fields: "{expected_fields}" must be provided.'
            )
        return self
