import logging
from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, ConfigDict, Field
from rich.logging import RichHandler

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class RelationAssertion(BaseModel):
    """Schema for a builtin Relation definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    apps: List = Field(max_length=2)


def bundle(juju_bundles, **kwargs):
    """Bundle assertion for relations existing verbatim.

    >>> bundle({"invalid-app-name": example_bundle()}, custom=example_with_fake_name())  # doctest: +ELLIPSIS
    """
    assert kwargs["custom"], "No arguments were provided"

    _rels = [RelationAssertion(**rel) for rel in kwargs["custom"]]
    rels = [rel for bundle in juju_bundles.values() for rel in bundle["relations"]]
    for _rel in _rels:
        if _rel.apps not in rels and [_rel.apps[1], _rel.apps[0]] not in rels:
            raise Exception(f"Relation ({_rel.apps}) not found in {rels}")


# ==========================
# Helper methods
# ==========================


def example_bundle():
    with Path("tests/resources/artifacts/bundle.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def example_with_fake_name():
    # TODO: Fix this so that it loads from tests/resources/artifacts and uses the below YAML for the probe

    """Invalid topology of cos-proxy and grafana-agent.
    In this status, cos-proxy and grafana-agent are inter-related, while being
    related to the same prometheus.
    """
    return {"application-name": "alertmanager_fake"}

# TODO
# name: RuleSet - test builtin fails assertions
# probes:
#   - name: Builtin relation-exists
#     type: builtin/relation-exists
#     with:
#       - apps: [alertmanager_fake:alerting, loki:alertmanager]

# name: RuleSet - test builtin fails assertions
# probes:
#   - name: Builtin relation-exists
#     type: builtin/relation-exists
#     with:
#       - apps: [alertmanager:alerting, loki_fake:alertmanager]
