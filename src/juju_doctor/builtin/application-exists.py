"""Application-exists verbatim builtin plugin.

The probe checks that the given application names (not charm names!) exist. This could be useful
when you need to check that a subset of a status (or bundle) is present, or when the scale of some
applications may vary after day-1.

To call this builtin within a RuleSet YAML file:

```yaml
name: RuleSet
probes:
    - name: Applications exist
      type: builtin/application-exists
      with:
        - application-name: loki
        - application-name: prometheus
          minimum: 1
          maximum: 3
```

Multiple assertions can be listed under the `with` key, adhering to the `ApplicationExists` schema.
"""

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from juju_doctor.artifacts import read_file


class ApplicationExists(BaseModel):
    """Schema for a builtin Application definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(alias="application-name")
    minimum: Optional[int] = Field(None, ge=0)
    maximum: Optional[int] = Field(None, ge=0)


def status(juju_statuses: Dict[str, Dict], **kwargs):
    """Status assertion for applications existing verbatim.

    >>> status({"0": example_status_missing_applications()}, **{"application-name": "foo"})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: There are no applications present in ...

    >>> status({"0": example_status()}, **example_with_fake_name())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: Unable to find the app (alertmanager_fake) in [...] ...

    >>> status({"0": example_status()}, **example_with_scale_above_max())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The scale (1) of alertmanager exceeds the allowable limit: 0 ...

    >>> status({"0": example_status()}, **example_with_scale_below_min())  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: The scale (1) of alertmanager is below the allowable limit: 2 ...
    """  # noqa: E501
    _app = ApplicationExists(**kwargs)
    for status_name, status in juju_statuses.items():
        if not (apps := status.get("applications")):
            raise Exception(f'There are no applications present in "{status_name}"')
        if not (found_app := apps.get(_app.name)):
            raise Exception(
                f"Unable to find the app ({_app.name}) in "
                f'[{", ".join(apps.keys())}] in "{status_name}"'
            )
        if _app.minimum is not None and found_app["scale"] < _app.minimum:
            raise Exception(
                f"The scale ({found_app['scale']}) of {_app.name} is below the allowable "
                f'limit: {_app.minimum} in "{status_name}"'
            )
        if _app.maximum is not None and found_app["scale"] > _app.maximum:
            raise Exception(
                f"The scale ({found_app['scale']}) of {_app.name} exceeds the allowable "
                f'limit: {_app.maximum} in "{status_name}"'
            )


# ==========================
# Helper functions
# ==========================


def example_status():
    """Doctest input."""
    return read_file("tests/resources/artifacts/status.yaml")


def example_status_missing_applications():
    """Doctest input.

    This deployment status is missing applications.
    """
    return {}


def example_with_fake_name():
    """Doctest input."""
    return {"application-name": "alertmanager_fake"}


def example_with_scale_above_max():
    """Doctest input."""
    return {"application-name": "alertmanager", "maximum": 0}


def example_with_scale_below_min():
    """Doctest input."""
    return {"application-name": "alertmanager", "minimum": 2}
