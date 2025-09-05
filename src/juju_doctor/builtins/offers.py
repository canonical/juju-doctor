import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.results import AssertionResult
from juju_doctor.ruleset import BaseBuiltin, BuiltinArtifacts

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class OfferAssertion(BaseModel):
    """Schema for a builtin Offer definition in a RuleSet."""
    model_config = ConfigDict(extra="forbid")

    name: str
    endpoint: Optional[str] = Field(None)
    interface: Optional[str] = Field(None)


class OfferBuiltin(BaseBuiltin):
    assertions: List[OfferAssertion]

    def validate(self, artifacts: Artifacts, probe_path: str) -> List[AssertionResult]:
        """Offer assertions against a status artifact.

        Verify that all specified offers are present in the artifact's status and check if the
        corresponding endpoints (and interfaces) match the expected values. If there is a diff,
        append an AssertionResult indicating failure; otherwise, it returns a success
        result if all checks pass.

        NOTE: Any variables which refer to the offer assertion will be private, whereas
        variables which refer to the artifact will be public.
        E.g. _offer is an offer in the assertion from the RuleSet
        E.g. offer is an offer in the artifact
        """
        _offers = self.assertions
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
