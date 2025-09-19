"""Helper module for displaying the result in a tree."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from rich.logging import RichHandler

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


class CheckFormat(str, Enum):
    """Options for formatting the output of the check command."""

    tree = "tree"
    json = "json"


class SchemaType(str, Enum):
    """Options for which schema type to output."""

    ruleset = "ruleset"
    builtins = "builtins"


@dataclass
class FormatTracker:
    """Output formatting for the application."""

    verbose: bool
    format: CheckFormat
    rich_map = {
        "green": "🟢",
        "red": "🔴",
        "check_mark": "✔️",
        "multiply": "✖️",
    }


class AssertionStatus(Enum):
    """Status string for an assertion."""

    PASS = "pass"
    FAIL = "fail"


@dataclass
class AssertionResult:
    """The result of a Probe function."""

    func_name: Optional[str]
    passed: bool
    exceptions: List[Optional[BaseException]] = field(default_factory=list)

    @property
    def status(self) -> str:
        """Result of the probe."""
        return AssertionStatus.PASS.value if self.passed else AssertionStatus.FAIL.value
