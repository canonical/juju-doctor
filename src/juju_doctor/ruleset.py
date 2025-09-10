"""Universal assertions for deployments."""

import logging
from typing import Any, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from rich.logging import RichHandler

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

RulesetType = TypeVar("RulesetType")
BaseModelType = TypeVar("BaseModelType", bound=BaseModel)

BUILTIN_DIR = "src/juju_doctor/builtin"


class ProbeAssertion(BaseModel):
    """Schema for a builtin Probe definition in a RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    url: Optional[str] = Field(None)
    with_: Optional[Any] = Field(None, alias="with")


class RuleSetModel(BaseModel):
    """A pydantic model of a declarative YAML RuleSet."""

    model_config = ConfigDict(extra="forbid")

    name: str
    probes: List[ProbeAssertion] = Field(...)
