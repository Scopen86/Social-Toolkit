"""Editable values and manual examples for the Discord API client."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.discord_engine import DiscordEngine  # noqa: E402


# Select "interaction", "fetch", "component", or "message" before running this file.
ACTION = "interaction"

# Message request variables.
CHANNEL_ID = ""  # Fill in the target channel ID.
MESSAGE_CONTENT = ""  # Plain text; use interaction for slash commands.

# Token and session ID are kept together in this local, git-ignored file.
AUTH_FILE = PROJECT_ROOT / "tools" / "discord_interaction" / "data" / "discord_auth.json"
INTERACTION_TYPE = 2
APPLICATION_ID = ""
GUILD_ID = ""
COMMAND_ID = ""
COMMAND_VERSION = ""
COMMAND_NAME = ""
COMMAND_OPTIONS = []

# For a button click, copy these IDs from the target bot message/component.
MESSAGE_ID = ""
BUTTON_CUSTOM_ID = ""


def load_session_id() -> str:
    """Read the client session ID stored in the local auth file."""

    with AUTH_FILE.open(encoding="utf-8") as file:
        session_id = json.load(file).get("session_id", "")
    if not session_id:
        raise ValueError(f"Add a current session_id to {AUTH_FILE}")
    return session_id


def make_interaction_payload() -> dict:
    """Build the reduced interaction body confirmed by the API probes."""

    data = {
        "version": COMMAND_VERSION,
        "id": COMMAND_ID,
        "name": COMMAND_NAME,
    }
    if COMMAND_OPTIONS:
        data["options"] = COMMAND_OPTIONS
    return {
        "type": INTERACTION_TYPE,
        "application_id": APPLICATION_ID,
        "guild_id": GUILD_ID,
        "channel_id": CHANNEL_ID,
        "session_id": load_session_id(),
        "data": data,
    }


def extract_buttons(components: list[dict]) -> list[dict[str, str]]:
    """Collect button labels and custom IDs from nested message components."""

    found = []
    for component in components:
        if component.get("custom_id"):
            found.append(
                {
                    "label": str(component.get("label") or "(unlabeled)"),
                    "custom_id": str(component["custom_id"]),
                }
            )
        found.extend(extract_buttons(component.get("components", [])))
    return found


def main() -> None:
    engine = DiscordEngine()
    if ACTION == "message":
        result = engine.send_message(CHANNEL_ID, MESSAGE_CONTENT)
    elif ACTION == "interaction":
        result = engine.invoke_interaction(make_interaction_payload())
    elif ACTION == "fetch":
        messages = engine.get_channel_messages(CHANNEL_ID, limit=20)
        result = [
            {
                "message_id": message.get("id"),
                "author": message.get("author", {}).get("username"),
                "content": message.get("content", ""),
                "buttons": extract_buttons(message.get("components", [])),
            }
            for message in messages
            if message.get("application_id") == APPLICATION_ID
            or message.get("author", {}).get("id") == APPLICATION_ID
        ]
    elif ACTION == "component":
        result = engine.click_component(
            application_id=APPLICATION_ID,
            guild_id=GUILD_ID,
            channel_id=CHANNEL_ID,
            message_id=MESSAGE_ID,
            session_id=load_session_id(),
            custom_id=BUTTON_CUSTOM_ID,
        )
    else:
        raise ValueError('ACTION must be "message", "interaction", "fetch", or "component"')
    print(result)


if __name__ == "__main__":
    main()
