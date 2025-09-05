import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.results import AssertionResult
from juju_doctor.ruleset import BaseBuiltin, BuiltinArtifacts

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class RelationAssertion(BaseModel):
    """Schema for a builtin Relation definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    apps: List


class RelationBuiltin(BaseBuiltin):
    # TODO: Update this docstring for the other builtins as well
    """Takes a list of relation pairs and asserts that they all exist verbatim.

    applicable for: bundle

    For example,
    ```
    relations:
        - apps: [grafana:catalogue, catalogue:catalogue]
    ```
    """

    assertions: List[RelationAssertion]

    # TODO: Consider the case when we have multiple validate types: status, bundle, show_unit ...
    # TODO: Create an issue for this, but we need an abstraction layer to gather needed input from artifacts and fill a dataclass with it, then use that to assert against
    # FIXME Consider switching to status
    def validate(self, artifacts: Artifacts, probe_path: str) -> List[AssertionResult]:
        """Relation assertions against a bundle artifact.

        Check for the presence of specified relations in a given artifact by iterating through the
        relations of each bundle and verifying if the required relation pairs exist. If any
        relation is missing, append an AssertionResult indicating failure; otherwise, return a
        success result if all relations are found.

        NOTE: Any variables which refer to the relation assertion will be private, whereas
        variables which refer to the artifact will be public.
        E.g. _rel is a relation in the assertion from the RuleSet
        E.g. rel is a relation in the artifact
        """
        _rels = self.assertions
        if not _rels:
            return []

        BuiltinArtifacts.artifacts["bundle"] += 1
        if not artifacts.bundle:
            log.warning(f'No "bundle" artifact was provided for probe: {probe_path}.')
            return []

        results: List[AssertionResult] = []
        rels = [rel for bundle in artifacts.bundle.values() for rel in bundle["relations"]]
        for _rel in _rels:
            if len(_rel.apps) != 2:
                raise NotImplementedError(
                    "Only 2 apps are currently allowed per relation assertion."
                )
            if _rel.apps not in rels and [_rel.apps[1], _rel.apps[0]] not in rels:
                exception = Exception(f"Relation ({_rel.apps}) not found in {rels}")
                results.append(AssertionResult(None, False, exception))

        if not results:
            results.append(AssertionResult(None, True))

        return results
