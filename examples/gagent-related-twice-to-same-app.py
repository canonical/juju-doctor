# ruff: noqa: D103
# ruff: noqa: D100
# ruff: noqa: F524
# ruff: noqa: E501

import yaml


def status(juju_statuses):
    """Status assertion against duplicate telemetry.

    grafana-agent should not be related to any app over both juju-info and cos-agent.

    >>> status({"failing-status": test_invalid_status()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: "grafana-agent" should not be related to any app over both "juju-info" and "cos-agent" in ...

    >>> status({"passing-status": test_valid_status()})
    """
    apps_related_to_gagent = {}
    for status_name, status in juju_statuses.items():
        for app in status.get("applications", {}).values():
            if app["charm"] != "grafana-agent":
                continue
            for endpoint, relations in app.get("relations", {}).items():
                if endpoint not in ("cos-agent", "juju-info"):
                    continue
                apps_related_to_gagent.setdefault(endpoint, [])
                for rel in relations:
                    apps_related_to_gagent[endpoint].append(rel["related-application"])
        assert not any(
            r in apps_related_to_gagent["juju-info"] for r in apps_related_to_gagent["cos-agent"]
        ), (
            '"grafana-agent" should not be related to any app over both '
            f'"juju-info" and "cos-agent" in "{status_name}"'
        )


def test_invalid_status():
    return yaml.safe_load("""
applications:
  ga:
    charm: grafana-agent
    relations:
      cos-agent:
      - related-application: foo
        interface: cos_agent
      juju-info:
      - related-application: foo
        interface: juju-info
  foo:
    charm: foo-charm
    relations:
      foo-cos-agent:
      - related-application: ga
        interface: cos_agent
      foo-juju-info:
      - related-application: ga
        interface: juju-info
""")


def test_valid_status():
    return yaml.safe_load("""
applications:
  ga:
    charm: grafana-agent
    relations:
      cos-agent:
      - related-application: foo
        interface: cos_agent
      juju-info:
      - related-application: bar
        interface: juju-info
  foo:
    charm: foo-charm
    relations:
      foo-cos-agent:
      - related-application: ga
        interface: cos_agent
  bar:
    charm: bar-charm
    relations:
      bar-juju-info:
      - related-application: ga
        interface: juju-info
""")
