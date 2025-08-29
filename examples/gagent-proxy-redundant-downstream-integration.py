# ruff: noqa: D103
# ruff: noqa: D100
# ruff: noqa: E501

import yaml


def status(juju_statuses):
    """Status assertion against duplicate telemetry.

    If cos-proxy is related to grafana-agent via the cos-agent endpoint, then cos-proxy and
    grafana-agent should not be related to the same "downstream-prometheus".

    >>> status({"failing-status": test_status()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: If "cos-proxy" is related to "grafana-agent" via the "cos-agent" endpoint, then "cos-proxy" and "grafana-agent" should not be related to the same "downstream-prometheus" in ...
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
        redundant_downstream = any(
            app in suspicious_endpoint_apps["send-remote-write"]
            for app in suspicious_endpoint_apps["downstream-prometheus-scrape"]
        )
        assert not (gagent_and_proxy_rel and redundant_downstream), (
            'If "cos-proxy" is related to "grafana-agent" via the "cos-agent" endpoint, then '
            '"cos-proxy" and "grafana-agent" should not be related to the same '
            f'"downstream-prometheus" in "{status_name}"'
        )


def test_status():
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
