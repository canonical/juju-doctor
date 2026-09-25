"""Juju-doctor probe for redundant downstream telemetry integrations.

If cos-proxy is related to grafana-agent via the cos-agent endpoint, then cos-proxy and
grafana-agent should not be related to the same "downstream-prometheus".

This probe is a solution probe (not a charm probe) because it targets a cyclic relation between
three charms.

Context: As openstack incrementally transitioned from cos-proxy to grafana-agent, some deployments
ended up with hybrid, invalid topologies.
"""

from typing import Dict

import yaml
from jubilant import Status

from juju_doctor.helpers import get_apps_by_charm_name


def status(juju_statuses: Dict[str, Status], **kwargs):
    """Status assertion for a cyclic relation between cos-proxy, grafana-agent, and prometheus.

    >>> status({"invalid-openstack-model": example_status_cyclic_agent_cos_proxy()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove the relation between ... (cos-proxy) and prometheus. ...

    >>> status({"invalid-openstack-model": example_multiple_proxies()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove the relation between "cp-2" (cos-proxy) and prometheus. ...

    >>> status({"valid-model": example_status_valid()})
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


def example_status_cyclic_agent_cos_proxy() -> Status:
    """Invalid topology of cos-proxy and grafana-agent.

    In this status, cos-proxy and grafana-agent are inter-related, while being
    related to the same prometheus.
    """
    return Status._from_dict(
        yaml.safe_load("""
model: {name: example, type: caas, controller: example, cloud: kubernetes, version: 4.0.0}
machines: {}
applications:
  ga:
    charm: grafana-agent
    charm-origin: charmhub
    charm-name: grafana-agent
    charm-rev: 1
    exposed: false
    relations:
      cos-agent: [{related-application: cp}]
      send-remote-write: [{related-application: prom}]
  cp:
    charm: cos-proxy
    charm-origin: charmhub
    charm-name: cos-proxy
    charm-rev: 1
    exposed: false
    relations:
      cos-agent: [{related-application: ga}]
      downstream-prometheus-scrape: [{related-application: prom}]
  prom:
    charm: prometheus-k8s
    charm-origin: charmhub
    charm-name: prometheus-k8s
    charm-rev: 1
    exposed: false
    relations:
      receive-remote-write: [{related-application: ga}]
      metrics-endpoint: [{related-application: cp}]
""")
    )


def example_multiple_proxies() -> Status:
    """Invalid topology of cos-proxy and grafana-agent.

    In this status, grafana-agent is related to 2 different cos-proxy apps. Only "cp-2" is related
    to the same prometheus as grafana-agent.
    """
    return Status._from_dict(
        yaml.safe_load("""
model: {name: example, type: caas, controller: example, cloud: kubernetes, version: 4.0.0}
machines: {}
applications:
  ga:
    charm: grafana-agent
    charm-origin: charmhub
    charm-name: grafana-agent
    charm-rev: 1
    exposed: false
    relations:
      cos-agent: [{related-application: cp-1}, {related-application: cp-2}]
      send-remote-write: [{related-application: prom}]
  cp-1:
    charm: cos-proxy
    charm-origin: charmhub
    charm-name: cos-proxy
    charm-rev: 1
    exposed: false
    relations:
      cos-agent: [{related-application: ga}]
  cp-2:
    charm: cos-proxy
    charm-origin: charmhub
    charm-name: cos-proxy
    charm-rev: 1
    exposed: false
    relations:
      cos-agent: [{related-application: ga}]
      downstream-prometheus-scrape: [{related-application: prom}]
  prom:
    charm: prometheus-k8s
    charm-origin: charmhub
    charm-name: prometheus-k8s
    charm-rev: 1
    exposed: false
    relations:
      receive-remote-write: [{related-application: ga}]
      metrics-endpoint: [{related-application: cp-2}]
""")
    )


def example_status_valid() -> Status:
    """Valid topology of cos-proxy and grafana-agent.

    In this status, cos-proxy and grafana-agent are inter-related, and
    not related to the same prometheus.
    """
    return Status._from_dict(
        yaml.safe_load("""
model: {name: example, type: caas, controller: example, cloud: kubernetes, version: 4.0.0}
machines: {}
applications:
  ga:
    charm: grafana-agent
    charm-origin: charmhub
    charm-name: grafana-agent
    charm-rev: 1
    exposed: false
    relations:
      cos-agent: [{related-application: cp}]
      send-remote-write: [{related-application: foo}]
  cp:
    charm: cos-proxy
    charm-origin: charmhub
    charm-name: cos-proxy
    charm-rev: 1
    exposed: false
    relations:
      cos-agent: [{related-application: ga}]
      downstream-prometheus-scrape: [{related-application: prom}]
  prom:
    charm: prometheus-k8s
    charm-origin: charmhub
    charm-name: prometheus-k8s
    charm-rev: 1
    exposed: false
    relations:
      receive-remote-write: [{related-application: ga}]
      metrics-endpoint: [{related-application: cp}]
  foo:
    charm: foo-k8s
    charm-origin: charmhub
    charm-name: foo-k8s
    charm-rev: 1
    exposed: false
    relations:
      receive-remote-write: [{related-application: ga}]
""")
    )
