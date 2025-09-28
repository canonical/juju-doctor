"""Juju-doctor probe for redundant juju-info integrations to grafana-agent.

Having both juju-info and cos-agent integrations to grafana-agent duplicates the juju-info
telemetry from the related app.

This probe is a charm probe (not a solution probe) because applies to arbitrary deployments
including grafana-agent.

Context: As openstack incrementally transitioned from cos-proxy to grafana-agent, some deployments
ended up with hybrid, invalid topologies.
"""

from typing import Dict

import yaml

from juju_doctor.helpers import get_apps_by_charm_name, get_charm_name_by_app_name


def status(juju_statuses: Dict[str, Dict], **kwargs):
    """Status assertion for duplicate juju-info telemetry to grafana-agent.

    >>> status({"invalid-openstack-model": example_status_redundant_endpoints_agent_cos_proxy()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove either the "juju-info" or "cos-agent" integration between ...

    >>> status({"valid-model": example_status_valid()})
    """  # noqa: E501
    apps_related_to_agent = {}
    for status_name, status in juju_statuses.items():
        # Gather apps related to grafana-agent
        if not (agents := get_apps_by_charm_name(status, "grafana-agent")):
            continue
        for agent_name, agent in agents.items():
            for endpoint, relations in agent.get("relations", {}).items():
                if endpoint not in ("cos-agent", "juju-info"):
                    continue
                apps_related_to_agent.setdefault(endpoint, [])
                for rel in relations:
                    apps_related_to_agent[endpoint].append(
                        (agent_name, rel["related-application"])
                    )

        # Assert that either juju-info or cos-agent exists per app, not both
        for agent, related_app in apps_related_to_agent.get("cos-agent", {}):
            other_charm = get_charm_name_by_app_name(status, related_app)
            for _, _related_app in apps_related_to_agent.get("juju-info", {}):
                assert related_app != _related_app, (
                    f'Remove either the "juju-info" or "cos-agent" integration between "{agent}" '
                    f'(grafana-agent) and "{related_app}" ({other_charm}). Having both '
                    f'"juju-info" and "cos-agent" duplicates the "juju-info" telemetry to '
                    f'"{agent}" in "{status_name}".'
                )


# ==========================
# Helper functions
# ==========================


def example_status_redundant_endpoints_agent_cos_proxy():
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
