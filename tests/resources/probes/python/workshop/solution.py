am = "alertmanager-k8s"
prom = "prometheus-k8s"


def status(juju_statuses):
    for status in juju_statuses.values():
        assert (
            status["applications"][am]["units"][f"{am}/0"]["juju-status"]["current"] == "idle"
        ), f"{am} is not in `idle` status."


def bundle(juju_bundles):
    for bundle in juju_bundles.values():
        assert "options" in bundle["applications"][am], f"There are no configs set for {am}."
        assert "config_file" in bundle["applications"][am]["options"], (
            f"{am} `config_file` option not set. The charm is using the default config."
        )


def show_unit(juju_show_units):
    for show_unit in juju_show_units.values():
        assert any(
            rel["endpoint"] == "alerting" and f"{prom}/0" in rel["related-units"]
            for rel in show_unit[f"{am}/0"]["relation-info"]
        ), f"{am} and {prom} are not related over the `alerting` endpoint"
