import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.results import AssertionResult
from juju_doctor.ruleset import BaseBuiltin, BuiltinArtifacts

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class MutuallyExlcusiveEndpointsAssertion(BaseModel):
    """Schema for a builtin Application definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    charm_name: str = Field(alias="charm-name")
    endpoints: List[str]
    # ignore: List[str]
    with_: Optional[Dict[str, Any]] = Field(None, alias="with")


class MutuallyExlcusiveEndpointBuiltin(BaseBuiltin):
    assertions: List[MutuallyExlcusiveEndpointsAssertion]

    def validate(self, artifacts: Artifacts, probe_path: str) -> List[AssertionResult]:
        """If charm-name is supplied, check that each app (of its type) in applications is not related to all of the endpoints in the endpoints list.
        
        Check that all the apps are related to the given charm type over at most 1 or the specified endpoints of the given charm."""
        _apps = self.assertions
        if not _apps:
            return []

        BuiltinArtifacts.artifacts["status"] += 1
        if not artifacts.status:
            log.warning(f'No "status" artifact was provided for probe: {probe_path}.')
            return []

        _app_names = [app.name for app in _apps]
        results: List[AssertionResult] = []

        for status_name, status in artifacts.status.items():
            if not all(_app in status["applications"].keys() for _app in _app_names):
                exception = Exception(f'Not all apps: {_app_names} were found in "{status_name}"')
                results.append(AssertionResult(None, False, exception))
            apps_relevant = {
                name: app for name, app in status["applications"].items() if name in _app_names
            }
            for name, app in apps_relevant.items():
                for _app in _apps:
                    if _app.name != name:
                        continue
                    if _app.minimum is not None and app["scale"] < _app.minimum:
                        exception = Exception(
                            f"{name} scale ({app['scale']}) is below the allowable limit: {_app.minimum}"
                        )
                        results.append(AssertionResult(None, False, exception))
                    if _app.maximum is not None and app["scale"] > _app.maximum:
                        exception = Exception(
                            f"{name} scale ({app['scale']}) exceeds the allowable limit: {_app.maximum}"
                        )
                        results.append(AssertionResult(None, False, exception))

        if not results:
            results.append(AssertionResult(None, True))

        return results
