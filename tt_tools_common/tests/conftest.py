import pytest
from pyluwen import detect_chips


@pytest.fixture()
def devices():
    """Return devices detected on the system."""
    return detect_chips()


@pytest.fixture()
def requires_hardware(devices):
    """Skip test if no hardware is detected."""
    if not devices:
        pytest.skip("No devices detected")
