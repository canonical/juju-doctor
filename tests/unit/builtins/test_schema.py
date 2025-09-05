import os
from pathlib import Path

import pytest
import yaml
from pydantic_core import ValidationError

from juju_doctor.ruleset import RuleSetModel


def test_rulesets_in_resources_dir():
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
            # TODO: I will likely need to update this path to "tests/resources/probes/ruleset/invalid/**/invalid-input-fields.py"
            if "tests/resources/probes/ruleset/invalid" in os.path.dirname(file_path):
                if Path(Path(file_path).name).stem == "circular":
                    continue
                with pytest.raises(ValidationError):
                    RuleSetModel(
                        **RuleSetModel.input_without_builtins(contents),
                        builtins=RuleSetModel.get_builtin_models(contents),
                    )
            else:
                # THEN no ValidationError is raised
                RuleSetModel(
                    **RuleSetModel.input_without_builtins(contents),
                    builtins=RuleSetModel.get_builtin_models(contents),
                )


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
