# TODO
# 1. Ignore the COS charms
# 2. We do not have polarity
# 3. Ask the Juju team why we have no polarity in status. How can I deduce this?


GRAFANA_AGENT = "grafana-agent"
COS_PROXY = "cos-proxy"

SUSPICIOUS_RELATIONS = [
    f"{GRAFANA_AGENT}:juju-info",
    f"{GRAFANA_AGENT}:cos-agent",
    f"{COS_PROXY}:prometheus-target",
]


def status(juju_statuses):
    """Status assertion.

    Iterate over all (vm) charms and emit an error if the same charm is related to more of one
    of the above. The polarity of the relation matters, because grafana agent may have
    more than one incoming relations, and that's correct.
    """
    suspicious_relations = []
    for status_name, status in juju_statuses.items():
        if not (applications := status.get("applications", {})):
            raise Exception(f"No applications found in {status_name}")
        for app_name, app in applications.items():
            for rel_name, rel_type in app["relations"].items():
                for rel in rel_type:
                    rel_app = rel["related-application"]
                    if rel_app not in [GRAFANA_AGENT, COS_PROXY]:
                        continue
                    if rel["interface"] not in ["cos_agent", "http", "juju_info"]:
                        continue
                    suspicious_relations.append(f'{app_name}:{rel_name}->{rel_app}:{rel["interface"]}')
        message = (
            f"Duplicate telemetry will be sent to Prometheus due to the redundant relations: "
            f"{suspicious_relations} found in {status_name}."
        )
        assert len(suspicious_relations) < 2, message


def bundle(juju_bundles):
    """Bundle assertion.

    Iterate over all (vm) charms and emit an error if the same charm is related to more of one
    of the above. The polarity of the relation matters, because grafana agent may have
    more than one incoming relations, and that's correct.
    """
    tracking = {}
    for bundle_name, bundle in juju_bundles.items():
        if not (relations := bundle.get("relations", {})):
            raise Exception(f"No relations found in {bundle_name}")
        for rel in relations:
            charm_1 = rel[0].split(":")[0]
            charm_2 = rel[1].split(":")[0]
            if not any(charm in (charm_1, charm_2) for charm in (COS_PROXY, GRAFANA_AGENT)):
                continue
            if any(suspicious in (rel[0], rel[1]) for suspicious in SUSPICIOUS_RELATIONS):
                tracking[""]
            # Relations are always alphabetically ordered
