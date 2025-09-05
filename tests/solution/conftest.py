import pytest

from src.juju_doctor.probes import SUPPORTED_PROBE_FUNCTIONS
from src.juju_doctor.ruleset import BuiltinArtifacts


@pytest.fixture(autouse=True)
def reset_counter():
    # Reset the class variable before each test
    BuiltinArtifacts.artifacts = dict.fromkeys(SUPPORTED_PROBE_FUNCTIONS, 0)
    yield
