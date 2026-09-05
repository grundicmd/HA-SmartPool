"""Constants for the Zodiac Pool Robot integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "zodiac_pool_robot"
PLATFORMS = [Platform.VACUUM, Platform.SENSOR, Platform.BINARY_SENSOR]
UPDATE_INTERVAL = timedelta(seconds=30)

DEVICE_TYPE_CYCLONEXT = "cyclonext"
DEVICE_TYPE_I2D_ROBOT = "i2d_robot"
SUPPORTED_DEVICE_TYPES = {DEVICE_TYPE_CYCLONEXT, DEVICE_TYPE_I2D_ROBOT}

API_KEY = "EOOEMOW4YR6QNB07"
IAQUALINK_API_BASE = "https://r-api.iaqualink.net"
ZODIAC_API_BASE = "https://prod.zodiac-io.com"
ZODIAC_WS_URL = "wss://prod-socket.zodiac-io.com/devices"
ZODIAC_WS_ORIGIN = "https://prod-socket.zodiac-io.com"
USER_AGENT = "iAqualink/578 CFNetwork/1335.0.3 Darwin/21.6.0"
