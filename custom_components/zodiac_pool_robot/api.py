"""Cloud API client for Zodiac and iAquaLink pool robots."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
import secrets
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientError, ClientResponse, ClientSession, WSMsgType

from .const import (
    API_KEY,
    DEVICE_TYPE_CYCLONEXT,
    DEVICE_TYPE_I2D_ROBOT,
    IAQUALINK_API_BASE,
    USER_AGENT,
    ZODIAC_API_BASE,
    ZODIAC_WS_ORIGIN,
    ZODIAC_WS_URL,
)

_LOGGER = logging.getLogger(__name__)


class ZodiacApiError(Exception):
    """Base Zodiac API error."""


class ZodiacAuthError(ZodiacApiError):
    """Authentication failed."""


class ZodiacConnectionError(ZodiacApiError):
    """Cloud connection failed."""


class ZodiacClient:
    """Client for Zodiac's current and legacy robot cloud APIs."""

    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self.authentication_token = ""
        self.id_token = ""
        self.user_id = ""

    async def async_login(self) -> None:
        """Authenticate and store cloud tokens."""
        payload = {"apiKey": API_KEY, "email": self._email, "password": self._password}
        try:
            async with asyncio.timeout(20):
                async with self._session.post(
                    f"{ZODIAC_API_BASE}/users/v1/login", json=payload
                ) as response:
                    data = await self._read_json(response)
                    status = response.status
        except (TimeoutError, ClientError) as err:
            raise ZodiacConnectionError("Unable to reach Zodiac cloud") from err

        if status in (400, 401, 403, 422) or not isinstance(data, Mapping):
            raise ZodiacAuthError("Invalid iAquaLink credentials")
        if status < 200 or status >= 300:
            raise ZodiacApiError(f"Login failed with HTTP {status}")

        oauth = data.get("userPoolOAuth") or {}
        self.authentication_token = str(data.get("authentication_token") or "")
        self.id_token = str(oauth.get("IdToken") or "")
        self.user_id = str(data.get("id") or "")
        if not self.authentication_token or not self.id_token or not self.user_id:
            raise ZodiacAuthError("Login response did not include required tokens")

    async def async_list_devices(self) -> list[dict[str, Any]]:
        """Return devices assigned to the iAquaLink account."""
        await self._ensure_login()
        params = {
            "api_key": API_KEY,
            "authentication_token": self.authentication_token,
            "user_id": self.user_id,
        }
        data = await self._request_json(
            "GET", f"{IAQUALINK_API_BASE}/devices.json", params=params, legacy=True
        )
        if not isinstance(data, list):
            raise ZodiacApiError("Unexpected device list response")
        return [device for device in data if isinstance(device, dict)]

    async def async_get_status(self, device: Mapping[str, Any]) -> dict[str, Any]:
        """Return normalized status for a supported robot."""
        device_id = str(device["serial_number"])
        device_type = str(device.get("device_type") or "")
        if device_type == DEVICE_TYPE_CYCLONEXT:
            try:
                shadow = await self._request_json(
                    "GET", f"{ZODIAC_API_BASE}/devices/v2/{device_id}/shadow"
                )
                return self._normalize_cyclonext(device, shadow)
            except ZodiacApiError:
                payload = await self._async_ws_subscribe(device_id)
                return self._normalize_cyclonext(device, payload)
        if device_type == DEVICE_TYPE_I2D_ROBOT:
            result = await self._async_legacy_command(device_id, "0A11")
            return self._normalize_i2d(device, result)
        raise ZodiacApiError(f"Unsupported device type: {device_type}")

    async def async_set_running(
        self, device: Mapping[str, Any], running: bool
    ) -> None:
        """Start or stop a robot."""
        device_id = str(device["serial_number"])
        device_type = str(device.get("device_type") or "")
        if device_type == DEVICE_TYPE_CYCLONEXT:
            await self._async_ws_set_mode(device_id, 1 if running else 0)
            return
        if device_type == DEVICE_TYPE_I2D_ROBOT:
            await self._async_legacy_command(device_id, "0A1240" if running else "0A1210")
            return
        raise ZodiacApiError(f"Unsupported device type: {device_type}")

    async def _ensure_login(self) -> None:
        if not self.id_token:
            await self.async_login()

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        json: Mapping[str, Any] | None = None,
        legacy: bool = False,
        retry_auth: bool = True,
    ) -> Any:
        await self._ensure_login()
        headers = {"Accept": "application/json"}
        if not legacy:
            headers.update({"Authorization": self.id_token, "User-Agent": USER_AGENT})
        try:
            async with asyncio.timeout(20):
                async with self._session.request(
                    method, url, params=params, json=json, headers=headers
                ) as response:
                    data = await self._read_json(response)
                    status = response.status
        except (TimeoutError, ClientError) as err:
            raise ZodiacConnectionError("Unable to reach Zodiac cloud") from err

        if status in (401, 403) and retry_auth:
            await self.async_login()
            return await self._request_json(
                method,
                url,
                params=params,
                json=json,
                legacy=legacy,
                retry_auth=False,
            )
        if status < 200 or status >= 300:
            raise ZodiacApiError(f"Zodiac API returned HTTP {status}")
        return data

    async def _async_legacy_command(self, device_id: str, request_code: str) -> str:
        params_value = urlencode({"request": request_code, "timeout": "800"})
        params = {
            "api_key": API_KEY,
            "authentication_token": self.authentication_token,
            "user_id": self.user_id,
            "command": "/command",
            "params": params_value,
        }
        data = await self._request_json(
            "POST",
            f"{IAQUALINK_API_BASE}/devices/{device_id}/execute_read_command.json",
            params=params,
            legacy=True,
        )
        try:
            return str(data["command"]["response"])
        except (KeyError, TypeError) as err:
            raise ZodiacApiError("Unexpected legacy command response") from err

    async def _async_ws_subscribe(self, device_id: str) -> dict[str, Any]:
        await self._ensure_login()
        try:
            user_id = int(float(self.user_id))
        except ValueError as err:
            raise ZodiacApiError("Invalid Zodiac user ID") from err

        payload = {
            "version": 1,
            "action": "subscribe",
            "namespace": "authorization",
            "service": "Authorization",
            "target": device_id,
            "payload": {"userId": user_id},
        }
        try:
            async with asyncio.timeout(20):
                async with self._session.ws_connect(
                    ZODIAC_WS_URL,
                    headers={"Authorization": self.id_token},
                    origin=ZODIAC_WS_ORIGIN,
                ) as websocket:
                    await websocket.send_json(payload)
                    return await self._wait_for_ws_payload(
                        websocket, device_id, service="Authorization"
                    )
        except (TimeoutError, ClientError) as err:
            raise ZodiacConnectionError("Unable to read robot WebSocket status") from err

    async def _async_ws_set_mode(self, device_id: str, mode: int) -> None:
        await self._ensure_login()
        try:
            user_id = int(float(self.user_id))
        except ValueError as err:
            raise ZodiacApiError("Invalid Zodiac user ID") from err

        subscribe = {
            "version": 1,
            "action": "subscribe",
            "namespace": "authorization",
            "service": "Authorization",
            "target": device_id,
            "payload": {"userId": user_id},
        }
        try:
            async with asyncio.timeout(25):
                async with self._session.ws_connect(
                    ZODIAC_WS_URL,
                    headers={"Authorization": self.id_token},
                    origin=ZODIAC_WS_ORIGIN,
                ) as websocket:
                    await websocket.send_json(subscribe)
                    initial = await self._wait_for_ws_payload(
                        websocket, device_id, service="Authorization"
                    )
                    robot_key = self._robot_key(initial)
                    command = {
                        "version": 1,
                        "action": "setState",
                        "namespace": "cyclonext",
                        "service": "StateController",
                        "target": device_id,
                        "payload": {
                            "state": {
                                "desired": {"equipment": {robot_key: {"mode": mode}}}
                            },
                            "clientToken": (
                                f"{user_id}|{secrets.token_urlsafe(16)}|"
                                f"{secrets.token_urlsafe(16)}"
                            ),
                        },
                    }
                    await websocket.send_json(command)
                    await self._wait_for_ws_payload(
                        websocket, device_id, service="StateStreamer"
                    )
        except (TimeoutError, ClientError) as err:
            raise ZodiacConnectionError("Unable to control robot") from err

    async def _wait_for_ws_payload(
        self, websocket: Any, device_id: str, *, service: str
    ) -> dict[str, Any]:
        while True:
            message = await websocket.receive()
            if message.type == WSMsgType.TEXT:
                data = message.json()
                if data.get("target") != device_id or data.get("service") != service:
                    continue
                payload = data.get("payload")
                if isinstance(payload, dict):
                    return payload
            elif message.type in (WSMsgType.CLOSED, WSMsgType.CLOSE, WSMsgType.ERROR):
                raise ZodiacConnectionError("Robot WebSocket closed unexpectedly")

    @staticmethod
    async def _read_json(response: ClientResponse) -> Any:
        try:
            return await response.json(content_type=None)
        except (ValueError, ClientError):
            return {}

    @staticmethod
    def _reported(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if isinstance(payload.get("robot"), Mapping):
            payload = payload["robot"]
        state = payload.get("state") if isinstance(payload, Mapping) else None
        if isinstance(state, Mapping):
            reported = state.get("reported")
            if isinstance(reported, Mapping):
                return reported
        reported = payload.get("reported") if isinstance(payload, Mapping) else None
        return reported if isinstance(reported, Mapping) else {}

    @classmethod
    def _robot_key(cls, payload: Mapping[str, Any]) -> str:
        equipment = cls._reported(payload).get("equipment")
        if not isinstance(equipment, Mapping) or not equipment:
            raise ZodiacApiError("Robot equipment was not present in cloud response")
        return next(
            (str(key) for key in equipment if str(key).startswith("robot")),
            str(next(iter(equipment))),
        )

    @classmethod
    def _normalize_cyclonext(
        cls, device: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        reported = cls._reported(payload)
        robot_key = cls._robot_key(payload)
        equipment = reported.get("equipment") or {}
        robot = equipment.get(robot_key) or {}
        error_data = robot.get("errors") if isinstance(robot, Mapping) else {}
        error_data = error_data if isinstance(error_data, Mapping) else {}
        ebox_data = reported.get("eboxData")
        ebox_data = ebox_data if isinstance(ebox_data, Mapping) else {}
        aws_data = reported.get("aws")
        aws_data = aws_data if isinstance(aws_data, Mapping) else {}

        mode = cls._as_int(robot.get("mode"), 0)
        error_code = cls._as_int(error_data.get("code"), 0)
        total_minutes = cls._as_float(
            robot.get("totRunTime", robot.get("totalRunTime")), None
        )
        remaining = cls._first_number(
            robot,
            "minutesRemaining",
            "remainingTime",
            "timeRemaining",
            "remaining",
        )
        return {
            "name": str(device.get("name") or "Zodiac Pool Robot"),
            "serial_number": str(device.get("serial_number") or ""),
            "device_type": str(device.get("device_type") or DEVICE_TYPE_CYCLONEXT),
            "model": str(device.get("model") or reported.get("model") or "CycloneXT"),
            "available": aws_data.get("status") in (None, "connected", "online"),
            "connection": str(aws_data.get("status") or "unknown"),
            "mode": mode,
            "running": mode == 1,
            "error_code": error_code,
            "error": cls._error_name(error_code),
            "canister": "full" if cls._as_int(robot.get("canister"), 0) else "ok",
            "cleaning_cycle": robot.get("cycle"),
            "remaining_minutes": remaining,
            "total_runtime_hours": (
                round(total_minutes / 60, 1) if total_minutes is not None else None
            ),
            "control_box_firmware": reported.get("vr"),
            "robot_firmware": robot.get("vr"),
            "control_box_serial": ebox_data.get("controlBoxSn"),
            "product_serial": ebox_data.get("completeCleanerSn"),
            "raw_robot": dict(robot),
        }

    @classmethod
    def _normalize_i2d(
        cls, device: Mapping[str, Any], response: str
    ) -> dict[str, Any]:
        try:
            raw = bytes.fromhex(response)
        except ValueError as err:
            raise ZodiacApiError("Invalid legacy status response") from err
        if len(raw) < 18 or raw[0:2] != b"\x00\x11":
            raise ZodiacApiError("Unexpected legacy status response")
        state = raw[2]
        error_code = raw[3]
        cleaning_mode = raw[4]
        return {
            "name": str(device.get("name") or "Zodiac Pool Robot"),
            "serial_number": str(device.get("serial_number") or ""),
            "device_type": DEVICE_TYPE_I2D_ROBOT,
            "model": "i2d Robot",
            "available": True,
            "connection": "connected",
            "mode": state,
            "running": state in (2, 4, 12),
            "error_code": error_code,
            "error": cls._error_name(error_code),
            "canister": "full" if cleaning_mode >> 4 else "ok",
            "cleaning_cycle": cleaning_mode & 0x0F,
            "remaining_minutes": raw[5],
            "total_runtime_hours": round(int.from_bytes(raw[9:12], "little") / 60, 1),
            "control_box_firmware": device.get("firmware_version"),
            "robot_firmware": None,
            "control_box_serial": None,
            "product_serial": None,
            "raw_robot": {},
        }

    @staticmethod
    def _error_name(error_code: int) -> str:
        return {
            0: "none",
            4: "pump_motor_consumption",
            5: "right_drive_motor_consumption",
            8: "out_of_water",
            10: "communication",
        }.get(error_code, f"error_{error_code}")

    @staticmethod
    def _as_int(value: Any, default: int) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_float(value: Any, default: float | None) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _first_number(cls, source: Mapping[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = cls._as_float(source.get(key), None)
            if value is not None:
                return value
        return None
