"""Relation-exists verbatim builtin plugin."""

import logging
from dataclasses import dataclass
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field
from rich.logging import RichHandler

from juju_doctor.artifacts import read_file

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class RelationAssertion(BaseModel):
    """Schema for a builtin Relation definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    apps: List = Field(max_length=2)


def status(juju_statuses: Dict[str, Dict], **kwargs):
    """Status assertion for relation existing verbatim.

    >>> status({"0": example_status()}, with_args=example_with_fake_app_0())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The relation ['alertmanager_fake:alerting', 'loki:alertmanager'] was not found ...

    >>> status({"0": example_status()}, with_args=example_with_fake_app_1())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The relation ['alertmanager:alerting', 'loki_fake:alertmanager'] was not found ...

    >>> status({"0": example_status()}, with_args=example_with_fake_endpoint_0())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The relation ['alertmanager:alerting_fake', 'loki:alertmanager'] was not found ...

    >>> status({"0": example_status()}, with_args=example_with_fake_endpoint_1())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The relation ['alertmanager:alerting', 'loki:alertmanager_fake'] was not found ...
    """  # noqa: E501
    assert kwargs["with_args"], "No arguments were provided"

    _rels = [RelationAssertion(**_rel) for _rel in kwargs["with_args"]]
    for _rel in _rels:
        _rel_obj = Relation.from_rel_pair(_rel.apps)
        for status_name, status in juju_statuses.items():
            app_0 = status.get("applications", {}).get(_rel_obj.name_0, {})
            app_1 = status.get("applications", {}).get(_rel_obj.name_1, {})
            rel_0_to_1 = any(
                rel.get("related-application") == _rel_obj.name_1
                for rel in app_0.get("relations", {}).get(_rel_obj.endpoint_0, {})
            )
            rel_1_to_0 = any(
                rel.get("related-application") == _rel_obj.name_0
                for rel in app_1.get("relations", {}).get(_rel_obj.endpoint_1, {})
            )
            if not all((app_0, app_1, rel_0_to_1, rel_1_to_0)):
                raise Exception(f'The relation {_rel.apps} was not found in "{status_name}"')


def bundle(juju_bundles: Dict[str, Dict], **kwargs):
    """Bundle assertion for relations existing verbatim.

    >>> bundle({"0": example_bundle()}, with_args=example_with_fake_app_0())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The relation ['alertmanager_fake:alerting', 'loki:alertmanager'] was not found ...

    >>> bundle({"0": example_bundle()}, with_args=example_with_fake_app_1())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The relation ['alertmanager:alerting', 'loki_fake:alertmanager'] was not found ...

    >>> bundle({"0": example_bundle()}, with_args=example_with_fake_endpoint_0())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The relation ['alertmanager:alerting_fake', 'loki:alertmanager'] was not found ...

    >>> bundle({"0": example_bundle()}, with_args=example_with_fake_endpoint_1())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The relation ['alertmanager:alerting', 'loki:alertmanager_fake'] was not found ...
    """  # noqa: E501
    assert kwargs["with_args"], "No arguments were provided"
    _rels = [RelationAssertion(**_rel) for _rel in kwargs["with_args"]]
    for _rel in _rels:
        rel_found = False
        _rel_obj = Relation.from_rel_pair(_rel.apps)
        for bundle_name, bundle in juju_bundles.items():
            if not (rels := bundle.get("relations")):
                continue
            for rel in rels:
                rel_obj = Relation.from_rel_pair(rel)
                if rel_obj.equals(_rel_obj):
                    rel_found = True
            if not rel_found:
                raise Exception(f'The relation {_rel.apps} was not found in "{bundle_name}"')


# ==========================
# Helper classes
# ==========================


@dataclass
class Relation:
    """A relation between 2 Juju applications and their endpoints."""

    name_0: str
    endpoint_0: str
    name_1: str
    endpoint_1: str
    names: List[str]
    endpoints: List[str]

    @staticmethod
    def from_rel_pair(rel_pair: List[str]) -> "Relation":
        """Create a Relation instance from a relation pair."""
        return Relation(
            rel_pair[0].split(":")[0],
            rel_pair[0].split(":")[1],
            rel_pair[1].split(":")[0],
            rel_pair[1].split(":")[1],
            [rel_pair[0].split(":")[0], rel_pair[1].split(":")[0]],
            [rel_pair[0].split(":")[1], rel_pair[1].split(":")[1]],
        )

    def equals(self, other: "Relation") -> bool:
        """Check for equality between 2 Relation instances.

        This function checks for equality with and without reversed app polarity.
        """
        flipped_equality = (
            self.name_0 == other.name_1
            and self.endpoint_0 in other.endpoint_1
            and self.names == other.names[::-1]
            and self.endpoints == other.endpoints[::-1]
        )
        return self == other or flipped_equality


# ==========================
# Helper functions
# ==========================


def example_status():
    """Doctest input."""
    return read_file("tests/resources/artifacts/status.yaml")


def example_bundle():
    """Doctest input."""
    return read_file("tests/resources/artifacts/bundle.yaml")


def example_with_fake_app_0():
    """Doctest input."""
    return [{"apps": ["alertmanager_fake:alerting", "loki:alertmanager"]}]


def example_with_fake_app_1():
    """Doctest input."""
    return [{"apps": ["alertmanager:alerting", "loki_fake:alertmanager"]}]


def example_with_fake_endpoint_0():
    """Doctest input."""
    return [{"apps": ["alertmanager:alerting_fake", "loki:alertmanager"]}]


def example_with_fake_endpoint_1():
    """Doctest input."""
    return [{"apps": ["alertmanager:alerting", "loki:alertmanager_fake"]}]
