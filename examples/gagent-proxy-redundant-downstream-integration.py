"""Juju-doctor probe for redundant downstream telemetry integrations.

If cos-proxy is related to grafana-agent via the cos-agent endpoint, then cos-proxy and
grafana-agent should not be related to the same "downstream-prometheus".

This probe is a solution probe (not a charm probe) because it targets a cyclic relation between
three charms.

Context: As openstack incrementally transitioned from cos-proxy to grafana-agent, some deployments
ended up with hybrid, invalid topologies.
"""

from pathlib import Path
from typing import Dict

from jubilant import Status

from juju_doctor.artifacts import read_artifact_file
from juju_doctor.helpers import get_apps_by_charm_name

_FIXTURES = (
    Path(__file__).resolve().parent.parent / "tests" / "resources" / "artifacts" / "examples"
)


def status(juju_statuses: Dict[str, Status], **kwargs):
    """Status assertion for a cyclic relation between cos-proxy, grafana-agent, and prometheus.

    >>> status({"invalid-openstack-model": example_status("gagent-proxy-cyclic.yaml")})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove the relation between ... (cos-proxy) and prometheus. ...

    >>> status({"invalid-openstack-model": example_status("gagent-proxy-multiple.yaml")})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove the relation between "cp-2" (cos-proxy) and prometheus. ...

    >>> status({"valid-model": example_status("gagent-proxy-valid.yaml")})
    """  # noqa: E501
    agent_and_proxy_rel = False
    suspicious_endpoint_apps = {}
    for status_name, status in juju_statuses.items():
        applications = status.apps

        # Gather suspicious grafana-agent relations to prometheus
        if not (agents := get_apps_by_charm_name(status, "grafana-agent")):
            continue
        for agent_name, agent in agents.items():
            for endpoint, relations in agent.relations.items():
                for rel in relations:
                    if endpoint == "cos-agent":
                        if applications[rel.related_app].charm == "cos-proxy":
                            agent_and_proxy_rel = True
                    elif endpoint == "send-remote-write":
                        suspicious_endpoint_apps.setdefault(endpoint, [])
                        suspicious_endpoint_apps[endpoint].append(
                            (agent_name, rel.related_app)
                        )

        # Gather suspicious cos-proxy relations to prometheus
        if not (proxies := get_apps_by_charm_name(status, "cos-proxy")):
            continue
        for proxy_name, proxy in proxies.items():
            for endpoint, relations in proxy.relations.items():
                if endpoint != "downstream-prometheus-scrape":
                    continue
                for rel in relations:
                    suspicious_endpoint_apps.setdefault(endpoint, [])
                    suspicious_endpoint_apps[endpoint].append(
                        (proxy_name, rel.related_app)
                    )

        # Assert that the suspicious relations are not redundant
        for proxy, scrape_downstream in suspicious_endpoint_apps.get(
            "downstream-prometheus-scrape", {}
        ):
            for agent, prw_downstream in suspicious_endpoint_apps.get("send-remote-write", {}):
                assert not (agent_and_proxy_rel and scrape_downstream == prw_downstream), (
                    f'Remove the relation between "{proxy}" (cos-proxy) and prometheus. "{proxy}" '
                    f'(cos-proxy) and "{agent}" (grafana-agent) are inter-related (cos-agent) and '
                    f'related to the same prometheus in "{status_name}"'
                )


# ==========================
# Helper functions
# ==========================


def example_status(filename: str) -> Status:
    """Load a full ``juju status`` fixture used by the doctests."""
    return Status._from_dict(read_artifact_file(str(_FIXTURES / filename)))
