import logging
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from rich.logging import RichHandler
from typing_extensions import Self

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class OfferAssertion(BaseModel):
    """Schema for a builtin Offer definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(alias="offer-name")
    endpoint: Optional[str] = Field(None)
    interface: Optional[str] = Field(None)

    @model_validator(mode='after')
    def check_endpoint_if_interface(self) -> Self:
        if self.interface is not None and self.endpoint is None:
            # TODO: Better message? Add a test for this?
            raise ValueError("The endpoint must be defined if the interface is defined")
        return self


def status(juju_statuses, **kwargs):
    """Status assertion for offers existing verbatim.

    >>> status({"invalid-openstack-model": example_status_cyclic_agent_cos_proxy()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove the relation between ... (cos-proxy) and prometheus. ...
    >>> status({"invalid-openstack-model": example_multiple_proxies()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove the relation between "cp-2" (cos-proxy) and prometheus. ...
    >>> status({"valid-model": example_status_valid()})
    """
    assert kwargs["custom"], "No arguments were provided"

    _offers = [OfferAssertion(**offer) for offer in kwargs["custom"]]
    _offer_names = [_offer.name for _offer in _offers]
    for status_name, status in juju_statuses.items():
        if not all(_offer in status["offers"] for _offer in _offer_names):
            raise Exception(f'Not all offers: {_offer_names} were found in "{status_name}"')
        relevant_offers = dict(
            filter(lambda item: item[0] in _offer_names, status["offers"].items())
        )
        for name, offer in relevant_offers.items():
            for _offer in _offers:
                if _offer.name == name:
                    if _offer.endpoint is not None and _offer.endpoint not in offer["endpoints"]:
                        raise Exception(
                            f"{name}: endpoint ({_offer.endpoint}) "
                            f"not in ({offer['endpoints'].keys()})"
                        )
                    interface = offer["endpoints"][_offer.endpoint]["interface"]
                    if _offer.interface is not None and _offer.interface != interface:
                        raise Exception(f"{name}: interface ({_offer.interface}) != ({interface})")

# TODO
# name: RuleSet - test builtin fails assertions
# probes:
#   - name: Builtin offer-exists
#     type: builtin/offer-exists
#     with:
#       - offer-name: loki-logging
#         endpoint: logging-fake

# name: RuleSet - test builtin fails assertions
# probes:
#   - name: Builtin offer-exists
#     type: builtin/offer-exists
#     with:
#       - offer-name: loki-logging
#         endpoint: logging
#         interface: loki_push_api_fake

# name: RuleSet - test builtin fails assertions
# probes:
#   - name: Builtin offer-exists
#     type: builtin/offer-exists
#     with:
#       - offer-name: loki-logging-fake
