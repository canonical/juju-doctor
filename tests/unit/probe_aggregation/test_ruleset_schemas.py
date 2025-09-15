import os
from pathlib import Path

import pytest
import yaml
from pydantic_core import ValidationError

from juju_doctor.probes import RuleSetModel


def test_rulesets_have_valid_schemas_in_resources_dir():
    # GIVEN a directory of ruleset YAML files
    yaml_files = [
        os.path.join(root, file)
        for root, _, files in os.walk("tests/resources/probes/ruleset")
        for file in files
        if file.endswith((".yaml", ".yml"))
    ]

    for file_path in yaml_files:
        with open(file_path, "r") as f:
            contents = yaml.safe_load(f)
            # WHEN the contents are loaded into a Pydantic RuleSetModel
            invalid_ruleset_dir = "tests/resources/probes/ruleset/invalid"
            raises_exception = Path(Path(file_path).name).stem.split("-")[0] == "raises"
            if invalid_ruleset_dir in os.path.dirname(file_path) and raises_exception:
                with pytest.raises(ValidationError):
                    RuleSetModel(**contents)
            else:
                # THEN no ValidationError is raised
                RuleSetModel(**contents)


def test_incorrect_schema_top_level_keys():
    # GIVEN a Ruleset with non-schema top-level keys is loaded
    incorrect_key = "foo"
    yaml_content = f"""
    name: Incorrect Ruleset
    {incorrect_key}: bar
    """
    yaml_data = yaml.safe_load(yaml_content)
    # THEN it fails validation
    with pytest.raises(ValidationError) as error:
        RuleSetModel(**yaml_data)

    assert incorrect_key in str(error.value)
    assert "Extra inputs are not permitted" in str(error.value)
