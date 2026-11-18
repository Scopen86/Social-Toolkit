"""Persistent log for failed group uploads."""

from __future__ import annotations

import datetime
import os

DEFAULT_FAILURE_LOG = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "tools",
        "facebook_group_repost",
        "data",
        "upload_failures.log",
    )
)


def log_upload_failure(
    link: str,
    error: object,
    name: str = "",
    path: str | None = None,
) -> str:
    """Append one failed upload to the log and return the log path."""
    log_path = os.path.abspath(os.path.expanduser(path or DEFAULT_FAILURE_LOG))
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_text = " ".join(str(error).split())
    line = f"{timestamp} | {name or '(unknown)'} | {link} | {error_text}\n"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as file:
        file.write(line)
    return log_path
