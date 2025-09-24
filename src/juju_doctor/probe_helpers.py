"""Importable functions for your custom probe.

These functions simplify the artifact (status, bundle, etc.) content parsing.

Add this line to your probe and you have access to all these functions:

`from juju_doctor.probe_helpers import PICK_YOUR_FUNCTION`
"""
import contextlib
from typing import Dict, Optional


def get_apps_by_charm_name(status: dict, charm_name: str) -> Dict[str, Dict]:
    """Helper function to get the application object from a charm name."""
    return {
        app_name: context
        for app_name, context in status.get("applications", {}).items()
        if context["charm"] == charm_name
    }

def get_charm_name_by_app_name(status: dict, app_name: str) -> Optional[str]:
    """Helper function to get the (predictable) charm name from an application name."""
    with contextlib.suppress(KeyError):
        return status["applications"][app_name]["charm"]
    return None
