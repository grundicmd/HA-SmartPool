"""Parser tests that do not require a Home Assistant installation."""

from pathlib import Path
import sys
import types
import unittest


COMPONENT_PATH = (
    Path(__file__).parents[2] / "custom_components" / "zodiac_pool_robot"
)
package = types.ModuleType("zodiac_pool_robot")
package.__path__ = [str(COMPONENT_PATH)]
sys.modules["zodiac_pool_robot"] = package

aiohttp = types.ModuleType("aiohttp")
aiohttp.ClientError = type("ClientError", (Exception,), {})
aiohttp.ClientResponse = type("ClientResponse", (), {})
aiohttp.ClientSession = type("ClientSession", (), {})
aiohttp.WSMsgType = types.SimpleNamespace(
    TEXT="text", CLOSED="closed", CLOSE="close", ERROR="error"
)
sys.modules["aiohttp"] = aiohttp

homeassistant = types.ModuleType("homeassistant")
homeassistant.__path__ = []
homeassistant_const = types.ModuleType("homeassistant.const")
homeassistant_const.Platform = types.SimpleNamespace(
    VACUUM="vacuum", SENSOR="sensor", BINARY_SENSOR="binary_sensor"
)
sys.modules["homeassistant"] = homeassistant
sys.modules["homeassistant.const"] = homeassistant_const

from zodiac_pool_robot.api import ZodiacClient  # noqa: E402


class ZodiacParserTest(unittest.TestCase):
    """Verify normalization of both supported cloud protocols."""

    def test_cyclonext_shadow(self) -> None:
        device = {
            "name": "Pool Robot",
            "serial_number": "TEST123",
            "device_type": "cyclonext",
        }
        shadow = {
            "state": {
                "reported": {
                    "aws": {"status": "connected"},
                    "vr": "V31C12",
                    "eboxData": {"controlBoxSn": "BOX1"},
                    "equipment": {
                        "robot.1": {
                            "mode": 1,
                            "cycle": 3,
                            "canister": 0,
                            "errors": {"code": 0},
                            "vr": "V15E133",
                            "totRunTime": 6480,
                        }
                    },
                }
            }
        }

        result = ZodiacClient._normalize_cyclonext(device, shadow)

        self.assertTrue(result["running"])
        self.assertTrue(result["available"])
        self.assertEqual(result["total_runtime_hours"], 108.0)
        self.assertEqual(result["control_box_firmware"], "V31C12")
        self.assertEqual(result["robot_firmware"], "V15E133")

    def test_cyclonext_websocket_wrapper(self) -> None:
        payload = {
            "robot": {
                "state": {
                    "reported": {
                        "equipment": {
                            "robot.1": {"mode": 0, "errors": {"code": 10}}
                        }
                    }
                }
            }
        }
        device = {
            "name": "Pool Robot",
            "serial_number": "TEST123",
            "device_type": "cyclonext",
        }

        result = ZodiacClient._normalize_cyclonext(device, payload)

        self.assertFalse(result["running"])
        self.assertEqual(result["error"], "communication")

    def test_legacy_status(self) -> None:
        device = {
            "name": "Legacy Robot",
            "serial_number": "OLD123",
            "device_type": "i2d_robot",
        }

        result = ZodiacClient._normalize_i2d(
            device, "001102000BD18FD305E407021F43090F4570"
        )

        self.assertTrue(result["running"])
        self.assertEqual(result["error"], "none")
        self.assertIsInstance(result["total_runtime_hours"], float)


if __name__ == "__main__":
    unittest.main()
