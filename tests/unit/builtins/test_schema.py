from pathlib import Path

import jsonschema
import pytest
import yaml
from jsonschema.exceptions import ValidationError

from juju_doctor.builtins import Probes, SupportedBuiltins, build_unified_schema
from juju_doctor.probes import Probe


def test_incorrect_schema_top_level_keys():
    # GIVEN a Ruleset schema
    schema = build_unified_schema()
    # WHEN a Ruleset with non-schema top-level keys is loaded
    incorrect_key = "foo"
    yaml_content = f"""
    name: Incorrect Ruleset
    {incorrect_key}: bar
    """
    yaml_data = yaml.safe_load(yaml_content)
    # THEN it fails validation
    with pytest.raises(ValidationError) as error:
        jsonschema.validate(yaml_data, schema)

    assert f"'{incorrect_key}' was unexpected" in str(error.value)


def test_combine_schemas():
    # GIVEN a Ruleset schema
    schema = build_unified_schema()
    # WHEN a Ruleset probe is loaded
    probe_path = Path("tests/resources/probes/ruleset/builtins.yaml")
    with open(probe_path, 'r') as file:
        yaml_data = yaml.safe_load(file)
    # THEN the schema is valid
    jsonschema.validate(yaml_data, schema)


@pytest.mark.parametrize("builtin_cls", SupportedBuiltins.all(filter=[Probes]))
def test_schema_validation_builtins(builtin_cls):
    # GIVEN a Ruleset probe with Builtin assertions
    probe_path = Path("tests/resources/probes/ruleset/builtins.yaml")
    with open(probe_path, 'r') as file:
        yaml_data = yaml.safe_load(file)
    # WHEN the relevant assertion for the Builtin is loaded
    builtin_assertion = yaml_data.get(builtin_cls.name())  # Adjust key as necessary
    # THEN the assertion matches the Builtin's schema
    builtin_obj = builtin_cls(Probe(Path(), Path()), builtin_assertion)
    builtin_obj.validate_schema()
    assert builtin_obj.valid_schema
