"""Applications matching a risk level builtin plugin.

The probe checks that all applications match the risk level. This could be useful when you need to
check that a deployment is on stable in a production environment, or when the channel of some
applications may vary after day-1.

To call this builtin within a RuleSet YAML file:

```yaml
name: RuleSet
probes:
    - name: Builtin risk is stable
      type: builtin/risk
      with:
        - type: stable
```

Multiple assertions can be listed under the `with` key, adhering to the `Risk` schema.
"""

from typing import Dict

from pydantic import BaseModel, ConfigDict, Field


# TODO: This is kind of an anti-pattern since the user can supply a list of assertions in the
# builtin which will never work because the deployment can only be ALL stable or ALL beta but not both
class Risk(BaseModel):
    """Schema for a builtin Application definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    risk_type: str = Field(alias="type")


def status(juju_statuses: Dict[str, Dict], **kwargs):
    """Status assertion for applications matching a risk type."""
    _input = Risk(**kwargs)
    for status_name, status in juju_statuses.items():
        not_risk = [
            app_name
            for app_name, app_data in status["applications"].items()
            if not app_data["charm-channel"].endswith(_input.risk_type)
        ]
        if not_risk:
            raise Exception(f"The following apps are not from {_input.risk_type}: {not_risk}")


# ==========================
# Helper functions
# ==========================
