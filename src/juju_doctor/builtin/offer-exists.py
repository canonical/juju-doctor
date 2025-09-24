"""Offer-exists verbatim builtin plugin.

The probe checks that the given offer names exist with the specified endpoints and interfaces. This
could be useful when you need to check that a subset of a status (or bundle) is present.

To call this builtin within a RuleSet YAML file:

```yaml
name: RuleSet
probes:
    - name: Offers exist
      type: builtin/offer-exists
      with:
        - offer-name: grafana-dashboards
        - offer-name: loki-logging
          endpoint: logging
          interface: loki_push_api
```

Multiple assertions can be listed under the `with` key, adhering to the `OfferExists` schema.
"""

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from juju_doctor.artifacts import read_file


class OfferExists(BaseModel):
    """Schema for a builtin Offer definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(alias="offer-name")
    endpoint: Optional[str] = Field(None)
    interface: Optional[str] = Field(None)

    @model_validator(mode="after")
    def check_endpoint_if_interface(self) -> Self:
        """Validate that the endpoint exists if the endpoint is defined."""
        if self.interface is not None and self.endpoint is None:
            raise ValueError("The endpoint must be defined if the interface is defined")
        return self


def status(juju_statuses: Dict[str, Dict], **kwargs):
    """Status assertion for offers existing verbatim.

    >>> status({"0": example_status_missing_offers()}, **{"offer-name": "foo"})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: There are no offers present in ...

    >>> status({"0": example_status()}, **example_with_fake_name())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: Unable to find the offer (loki-logging-fake) in [...] ...

    >>> status({"0": example_status()}, **example_with_fake_endpoint())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The endpoint of loki-logging (logging-fake) is not found in [logging] ...

    >>> status({"0": example_status()}, **example_with_fake_interface())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The interface (loki_push_api_fake) of the provided offer (loki-logging) does not match the expected interface (loki_push_api) ...

    >>> status({"0": example_status()}, **example_with_interface_without_endpoint())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    pydantic_core._pydantic_core.ValidationError: ... The endpoint must be defined if the interface is defined ...
    """  # noqa: E501
    _offer = OfferExists(**kwargs)

    for status_name, status in juju_statuses.items():
        if not (offers := status.get("offers")):
            raise Exception(f'There are no offers present in "{status_name}"')
        if not (found_offer := offers.get(_offer.name)):
            raise Exception(
                f"Unable to find the offer ({_offer.name}) in "
                f'[{", ".join(offers.keys())}] in "{status_name}"'
            )
        if _offer.endpoint is not None and _offer.endpoint not in found_offer["endpoints"]:
            raise Exception(
                f"The endpoint of {_offer.name} ({_offer.endpoint}) is not found in "
                f'[{", ".join(found_offer["endpoints"].keys())}] in "{status_name}"'
            )
        interface = found_offer["endpoints"][_offer.endpoint]["interface"]
        if _offer.interface is not None and _offer.interface != interface:
            raise Exception(
                f"The interface ({_offer.interface}) of the provided offer ({_offer.name}) "
                f'does not match the expected interface ({interface}) in "{status_name}"'
            )


# ==========================
# Helper functions
# ==========================


def example_status():
    """Doctest input."""
    return read_file("tests/resources/artifacts/status.yaml")


def example_status_missing_offers():
    """Doctest input.

    This deployment status is missing offers.
    """
    return {}


def example_with_fake_name():
    """Doctest input."""
    return {"offer-name": "loki-logging-fake"}


def example_with_fake_endpoint():
    """Doctest input."""
    return {"offer-name": "loki-logging", "endpoint": "logging-fake"}


def example_with_fake_interface():
    """Doctest input."""
    return {"offer-name": "loki-logging", "endpoint": "logging", "interface": "loki_push_api_fake"}


def example_with_interface_without_endpoint():
    """Doctest input."""
    return {"offer-name": "loki-logging", "interface": "loki_push_api_fake"}
