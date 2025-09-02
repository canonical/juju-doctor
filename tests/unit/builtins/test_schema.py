import os

import pytest
import yaml
from pydantic_core import ValidationError

from juju_doctor.builtins import RuleSetModel


def test_rulesets_in_resources_dir():
    # GIVEN a directory of ruleset YAML files
    for root, _, files in os.walk("tests/resources/probes/ruleset"):
        for file in files:
            if file.endswith(".yaml") or file.endswith(".yml"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    data = yaml.safe_load(f)
                    # WHEN the contents are loaded into a Pydantic RuleSetModel
                    if root == "tests/resources/probes/ruleset/invalid/schema":
                        with pytest.raises(ValidationError):
                            RuleSetModel(**data)
                    else:
                        RuleSetModel(**data)
                    # THEN no ValidationError is raised


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
