import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.results import AssertionResult
from juju_doctor.ruleset import BaseBuiltin, BuiltinArtifacts

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class ApplicationAssertion(BaseModel):
    """Schema for a builtin Application definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str
    minimum: Optional[int] = Field(None, ge=0)
    maximum: Optional[int] = Field(None, ge=0)
    # TODO: "with" is redundant because BaseModel is allowing customizations
    # loosely allowing kwargs is bad because the source code would not support all possibilities
    # Simme intended "with" to work for scriptlet and http probes
    # with_: Optional[Dict[str, Any]] = Field(None, alias="with")


class ApplicationBuiltin(BaseBuiltin):
    assertions: List[ApplicationAssertion]

    def validate(self, artifacts: Artifacts, probe_path: str) -> List[AssertionResult]:
        """Takes a list of applications and assert that they all exist verbatim.

        applicable for: status

        Example:
            applications:
              - name: alertmanager

        Returns an AssertionResult. If the application (and its context) is not found, the
        AssertionResult indicates failure; otherwise, the AssertionResult indicates success.

        NOTE: Any variables which refer to the application assertion will be private, whereas
        variables which refer to the artifact will be public.
        E.g. _app is an application in the assertion from the RuleSet
        E.g. app is an application in the artifact
        """
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
