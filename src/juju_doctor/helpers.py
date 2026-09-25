"""Importable functions for your custom probe.

These functions simplify the artifact (status, bundle, etc.) content parsing.

Add this line to your probe and you have access to all these functions:

`from juju_doctor.helpers import PICK_YOUR_FUNCTION`
"""
from typing import Dict, Optional

from jubilant import Status
from jubilant.statustypes import AppStatus


def get_apps_by_charm_name(status: Status, charm_name: str) -> Dict[str, AppStatus]:
    """Get the applications deployed with a charm name from a Juju status.

    Args:
        status: a :class:`jubilant.Status` artifact.
        charm_name: the name of the charm, e.g. ``grafana-k8s``.

    Returns:
        A mapping of application name to :class:`jubilant.statustypes.AppStatus`.
    """
    return {
        app_name: app
        for app_name, app in status.apps.items()
        if app.charm_name == charm_name
    }


def get_charm_name_by_app_name(status: Status, app_name: str) -> Optional[str]:
    """Get the (predictable) charm name from an application name."""
    app = status.apps.get(app_name)
    return app.charm_name if app else None
