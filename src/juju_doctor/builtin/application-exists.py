"""Application-exists verbatim builtin plugin."""

import logging
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field
from rich.logging import RichHandler

from juju_doctor.artifacts import read_file

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class ApplicationAssertion(BaseModel):
    """Schema for a builtin Application definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(alias="application-name")
    minimum: Optional[int] = Field(None, ge=0)
    maximum: Optional[int] = Field(None, ge=0)


def status(juju_statuses: Dict[str, Dict], **kwargs):
    """Status assertion for applications existing verbatim.

    >>> status({"0": example_status()}, with_args=example_with_fake_name())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: Unable to find the app (alertmanager_fake) in [...] ...

    >>> status({"0": example_status()}, with_args=example_with_scale_above_max())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The scale (1) of alertmanager exceeds the allowable limit: 0 ...

    >>> status({"0": example_status()}, with_args=example_with_scale_below_min())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The scale (1) of alertmanager is below the allowable limit: 2 ...
    """  # noqa: E501
    assert kwargs["with_args"], "No arguments were provided"

    _apps = [ApplicationAssertion(**_app) for _app in kwargs["with_args"]]
    for _app in _apps:
        for status_name, status in juju_statuses.items():
            if not (apps := status.get("applications")):
                continue
            if not (found_app := apps.get(_app.name)):
                raise Exception(
                    f"Unable to find the app ({_app.name}) in "
                    f'[{", ".join(apps.keys())}] in "{status_name}"'
                )
            if _app.minimum is not None and found_app["scale"] < _app.minimum:
                raise Exception(
                    f"The scale ({found_app['scale']}) of {_app.name} is below the allowable "
                    f'limit: {_app.minimum} in "{status_name}"'
                )
            if _app.maximum is not None and found_app["scale"] > _app.maximum:
                raise Exception(
                    f"The scale ({found_app['scale']}) of {_app.name} exceeds the allowable "
                    f'limit: {_app.maximum} in "{status_name}"'
                )


# ==========================
# Helper functions
# ==========================


def example_status():
    """Doctest input."""
    return read_file("tests/resources/artifacts/status.yaml")


def example_with_fake_name():
    """Doctest input."""
    return [{"application-name": "alertmanager_fake"}]


def example_with_scale_above_max():
    """Doctest input."""
    return [{"application-name": "alertmanager", "maximum": 0}]


def example_with_scale_below_min():
    """Doctest input."""
    return [{"application-name": "alertmanager", "minimum": 2}]
