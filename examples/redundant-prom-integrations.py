AGENT = "grafana-agent"
COS_PROXY = "cos-proxy"

SUSPICIOUS_RELATIONS = [
    f"{AGENT}:juju-info",
    f"{AGENT}:cos-agent",
    f"{COS_PROXY}:prometheus-target",
]


def status(juju_statuses):
    for status_name, status in juju_statuses.items():
        status_relations = [
            f"{k}:{r}"
            for k, v in status.get("applications", {}).items()
            for r in v["relations"]
        ]
        found_relations = [name for name in SUSPICIOUS_RELATIONS if name in status_relations]
        message = (
            f"Duplicate telemetry will be sent to Prometheus due to the redundant relations: "
            f"{found_relations} found in {status_name}."
        )
        assert len(found_relations) < 2, message
