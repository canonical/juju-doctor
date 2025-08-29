"""Juju-doctor probe for redundant downstream telemetry integrations.

If cos-proxy is related to grafana-agent via the cos-agent endpoint, then cos-proxy and
grafana-agent should not be related to the same "downstream-prometheus".

This probe is a solution probe (not a charm probe) because it targets a cyclic relation between
three charms.

Context: As openstack incrementally transitioned from cos-proxy to grafana-agent, some deployments
ended up with hybrid, invalid topologies.
"""

from typing import Optional

import yaml


def status(juju_statuses):
    """Status assertion for a cyclic relation between cos-proxy, grafana-agent, and prometheus.

    >>> status({"failing-status": test_status()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove the relation between ... (cos-proxy) and prometheus. ...
    """
    gagent_and_proxy_rel = False
    suspicious_endpoint_apps = {}
    for status_name, status in juju_statuses.items():
        applications = status.get("applications", {})
        for app in applications.values():
            if app["charm"] == "grafana-agent":
                for endpoint, relations in app.get("relations", {}).items():
                    for rel in relations:
                        if endpoint == "cos-agent":
                            if (
                                applications.get(rel["related-application"])["charm"]
                                == "cos-proxy"
                            ):
                                gagent_and_proxy_rel = True
                        elif endpoint == "send-remote-write":
                            suspicious_endpoint_apps.setdefault(endpoint, [])
                            suspicious_endpoint_apps[endpoint].append(rel["related-application"])
            elif app["charm"] == "cos-proxy":
                for endpoint, relations in app.get("relations", {}).items():
                    if endpoint != "downstream-prometheus-scrape":
                        continue
                    for rel in relations:
                        suspicious_endpoint_apps.setdefault(endpoint, [])
                        suspicious_endpoint_apps[endpoint].append(rel["related-application"])
        for app in suspicious_endpoint_apps["downstream-prometheus-scrape"]:
            redundant_downstream = app in suspicious_endpoint_apps["send-remote-write"]
            ga_app = get_app_by_charm_name(status, "grafana-agent")
            cp_app = get_app_by_charm_name(status, "cos-proxy")
            assert not (gagent_and_proxy_rel and redundant_downstream), (
                f'Remove the relation between "{cp_app}" (cos-proxy) and prometheus. "{cp_app}" '
                f'(cos-proxy) and "{ga_app}" (grafana-agent) are inter-related (cos-agent) and '
                f'related to the same prometheus in "{status_name}"'
            )


def get_app_by_charm_name(status: dict, charm_name: str) -> Optional[str]:
    """Helper function to get the (unpredictable) application name from a charm name."""
    if applications := status.get("applications", {}):
        for app, context in applications.items():
            if charm_name == context["charm"]:
                return app
    return None


def get_charm_by_app_name(status: dict, app_name: str) -> Optional[str]:
    """Helper function to get the (predictable) charm name from an application name."""
    if applications := status.get("applications", {}):
        if charm := applications.get(app_name, None):
            return charm["charm"]
    return None


def test_status():
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
