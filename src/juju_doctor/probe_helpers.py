from typing import Dict


# TODO: Remove
def get_apps_by_charm_name(status: dict, charm_name: str) -> Dict[str, Dict]:
    """Helper function to get the application object from a charm name."""
    return {
        app_name: context
        for app_name, context in status.get("applications", {}).items()
        if context["charm"] == charm_name
    }
