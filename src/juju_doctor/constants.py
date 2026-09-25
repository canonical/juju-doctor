"""Constants used in the juju-doctor app."""
from typing import Final

ROOT_NODE_ID: Final = "root"
ROOT_NODE_TAG: Final = "Results"
BUILTIN_DIR: Final = "src/juju_doctor/builtin"
SUPPORTED_PROBE_FUNCTIONS: Final = frozenset(
    {"status", "bundle", "show_unit", "show_model", "model_dump"}
)
