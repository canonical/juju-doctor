"""Universal assertions for deployments."""

import contextlib
import importlib
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, get_type_hints

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import ValidationError
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts
from juju_doctor.results import SUPPORTED_PROBE_FUNCTIONS, AssertionResult

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

GenericRuleset = TypeVar("GenericRuleset")  # TODO: Make this make sense
GenericAssertion = TypeVar('GenericRuleset', bound=BaseModel)

BUILTINS_DIR = "src/juju_doctor/builtins"


class ProbeAssertion(BaseModel):
    """Schema for a builtin Probe definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    url: str
    with_: Optional[Dict[str, Any]] = Field(None, alias="with")


# TODO: I don't like this, but it works, maybe move to BaseBuiltin?
class BuiltinArtifacts:
    """Track the artifacts used by builtin assertions."""

    artifacts: Dict = dict.fromkeys(SUPPORTED_PROBE_FUNCTIONS, 0)

    @classmethod
    def reset_count(cls):
        cls.artifacts = dict.fromkeys(SUPPORTED_PROBE_FUNCTIONS, 0)


class BaseBuiltin(ABC, BaseModel):
    """Base class for all Pydantic models of builtins and their validations."""

    assertions: List[GenericAssertion]

    @abstractmethod
    def validate(self, artifacts: Artifacts, probe_path: str) -> List[AssertionResult]:
        """Method to validate artifacts.

        Must be implemented by subclasses.
        """
        pass


class RuleSetModel(BaseModel):
    """A pydantic model of a declarative YAML RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str
    probes: Optional[List[ProbeAssertion]] = None
    builtins: Dict[str, BaseBuiltin] = None

    @model_validator(mode="after")
    # FIXME: In Python 3.11+ we can replace "RuleSetModel[GenericRuleset]" with typing.Self
    def at_least_one_assertion_is_defined(self) -> "RuleSetModel[GenericRuleset]":
        """Check if at least one of the optional fields is present."""
        if not any((getattr(self, "probes"), getattr(self, "builtins"))):
            raise ValueError("At least one probe or builtin must be provided.")
        return self

    @classmethod
    def get_builtin_plugins(cls, directory: str) -> Dict[str, BaseBuiltin]:
        """Aggregate builtins in src.juju_doctor.builtins.

        To be considered, the Builtin must:
            1. be a subclass of BaseBuiltin.
            2. implement all abstract methods.
            3. implement a custom assertions model (the default is BaseModel).
        """
        builtin_definitions = {}

        for filename in os.listdir(directory):
            if not filename.endswith(".py"):
                continue

            module_name = filename[:-3]
            module = importlib.import_module(f"juju_doctor.builtins.{module_name}")

            # Iterate over all attributes in the module for a valid Builtin class
            subclasses = [
                getattr(module, attr)
                for attr in dir(module)
                if isinstance(getattr(module, attr), type)
                and issubclass(getattr(module, attr), BaseBuiltin)
                and getattr(module, attr).__name__ != BaseBuiltin.__name__
            ]
            for subclass in subclasses:
                with contextlib.suppress(TypeError):
                    with contextlib.suppress(ValidationError):
                        # Raises TypeError if requirements in the BaseBuiltin ABC are not met
                        # Always Raises ValidationError
                        subclass()
                    _type = get_type_hints(subclass).get("assertions").__args__[0]
                    if _type != BaseModel and issubclass(subclass, BaseModel):
                        builtin_definitions[module_name] = subclass

        return builtin_definitions

    @classmethod
    def get_builtin_models(cls, contents: Dict) -> Dict[str, BaseBuiltin]:
        """Return the pydantic models of each builtin plugin which exists in contents."""
        builtins = {}
        builtin_plugins = RuleSetModel.get_builtin_plugins(BUILTINS_DIR)
        for name, builtin_plugin in builtin_plugins.items():
            if builtin_content := contents.get("builtins", {}).get(name):
                builtins[name] = builtin_plugin(**{"assertions": builtin_content}, Counter())

        return builtins

    @classmethod
    def input_without_builtins(cls, contents: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out the "builtins" key-value pair in contents."""
        return {k: v for k, v in contents.items() if k != "builtins"}
