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

from juju_doctor.helpers import get_apps_by_charm_name


def status(juju_statuses: Dict[str, Dict], **kwargs):
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
        applications = status.get("applications", {})

        # Gather suspicious grafana-agent relations to prometheus
        if not (agents := get_apps_by_charm_name(status, "grafana-agent")):
            continue
        for agent_name, agent in agents.items():
            for endpoint, relations in agent.get("relations", {}).items():
                for rel in relations:
                    if endpoint == "cos-agent":
                        if applications.get(rel["related-application"])["charm"] == "cos-proxy":
                            agent_and_proxy_rel = True
                    elif endpoint == "send-remote-write":
                        suspicious_endpoint_apps.setdefault(endpoint, [])
                        suspicious_endpoint_apps[endpoint].append(
                            (agent_name, rel["related-application"])
                        )

        # Gather suspicious cos-proxy relations to prometheus
        if not (proxies := get_apps_by_charm_name(status, "cos-proxy")):
            continue
        for proxy_name, proxy in proxies.items():
            for endpoint, relations in proxy.get("relations", {}).items():
                if endpoint != "downstream-prometheus-scrape":
                    continue
                for rel in relations:
                    suspicious_endpoint_apps.setdefault(endpoint, [])
                    suspicious_endpoint_apps[endpoint].append(
                        (proxy_name, rel["related-application"])
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


def example_status_cyclic_agent_cos_proxy():
    """Invalid topology of cos-proxy and grafana-agent.

    In this status, cos-proxy and grafana-agent are inter-related, while being
    related to the same prometheus.
    """
    return yaml.safe_load("""
applications:
  ga:
    charm: grafana-agent
    relations:
      cos-agent:
      - related-application: cp
        interface: cos_agent
      send-remote-write:
      - related-application: prom
        interface: prometheus_remote_write
  cp:
    charm: cos-proxy
    relations:
      cos-agent:
      - related-application: ga
        interface: cos_agent
      downstream-prometheus-scrape:
      - related-application: prom
        interface: prometheus_scrape
  prom:
    charm: prometheus-k8s
    relations:
      receive-remote-write:
      - related-application: ga
        interface: prometheus_remote_write
      metrics-endpoint:
      - related-application: cp
        interface: prometheus_scrape
""")


def example_multiple_proxies():
    """Invalid topology of cos-proxy and grafana-agent.

    In this status, grafana-agent is related to 2 different cos-proxy apps. Only "cp-2" is related
    to the same prometheus as grafana-agent.
    """
    return yaml.safe_load("""
applications:
  ga:
    charm: grafana-agent
    relations:
      cos-agent:
      - related-application: cp-1
        interface: cos_agent
      - related-application: cp-2
        interface: cos_agent
      send-remote-write:
      - related-application: prom
        interface: prometheus_remote_write
  cp-1:
    charm: cos-proxy
    relations:
      cos-agent:
      - related-application: ga
        interface: cos_agent
  cp-2:
    charm: cos-proxy
    relations:
      cos-agent:
      - related-application: ga
        interface: cos_agent
      downstream-prometheus-scrape:
      - related-application: prom
        interface: prometheus_scrape
  prom:
    charm: prometheus-k8s
    relations:
      receive-remote-write:
      - related-application: ga
        interface: prometheus_remote_write
      metrics-endpoint:
      - related-application: cp-2
        interface: prometheus_scrape
""")


def example_status_valid():
    """Valid topology of cos-proxy and grafana-agent.

    In this status, cos-proxy and grafana-agent are inter-related, and
    not related to the same prometheus.
    """
    return yaml.safe_load("""
applications:
  ga:
    charm: grafana-agent
    relations:
      cos-agent:
      - related-application: cp
        interface: cos_agent
      send-remote-write:
      - related-application: foo
        interface: prometheus_remote_write
  cp:
    charm: cos-proxy
    relations:
      cos-agent:
      - related-application: ga
        interface: cos_agent
      downstream-prometheus-scrape:
      - related-application: prom
        interface: prometheus_scrape
  prom:
    charm: prometheus-k8s
    relations:
      receive-remote-write:
      - related-application: ga
        interface: prometheus_remote_write
      metrics-endpoint:
      - related-application: cp
        interface: prometheus_scrape
  foo:
    charm: foo-k8s
    relations:
      receive-remote-write:
      - related-application: ga
        interface: prometheus_remote_write
""")
