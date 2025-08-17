def status(juju_statuses, **args):
    assert args["application"] == "prometheus-k8s"
    assert args["path"] == "/api/v1/metrics"
