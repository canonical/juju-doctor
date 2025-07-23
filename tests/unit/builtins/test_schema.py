from pathlib import Path

import jsonschema
import pytest
import yaml

from juju_doctor.builtins import Builtins, build_unified_schema
from juju_doctor.probes import Probe


def test_load_schema():
    pass
    # GIVEN a schema file
    # WHEN the contents are read
    # THEN there are no errors


def test_combine_schemas():
    # GIVEN a Ruleset schema
    schema = build_unified_schema()
    # WHEN a Ruleset probe is loaded
    probe_path = Path("tests/resources/probes/ruleset/builtins.yaml")
    with open(probe_path, 'r') as file:
        yaml_data = yaml.safe_load(file)
    # THEN the schema is valid
    jsonschema.validate(yaml_data, schema)


@pytest.mark.parametrize("builtin_cls", Builtins.all())
def test_schema_validation(builtin_cls):
    # GIVEN a Ruleset probe with Builtin assertions
    probe_path = Path("tests/resources/probes/ruleset/builtins.yaml")
    with open(probe_path, 'r') as file:
        yaml_data = yaml.safe_load(file)
    # WHEN the relevant assertion for the Builtin is loaded
    builtin_assertion = yaml_data.get(builtin_cls.name())  # Adjust key as necessary
    # THEN the assertion matches the Builtin's schema
    builtin_obj = builtin_cls(Probe(Path(), Path()), builtin_assertion)
    assert builtin_obj.is_schema_valid()
