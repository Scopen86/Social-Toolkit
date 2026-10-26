"""Small Discord API client based on the captured v9 requests."""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTH_FILE = (
    PROJECT_ROOT / "tools" / "discord_interaction" / "data" / "discord_auth.json"
)
API_BASE = "https://discord.com/api/v9"


class DiscordAPIError(RuntimeError):
    """Raised when Discord rejects a request or the connection fails."""


def _snowflake_like_nonce() -> str:
    """Return a fresh nonce shaped like the integer values in the captures."""

    timestamp_ms = int(time.time() * 1000)
    return str((timestamp_ms - 1_420_070_400_000) << 22 | secrets.randbits(22))


class DiscordEngine:
    """Send messages and invoke application commands through Discord API v9."""

    def __init__(
        self,
        token: str | None = None,
        *,
        auth_file: str | Path = DEFAULT_AUTH_FILE,
        timeout: float = 20,
    ) -> None:
        self.auth_file = Path(auth_file)
        self.timeout = timeout
        self.token = (token or self._read_token()).strip()
        if not self.token:
            raise ValueError(f"Discord token is empty; set it in {self.auth_file}")

    def _read_token(self) -> str:
        try:
            auth = json.loads(self.auth_file.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Discord auth file not found: {self.auth_file}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {self.auth_file}") from exc
        token = auth.get("token", "") if isinstance(auth, dict) else ""
        if not isinstance(token, str) or not token.strip():
            raise ValueError(f"Add a non-empty token field to {self.auth_file}")
        return token.strip()

    def _post(self, endpoint: str, payload: dict[str, Any]) -> Any:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{API_BASE}{endpoint}",
            data=body,
            method="POST",
            headers={
                "Authorization": self.token,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Social-Toolkit/1.0",
                "X-Discord-Locale": "en-US",
                "X-Discord-Timezone": "Asia/Saigon",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_body = response.read()
                if not response_body:
                    return None
                return json.loads(response_body.decode("utf-8"))
        except HTTPError as exc:
            # Avoid echoing response bodies, which can contain account data.
            raise DiscordAPIError(f"Discord API returned HTTP {exc.code}") from exc
        except URLError as exc:
            raise DiscordAPIError(f"Could not reach Discord API: {exc.reason}") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DiscordAPIError("Discord returned an unreadable response") from exc

    def _get(self, endpoint: str) -> Any:
        request = Request(
            f"{API_BASE}{endpoint}",
            method="GET",
            headers={
                "Authorization": self.token,
                "Accept": "application/json",
                "User-Agent": "Social-Toolkit/1.0",
                "X-Discord-Locale": "en-US",
                "X-Discord-Timezone": "Asia/Saigon",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_body = response.read()
                if not response_body:
                    return None
                return json.loads(response_body.decode("utf-8"))
        except HTTPError as exc:
            raise DiscordAPIError(f"Discord API returned HTTP {exc.code}") from exc
        except URLError as exc:
            raise DiscordAPIError(f"Could not reach Discord API: {exc.reason}") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DiscordAPIError("Discord returned an unreadable response") from exc

    def get_channel_messages(self, channel_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch recent channel messages, including component data when available."""

        if not channel_id:
            raise ValueError("channel_id is required")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        query = urlencode({"limit": limit})
        messages = self._get(f"/channels/{channel_id}/messages?{query}")
        if not isinstance(messages, list):
            raise DiscordAPIError("Discord returned an unexpected messages response")
        return messages

    def send_message(
        self,
        channel_id: str,
        content: str,
        *,
        tts: bool = False,
        flags: int = 0,
        nonce: str | None = None,
    ) -> Any:
        """Send a text message using the captured channel message endpoint."""

        if not channel_id or not content:
            raise ValueError("channel_id and non-empty content are required")
        payload = {
            "mobile_network_type": "unknown",
            "content": content,
            "nonce": nonce or _snowflake_like_nonce(),
            "tts": tts,
            "flags": flags,
        }
        return self._post(f"/channels/{channel_id}/messages", payload)

    def invoke_interaction(
        self,
        payload: dict[str, Any],
    ) -> Any:
        """POST an interaction payload supplied by the caller without changes."""

        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")
        if not payload.get("session_id"):
            raise ValueError("payload must include a current session_id")
        return self._post("/interactions", payload)

    def click_component(
        self,
        *,
        application_id: str,
        guild_id: str,
        channel_id: str,
        message_id: str,
        session_id: str,
        custom_id: str,
        message_flags: int = 0,
    ) -> Any:
        """Send the captured button-click interaction for a bot message."""

        required = {
            "application_id": application_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "message_id": message_id,
            "session_id": session_id,
            "custom_id": custom_id,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError("Missing component interaction fields: " + ", ".join(missing))

        payload = {
            "type": 3,
            "nonce": _snowflake_like_nonce(),
            "guild_id": guild_id,
            "channel_id": channel_id,
            "message_flags": message_flags,
            "message_id": message_id,
            "application_id": application_id,
            "session_id": session_id,
            "data": {"component_type": 2, "custom_id": custom_id},
        }
        return self.invoke_interaction(payload)
