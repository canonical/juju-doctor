"""Universal assertions for deployments."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional

from juju_doctor.artifacts import Artifacts


class AssertionStatus(Enum):
    """Result of probe or builtin assertion."""

    PASS = "pass"
    FAIL = "fail"


class _Builtin(object):
    """Baseclass for builtin assertions.

    Each builtin validates its assertions against a schema and then the assertions against artifacts.

    # We need to create a schema and if its not used, Raise error
    # Parse the YAML for predefined top-level keys: applications, relations, offers, consumes, probes
    # We will have to aggregate builtins from potentially many rulesets,
    # aggregate_probes could consume this? It already does bc from_url makes it circular
    # When combining, make sure to not overwrite previous aggregations, UNIT TEST
    """

    # TODO How can I type hint here "Probe" without a circular dep
    def __init__(self, probe, schema_file: Path, assertion: dict = None):
        self.probe = probe
        self.schema_file = schema_file
        self.assertion = assertion

    def validate_schema(self):
        """Check that the provided schema is valid."""
        # TODO Use Pydantic? Use Crossplane? Use Otelbin schema approach?
        pass

    @property
    def schema(self):
        """Get the schema definition from file."""
        # TODO Consolidate the _read_files into fetcher.py?
        # json.loads(_read_file(self.schema_file))
        pass

    def validate(self, artifacts: Artifacts):
        """Validate assertions against artifacts or live model."""
        raise NotImplementedError


class Applications(_Builtin):
    # TODO Can I use kwargs or args here to make it cleaner?
    def __init__(self, probe, schema_file: Path, assertion: dict = None):
        super().__init__(probe, schema_file, assertion)

    def validate(self, artifacts: Artifacts) -> List["AssertionResult"]:
        results: List[AssertionResult] = []
        for app in self.assertion:
            # TODO Flatten this list comprehension like [a for a in b for b in something]
            bundle_apps = [bundle["applications"].keys() for bundle in artifacts.bundle.values()]
            if app["name"] not in bundle_apps:
                exception = f"{app['name']} was not found in bundle apps: {bundle_apps}"
                results.append(
                    AssertionResult(
                        self.probe,
                        func_name=f"builtin:{Builtins.APPLICATIONS.name.lower()}",
                        passed=False,
                        exception=exception,
                    )
                )
            app_scale = [bundle["applications"][app["name"]]["scale"] for bundle in artifacts.bundle.values()][0]
            if "minimum" in app and app_scale < app["minimum"]:
                exception = f'{app["name"]} scale is below the allowable limit: {app["minimum"]}'
                results.append(
                    AssertionResult(
                        self.probe,
                        func_name=f"builtin:{Builtins.APPLICATIONS.name.lower()}",
                        passed=False,
                        exception=exception,
                    )
                )
            if "maximum" in app and app_scale > app["maximum"]:
                exception = f'{app["name"]} scale exceeds the allowable limit: {app["maximum"]}'
                results.append(
                    AssertionResult(
                        self.probe,
                        func_name=f"builtin:{Builtins.APPLICATIONS.name.lower()}",
                        passed=False,
                        exception=exception,
                    )
                )
            # TODO Handle unit counts
        return results


class Relations(_Builtin):
    def __init__(self, probe, schema_file: Path, assertion: dict = None):
        super().__init__(probe, schema_file, assertion)

    def validate(self, artifacts: Artifacts):
        results: List[AssertionResult] = []
        for relation in self.assertion:
            # TODO Flatten this list comprehension like [a for a in b for b in something]
            bundle_relations = [bundle["relations"] for bundle in artifacts.bundle.values()]
            if [relation["provides"], relation["requires"]] not in bundle_relations:
                exception = Exception(
                    f'Relation ({[relation["provides"], relation["requires"]]}) not found in {bundle_relations}'
                )
                results.append(
                    AssertionResult(
                        self.probe,
                        func_name=f"builtin:{Builtins.RELATIONS.name.lower()}",
                        passed=False,
                        exception=exception,
                    )
                )
        return results


class Offers(_Builtin):
    def __init__(self, probe, schema_file: Path, assertion: dict = None):
        super().__init__(probe, schema_file, assertion)

    def validate(self, artifacts: Artifacts):
        results: List[AssertionResult] = []
        # TODO We cut the multi-doc containing offers in artifacts.py: https://github.com/canonical/juju-doctor/issues/10
        return results

class Consumes(_Builtin):
    def __init__(self, probe, schema_file: Path, assertion: dict = None):
        super().__init__(probe, schema_file, assertion)

    def validate(self, artifacts: Artifacts):
        # TODO The artifacts were not generated with a CMR, so we are missing SAAS
        return []


class Builtins(Enum):
    """Supported Probe file extensions."""

    APPLICATIONS = Applications
    RELATIONS = Relations
    OFFERS = Offers
    CONSUMES = Consumes


# TODO Try to combine this with ProbeAssertionResult
@dataclass
class AssertionResult:
    """A helper class to wrap results for a Probe's functions."""

    probe: Any  # TODO Fix type hinting due to circular module imports
    func_name: str
    passed: bool
    exception: Optional[BaseException] = None

    @property
    def status(self) -> str:
        """Result of the probe."""
        return AssertionStatus.PASS.value if self.passed else AssertionStatus.FAIL.value

    # TODO Type hinting SimpleNameSpace
    def get_text(self, output_fmt):
        """Probe results (formatted as Pretty-print) as a string."""
        exception_msg = None
        green = output_fmt.rich_map["green"]
        red = output_fmt.rich_map["red"]
        if self.passed:
            return f"{green} {self.probe.name}", exception_msg
        # If the probe failed
        exception_suffix = f"({self.probe.name}/{self.func_name}): {self.exception}"
        if output_fmt.format == "json":
            exception_msg = f"Exception {exception_suffix}"
        else:
            if output_fmt.verbose:
                exception_msg = f"[b]Exception[/b] {exception_suffix}"
        return SimpleNamespace(node_tag=f"{red} {self.probe.name}", exception_msg=exception_msg)
