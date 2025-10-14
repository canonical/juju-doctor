"""Mutually-exclusive-endpoints builtin plugin.

The probe checks that all apps of the given charm type are not related to another app over multiple
of the endpoints in the list. This could be useful when endpoints duplicate data, or they conflict
in any way. Applications which are exceptions to this assertion for the given charm type can be
added to the ignore list.

To call this builtin within a RuleSet YAML file:

```yaml
name: RuleSet
probes:
    - name: Avoid mutually exclusive endpoints
      type: builtin/mutually-exclusive-endpoints
      with:
        - charm-name: grafana-agent
          endpoints:
            - juju-info
            - cos_agent
          ignore_apps:
            - grafana-agent
```

Multiple assertions can be listed under the `with` key, adhering to the
`MutuallyExclusiveEndpoints` schema.
"""

from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

from juju_doctor.helpers import get_apps_by_charm_name, get_charm_name_by_app_name


class MutuallyExclusiveEndpoints(BaseModel):
    """Schema for a builtin Application definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    charm_name: str = Field(alias="charm-name")
    endpoints: List[str] = Field()
    ignore_apps: Optional[List[str]] = Field(None)


def status(juju_statuses: Dict[str, Dict], **kwargs):
    """Status assertion for applications existing verbatim.

    >>> status({"valid-model": example_status_valid()}, **example_args_without_ignore())

    >>> status({"0": example_status_multiple_endpoints_violating()}, **example_args_ignoring_all_apps())  # doctest: +ELLIPSIS

    >>> status({"0": example_status_missing_applications()}, **example_args_without_ignore())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: There are no applications present in ...

    >>> status({"0": example_status_single_endpoint_violating()}, **example_args_without_ignore())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove either the ... or ... integration between ga ... and foo ...

    >>> status({"0": example_status_multiple_endpoints_violating()}, **example_args_without_ignore())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove either the ... or ... integration between ga-one ... and foo ...

    >>> status({"0": example_status_multiple_endpoints_violating()}, **example_args_ignoring_app_one())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove either the ... or ... integration between ga-two ... and foo ...

    >>> status({"0": example_status_multiple_endpoints_violating()}, **example_args_ignoring_app_two())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove either the ... or ... integration between ga-one ... and foo ...
    """  # noqa: E501
    _input = MutuallyExclusiveEndpoints(**kwargs)
    for status_name, status in juju_statuses.items():
        endpoints_with_relations = {}
        if not status.get("applications"):
            raise AssertionError(f'There are no applications present in "{status_name}"')
        # Gather apps related to the requested charm
        if not (apps := get_apps_by_charm_name(status, _input.charm_name)):
            continue
        for app_name, app in apps.items():
            if _input.ignore_apps and app_name in _input.ignore_apps:
                continue
            for endpoint, relations in app.get("relations", {}).items():
                if endpoint not in (_input.endpoints):
                    continue
                endpoints_with_relations.setdefault(endpoint, [])
                for rel in relations:
                    endpoints_with_relations[endpoint].append(
                        (app_name, rel["related-application"])
                    )

        # Assert that either juju-info or cos-agent exists per app, not both
        for endpoint, pairs in endpoints_with_relations.items():
            for relation_pair in pairs:
                # Check against all other keys
                for other_endpoint, other_pairs in endpoints_with_relations.items():
                    if endpoint != other_endpoint and relation_pair in other_pairs:
                        app_1 = relation_pair[0]
                        app_2 = relation_pair[1]
                        charm_1 = get_charm_name_by_app_name(status, app_1)
                        charm_2 = get_charm_name_by_app_name(status, app_2)
                        raise AssertionError(
                            f"Remove either the {endpoint} or {other_endpoint} integration "
                            f"between {app_1} ({charm_1}) and {app_2} ({charm_2}) in "
                            f'"{status_name}".'
                        )


# ==========================
# Helper functions
# ==========================


def example_status_missing_applications():
    """Doctest input.

    This deployment status is missing applications.
    """
    return {}


def example_status_multiple_endpoints_violating():
    """Invalid topology of grafana-agent and another charm.

    In this status, grafana-agent and foo-charm are inter-related over both of the
    cos_agent and juju-info interfaces.
    """
    return yaml.safe_load("""
applications:
  ga-one:
    charm: grafana-agent
    relations:
      cos-agent:
      - related-application: foo
        interface: cos_agent
      juju-info:
      - related-application: foo
        interface: juju-info
  ga-two:
    charm: grafana-agent
    relations:
      cos-agent:
      - related-application: foo
        interface: cos_agent
      juju-info:
      - related-application: foo
        interface: juju-info
  foo:
    charm: foo-charm
    relations:
      foo-cos-agent:
      - related-application: ga-one
        interface: cos_agent
      - related-application: ga-two
        interface: cos_agent
      foo-juju-info:
      - related-application: ga-one
        interface: juju-info
      - related-application: ga-two
        interface: juju-info
""")


def example_status_single_endpoint_violating():
    """Invalid topology of grafana-agent and another charm.

    In this status, grafana-agent and foo-charm are inter-related over both of the
    cos_agent and juju-info interfaces.
    """
    return yaml.safe_load("""
applications:
  ga:
    charm: grafana-agent
    relations:
      cos-agent:
      - related-application: foo
        interface: cos_agent
      juju-info:
      - related-application: foo
        interface: juju-info
  foo:
    charm: foo-charm
    relations:
      foo-cos-agent:
      - related-application: ga
        interface: cos_agent
      foo-juju-info:
      - related-application: ga
        interface: juju-info
""")


def example_status_valid():
    """Valid topology of grafana-agent and other charms.

    In this status, grafana-agent is related to two different charms: foo and bar. For each
    relation, grafana-agent is related to only one of the cos_agent and juju-info interfaces.
    """
    return yaml.safe_load("""
applications:
  ga:
    charm: grafana-agent
    relations:
      cos-agent:
      - related-application: foo
        interface: cos_agent
      juju-info:
      - related-application: bar
        interface: juju-info
  foo:
    charm: foo-charm
    relations:
      foo-cos-agent:
      - related-application: ga
        interface: cos_agent
  bar:
    charm: bar-charm
    relations:
      bar-juju-info:
      - related-application: ga
        interface: juju-info
""")


def example_args_without_ignore():
    """Doctest input."""
    return {"charm-name": "grafana-agent", "endpoints": ["cos-agent", "juju-info"]}


def example_args_ignoring_app_one():
    """Doctest input."""
    return {
        "charm-name": "grafana-agent",
        "endpoints": ["cos-agent", "juju-info"],
        "ignore_apps": ["ga-one"],
    }


def example_args_ignoring_app_two():
    """Doctest input."""
    return {
        "charm-name": "grafana-agent",
        "endpoints": ["cos-agent", "juju-info"],
        "ignore_apps": ["ga-two"],
    }


def example_args_ignoring_all_apps():
    """Doctest input."""
    return {
        "charm-name": "grafana-agent",
        "endpoints": ["cos-agent", "juju-info"],
        "ignore_apps": ["ga-one", "ga-two"],
    }
