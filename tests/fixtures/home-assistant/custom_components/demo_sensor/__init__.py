"""Demo Home Assistant custom component fixture."""

from __future__ import annotations

DOMAIN = "demo_sensor"


async def async_setup(hass, config):
    """Set up the demo_sensor component."""
    return True
