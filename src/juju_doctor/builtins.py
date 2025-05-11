"""Universal assertions for deployments."""
from enum import Enum
from pathlib import Path

from juju_doctor.artifacts import Artifacts


class _Builtin(object):
    """Baseclass for builtin assertions.

    Each builtin validates its assertions against a schema and then the assertions against artifacts.

    # We need to create a schema and if its not used, Raise error
    # Parse the YAML for predefined top-level keys: applications, relations, offers, consumes, probes
    # We will have to aggregate builtins from potentially many rulesets,
    # aggregate_probes could consume this? It already does bc from_url makes it circular
    # When combining, make sure to not overwrite previous aggregations, UNIT TEST
    """
    def __init__(self, schema_file: Path, assertion: dict = None):
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
    def __init__(self, schema_file: Path, assertion: dict = None):
        super().__init__(schema_file, assertion)

    def validate(self, artifacts: Artifacts):
        for app in self.assertion:
            # TODO Flatten this
            bundle_apps = [bundle["applications"].keys() for bundle in artifacts.bundle.values()]
            assert app["name"] in bundle_apps
            # TODO Handle unit counts

class Relations(_Builtin):
    def __init__(self, schema_file: Path, assertion: dict = None):
        super().__init__(schema_file, assertion)

    def validate(self, artifacts: Artifacts):
        for app in self.assertion:
            pass

class Offers(_Builtin):
    def __init__(self, schema_file: Path, assertion: dict = None):
        super().__init__(schema_file, assertion)

    def validate(self, artifacts: Artifacts):
        for app in self.assertion:
            pass

class Consumes(_Builtin):
    def __init__(self, schema_file: Path, assertion: dict = None):
        super().__init__(schema_file, assertion)

    def validate(self, artifacts: Artifacts):
        for app in self.assertion:
            pass


class Builtins(Enum):
    """Supported Probe file extensions."""

    APPLICATIONS = Applications
    RELATIONS = Relations
    OFFERS = Offers
    CONSUMES = Consumes
