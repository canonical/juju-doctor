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
    AssertionError: If {COS_PROXY} is related to {GRAFANA_AGENT} via the cos-agent endpoint, then {COS_PROXY} and {GRAFANA_AGENT} shouldn't be related to the same "downstream-prometheus"

    >>> bundle({"bundle-missing-relations": test_no_relations()})
    Traceback (most recent call last):
    ...
    Exception: No relations found in bundle-missing-relations
    """
    suspicious_relations = []
    for bundle_name, bundle in juju_bundles.items():
        if not (relations := bundle.get("relations", {})):
            raise Exception(f"No relations found in {bundle_name}")
        for rel in relations:
            app_1 = rel[0].split(":")[0]
            app_2 = rel[1].split(":")[0]
            endpoint_1 = rel[0].split(":")[1]
            endpoint_2 = rel[1].split(":")[1]
            proxy_related_to_agent = (app_1, app_2) == (GRAFANA_AGENT, COS_PROXY) or (
                app_2,
                app_1,
            ) == (GRAFANA_AGENT, COS_PROXY)
            if proxy_related_to_agent:
                if "cos-agent" in (endpoint_1, endpoint_2):
                    suspicious_relations.append(rel)
                if "juju-info" in (endpoint_1, endpoint_2):
                    suspicious_relations.append(rel)
        assert len(suspicious_relations) < 2, (
            f"If {COS_PROXY} is related to {GRAFANA_AGENT} via the cos-agent endpoint, then "
            f"{COS_PROXY} and {GRAFANA_AGENT} shouldn't be related to the same "
            '"downstream-prometheus"'
        )


def test_bundle():
    return yaml.safe_load(f"""
relations:
- - {GRAFANA_AGENT}:cos-agent
  - {COS_PROXY}:cos-agent
- - {GRAFANA_AGENT}:juju-info
  - {COS_PROXY}:juju-info
""")


def test_no_relations():
    return yaml.safe_load("""
missing: relations key
""")
