"""Common fixtures for Energy Tracker tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return


@pytest.fixture
def mock_issue_registry(hass: HomeAssistant) -> Generator[MagicMock]:
    """Mock the issue registry."""
    with patch.object(ir, "async_create_issue") as mock_create:
        yield mock_create


@pytest.fixture
def api_token() -> str:
    """Return a test API token."""
    return "test-token-12345678"


@pytest.fixture
def device_id() -> str:
    """Return a valid UUID device ID."""
    return "12345678-1234-1234-1234-123456789abc"
