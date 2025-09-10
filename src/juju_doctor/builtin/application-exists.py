import logging
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from rich.logging import RichHandler

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class ApplicationAssertion(BaseModel):
    """Schema for a builtin Application definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(alias="application-name")
    minimum: Optional[int] = Field(None, ge=0)
    maximum: Optional[int] = Field(None, ge=0)


def status(juju_statuses, **kwargs):
    """Status assertion for applications existing verbatim.

    >>> status({"invalid-openstack-model": example_status_cyclic_agent_cos_proxy()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove the relation between ... (cos-proxy) and prometheus. ...
    >>> status({"invalid-openstack-model": example_multiple_proxies()})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: Remove the relation between "cp-2" (cos-proxy) and prometheus. ...
    >>> status({"valid-model": example_status_valid()})
    """
    assert kwargs["custom"], "No arguments were provided"

    _apps = [ApplicationAssertion(**app) for app in kwargs["custom"]]
    _app_names = [app.name for app in _apps]
    for status_name, status in juju_statuses.items():
        if not all(_app in status["applications"].keys() for _app in _app_names):
            raise Exception(f'Not all apps: {_app_names} were found in "{status_name}"')
        apps_relevant = {
            name: app for name, app in status["applications"].items() if name in _app_names
        }
        for name, app in apps_relevant.items():
            for _app in _apps:
                if _app.name != name:
                    continue
                if _app.minimum is not None and app["scale"] < _app.minimum:
                    raise Exception(
                        f"{name} scale ({app['scale']}) is below the allowable limit: "
                        f"{_app.minimum}"
                    )
                if _app.maximum is not None and app["scale"] > _app.maximum:
                    raise Exception(
                        f"{name} scale ({app['scale']}) exceeds the allowable limit: "
                        f"{_app.maximum}"
                    )


# TODO:
# name: RuleSet - test builtin fails assertions
# probes:
#   - name: Builtin application-exists
#     type: builtin/application-exists
#     with:
#       - application-name: alertmanager_fake

# name: RuleSet - test builtin fails assertions
# probes:
#   - name: Builtin application-exists
#     type: builtin/application-exists
#     with:
#       - application-name: alertmanager
#         maximum: 0

# name: RuleSet - test builtin fails assertions
# probes:
#   - name: Builtin application-exists
#     type: builtin/application-exists
#     with:
#       - application-name: alertmanager
#         minimum: 2
