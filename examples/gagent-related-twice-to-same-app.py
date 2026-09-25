"""Juju-doctor probe for redundant juju-info integrations to grafana-agent.

Having both juju-info and cos-agent integrations to grafana-agent duplicates the juju-info
telemetry from the related app.

This probe is a charm probe (not a solution probe) because applies to arbitrary deployments
including grafana-agent.

Context: As openstack incrementally transitioned from cos-proxy to grafana-agent, some deployments
ended up with hybrid, invalid topologies.
"""

from pathlib import Path
from typing import Dict

from jubilant import Status

from juju_doctor.artifacts import read_artifact_file
from juju_doctor.helpers import get_apps_by_charm_name, get_charm_name_by_app_name

_FIXTURES = (
    Path(__file__).resolve().parent.parent / "tests" / "resources" / "artifacts" / "examples"
)


def status(juju_statuses: Dict[str, Status], **kwargs):
    """Status assertion for duplicate juju-info telemetry to grafana-agent.

    >>> status({"invalid-openstack-model": example_status("gagent-redundant.yaml")})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove either the "juju-info" or "cos-agent" integration between ...

    >>> status({"valid-model": example_status("gagent-valid.yaml")})
    """  # noqa: E501
    apps_related_to_agent = {}
    for status_name, status in juju_statuses.items():
        # Gather apps related to grafana-agent
        if not (agents := get_apps_by_charm_name(status, "grafana-agent")):
            continue
        for agent_name, agent in agents.items():
            for endpoint, relations in agent.relations.items():
                if endpoint not in ("cos-agent", "juju-info"):
                    continue
                apps_related_to_agent.setdefault(endpoint, [])
                for rel in relations:
                    apps_related_to_agent[endpoint].append(
                        (agent_name, rel.related_app)
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


def example_status(filename: str) -> Status:
    """Load a full ``juju status`` fixture used by the doctests."""
    return Status._from_dict(read_artifact_file(str(_FIXTURES / filename)))
