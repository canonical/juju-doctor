import os
from pathlib import Path
from typing import List
from unittest import mock

from pydantic import BaseModel

from juju_doctor.artifacts import Artifacts
from juju_doctor.results import AssertionResult
from juju_doctor.ruleset import BUILTINS_DIR, BaseBuiltin, RuleSetModel


def test_builtin_not_subclass():
    # GIVEN a Builtin class which is not a subclass of BaseBuiltin
    class InvalidBuiltin:
        pass

    mock_module = mock.Mock()
    # WHEN the module contains said class
    mock_module.IncorrectBuiltin = InvalidBuiltin
    with (
        mock.patch("os.listdir", return_value=["incorrect_builtin.py"]),
        mock.patch("importlib.import_module", return_value=mock_module),
    ):
        # THEN the module is not respected
        assert not RuleSetModel.get_builtin_plugins("dummy_directory")


def test_builtin_is_subclass():
    # GIVEN a Builtin class missing abstractmethod definitions
    class InvalidBuiltin(BaseBuiltin):
        pass

    mock_module = mock.Mock()
    # WHEN the module contains said class
    mock_module.IncorrectBuiltin = InvalidBuiltin
    with (
        mock.patch("os.listdir", return_value=["incorrect_builtin.py"]),
        mock.patch("importlib.import_module", return_value=mock_module),
    ):
        # THEN the module is not respected
        assert not RuleSetModel.get_builtin_plugins("dummy_directory")


def test_builtin_valid_interface():
    # GIVEN a custom pydantic model
    class CustomModel(BaseModel):
        foo: bool

    # AND a Builtin class with a valid interface
    class ValidBuiltin(BaseBuiltin):
        assertions: List[CustomModel]

        def validate(self, artifacts: Artifacts) -> List[AssertionResult]:
            pass

    mock_module = mock.Mock()
    # WHEN the module contains said class
    mock_module.ValidBuiltin = ValidBuiltin
    with (
        mock.patch("os.listdir", return_value=["valid_builtin.py"]),
        mock.patch("importlib.import_module", return_value=mock_module),
    ):
        # THEN the module is respected
        assert "valid_builtin" in RuleSetModel.get_builtin_plugins("dummy_directory")


def test_builtin_plugins():
    # GIVEN the juju-doctor builtin plugins directory
    plugin_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(BUILTINS_DIR)
        for file in files
        if file.endswith(".py")
    ]
    # WHEN their interfaces are validated
    builtin_plugins = RuleSetModel.get_builtin_plugins(BUILTINS_DIR)
    # THEN all plugins are valid
    all(Path(Path(file_path).name).stem in builtin_plugins for file_path in plugin_files)
