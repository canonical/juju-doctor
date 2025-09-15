"""Helper module for displaying the result in a tree."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from rich.logging import RichHandler

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)


@dataclass
class OutputFormat:
    """Output formatting for the application."""

    verbose: bool
    format: str = ""
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
    exception: Optional[BaseException] = None

    @property
    def status(self) -> str:
        """Result of the probe."""
        return AssertionStatus.PASS.value if self.passed else AssertionStatus.FAIL.value
