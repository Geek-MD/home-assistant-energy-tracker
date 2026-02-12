"""Common fixtures for Energy Tracker tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return


@pytest.fixture
def api_token() -> str:
    """Return a test API token."""
    return "test-token-12345678"


@pytest.fixture
def device_id() -> str:
    """Return a valid UUID device ID."""
    return "12345678-1234-1234-1234-123456789abc"


@pytest.fixture(autouse=True)
def mock_forward_entry_setups():
    """Mock async_forward_entry_setups to prevent actual platform setup."""
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        return_value=AsyncMock(),
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_unload_platforms():
    """Mock async_unload_platforms to prevent actual platform unload."""
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ) as mock:
        yield mock
