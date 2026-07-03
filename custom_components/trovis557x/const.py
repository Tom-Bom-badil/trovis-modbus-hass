"""Constants for the Trovis 557x integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "trovis557x"
MODBUS_CONNECTION_DOMAIN: Final = "modbus_connection"

CONF_CONNECTION_ENTRY_ID: Final = "connection_entry_id"
CONF_UNIT_ID: Final = "unit_id"
CONF_SLUG: Final = "slug"
CONF_ACCESS_CODE: Final = "access_code"
CONF_MODEL: Final = "model"
CONF_DETECTED_SENSORS: Final = "detected_sensors"

DEFAULT_UNIT_ID: Final = 246
DEFAULT_SLUG: Final = "trovis"

# A heating controller is not an express train.
SCAN_INTERVAL: Final = timedelta(seconds=60)
