"""Juju-doctor probe for redundant juju-info integrations to grafana-agent.

Having both juju-info and cos-agent integrations to grafana-agent duplicates the juju-info
telemetry from the related app.

This probe is a charm probe (not a solution probe) because applies to arbitrary deployments
including grafana-agent.

Context: As openstack incrementally transitioned from cos-proxy to grafana-agent, some deployments
ended up with hybrid, invalid topologies.
"""

from typing import Optional

import yaml


def status(juju_statuses):
    """Status assertion for duplicate juju-info telemetry to grafana-agent.

    >>> status({"failing-status": test_invalid_status()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove either the "juju-info" or "cos-agent" integration between ...

    >>> status({"passing-status": test_valid_status()})
    """
    apps_related_to_gagent = {}
    for status_name, status in juju_statuses.items():
        # Gather apps related to grafana-agent
        agent = get_app_by_charm_name(status, "grafana-agent")
        for endpoint, relations in agent.get("relations", {}).items():
            if endpoint not in ("cos-agent", "juju-info"):
                continue
            apps_related_to_gagent.setdefault(endpoint, [])
            for rel in relations:
                apps_related_to_gagent[endpoint].append(rel["related-application"])

        # Assert that either juju-info or cos-agent exists per app, not both
        for related_app in apps_related_to_gagent.get("cos-agent", {}):
            ga_app = get_app_name_by_charm_name(status, "grafana-agent")
            other_charm = get_charm_name_by_app_name(status, related_app)
            assert related_app not in apps_related_to_gagent.get("juju-info", {}), (
                f'Remove either the "juju-info" or "cos-agent" integration between "{ga_app}" '
                f'(grafana-agent) and "{related_app}" ({other_charm}). Having both "juju-info" '
                f'and "cos-agent" duplicates the "juju-info" telemetry to "{ga_app}" in '
                f'"{status_name}".'
            )


# ==========================
# Helper methods
# ==========================


def get_app_name_by_charm_name(status: dict, charm_name: str) -> Optional[str]:
    """Helper function to get the (unpredictable) application name from a charm name."""
    if applications := status.get("applications", {}):
        for app, context in applications.items():
            if charm_name == context["charm"]:
                return app
    return None


def get_charm_name_by_app_name(status: dict, app_name: str) -> Optional[str]:
    """Helper function to get the (predictable) charm name from an application name."""
    if applications := status.get("applications", {}):
        if charm := applications.get(app_name, None):
            return charm["charm"]
    return None


def get_app_by_charm_name(status: dict, charm_name: str) -> Optional[str]:
    """Helper function to get the application object from a charm name."""
    if applications := status.get("applications", {}):
        for context in applications.values():
            if charm_name == context["charm"]:
                return context
    return None


def test_invalid_status():
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


def test_valid_status():
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
