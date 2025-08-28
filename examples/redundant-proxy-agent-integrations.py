# ruff: noqa: D103
# ruff: noqa: D100
# ruff: noqa: E501

import yaml

GRAFANA_AGENT = "grafana-agent"
COS_PROXY = "cos-proxy"


def bundle(juju_bundles):
    f"""Bundle assertion against duplicate telemetry.

    >>> bundle({"failing-bundle": test_bundle()})
    Traceback (most recent call last):
    ...
    AssertionError: {COS_PROXY} and {GRAFANA_AGENT} should not be related to both juju-info and cos-agent.

    >>> bundle({"bundle-missing-relations": test_no_relations()})
    Traceback (most recent call last):
    ...
    Exception: No relations found in bundle-missing-relations

    >>> bundle({"bundle-missing-saas": test_no_saas()})
    Traceback (most recent call last):
    ...
    Exception: No saas found in bundle-missing-saas
    """
    suspicious_rel = False
    proxy_endpoints = []
    agent_endpoints = []
    for bundle_name, bundle in juju_bundles.items():
        if not (relations := bundle.get("relations", {})):
            raise Exception(f"No relations found in {bundle_name}")
        if not (bundle.get("saas", {})):
            raise Exception(f"No saas found in {bundle_name}")
        for rel in relations:
            app_1 = rel[0].split(":")[0]
            app_2 = rel[1].split(":")[0]
            endpoint_1 = rel[0].split(":")[1]
            endpoint_2 = rel[1].split(":")[1]
            proxy_related_to_agent = (app_1, app_2) == (GRAFANA_AGENT, COS_PROXY) or (
                app_2,
                app_1,
            ) == (GRAFANA_AGENT, COS_PROXY)
            if proxy_related_to_agent and "cos-agent" in (endpoint_1, endpoint_2):
                suspicious_rel = True
                continue
            if COS_PROXY in (app_1, app_2):
                if app_1 == COS_PROXY:
                    endpoint = (endpoint_1, app_2)
                else:
                    endpoint = (endpoint_2, app_1)
                if endpoint[0] == "downstream-prometheus-scrape":
                    proxy_endpoints.append(endpoint)
            if GRAFANA_AGENT in (app_1, app_2):
                if app_1 == GRAFANA_AGENT:
                    endpoint = (endpoint_1, app_2)
                else:
                    endpoint = (endpoint_2, app_1)
                if endpoint[0] == "send-remote-write":
                    agent_endpoints.append(endpoint)

        suspicious_proxy_rels = [pe[1] for pe in proxy_endpoints]
        duplicate_endpoints = any(ae[1] in suspicious_proxy_rels for ae in agent_endpoints)
        assert not (suspicious_rel and duplicate_endpoints), (
            f"{COS_PROXY} and {GRAFANA_AGENT} should not be related to both "
            "juju-info and cos-agent."
        )


def test_bundle():
    return yaml.safe_load(f"""
saas:
  prometheus:
    url: microk8s:admin/cos.prometheus
relations:
- - {GRAFANA_AGENT}:cos-agent
  - {COS_PROXY}:cos-agent
- - {COS_PROXY}:downstream-prometheus-scrape
  - prometheus:metrics-endpoint
- - {GRAFANA_AGENT}:send-remote-write
  - prometheus:receive-remote-write
""")


def test_no_relations():
    return yaml.safe_load("""
saas:
  prometheus:
    url: microk8s:admin/cos.prometheus
""")


def test_no_saas():
    return yaml.safe_load(f"""
relations:
- - {GRAFANA_AGENT}:cos-agent
  - {COS_PROXY}:cos-agent
""")
