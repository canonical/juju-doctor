GRAFANA_AGENT = "grafana-agent"
COS_PROXY = "cos-proxy"
COS_AGENT = "cos-agent"

SUSPICIOUS_RELATIONS = [
    f"{GRAFANA_AGENT}:juju-info",
    f"{GRAFANA_AGENT}:cos-agent",
    f"{COS_PROXY}:prometheus-target",
]


def bundle(juju_bundles):
    """Bundle assertion.

    If cos-proxy is related to grafana-agent (cos-agent), then cos-proxy and grafana-agent
    shouldn't be related to the same "downstream-prometheus"
    """
    suspicious_rel = False
    proxy_endpoints = []
    agent_endpoints = []
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
            if proxy_related_to_agent and COS_AGENT in (endpoint_1, endpoint_2):
                suspicious_rel = True
                continue
            if COS_PROXY in (app_1, app_2):
                if app_1 == COS_PROXY:
                    proxy_endpoints.append(endpoint_1)
                else:
                    proxy_endpoints.append(
                        app_2,
                    )
            if GRAFANA_AGENT in (app_1, app_2):
                if app_1 == GRAFANA_AGENT:
                    agent_endpoints.append(endpoint_1)
                else:
                    agent_endpoints.append(endpoint_2)

        duplicate_endpoints = any(
            agent_endpoint in proxy_endpoints for agent_endpoint in agent_endpoints
        )
        assert not (suspicious_rel and duplicate_endpoints), (
            f"If {COS_PROXY} is related to {GRAFANA_AGENT} via the {COS_AGENT} endpoint, then "
            f"{COS_PROXY} and {GRAFANA_AGENT} shouldn't be related to the same "
            '"downstream-prometheus"'
        )
