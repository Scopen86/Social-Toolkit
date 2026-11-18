"""Tkinter interface for manually trying the Discord API requests."""

from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
import time
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.discord_engine import DiscordEngine  # noqa: E402


DATA_DIR = PROJECT_ROOT / "tools" / "discord_interaction" / "data"
AUTH_FILE = DATA_DIR / "discord_auth.json"


def _read_saved_session_id() -> str:
    try:
        auth_data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(auth_data.get("session_id", "")) if isinstance(auth_data, dict) else ""


class DiscordTab(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.root = self.winfo_toplevel()

        self.action = tk.StringVar(value="interaction")
        self.channel_id = tk.StringVar()
        self.session_id = tk.StringVar(value=_read_saved_session_id())
        self.application_id = tk.StringVar()
        self.guild_id = tk.StringVar()
        self.command_id = tk.StringVar()
        self.command_version = tk.StringVar()
        self.command_name = tk.StringVar()
        self.message_id = tk.StringVar()
        self.custom_id = tk.StringVar()
        self._last_interaction_at: float | None = None
        self._current_buttons: dict[str, str] = {}
        self._button_choice_frame: ttk.Frame | None = None

        self._build()

    def _build(self) -> None:
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        outer = ttk.Frame(canvas, padding=12)

        outer.bind(
            "<Configure>",
            lambda event, c=canvas: c.configure(scrollregion=c.bbox("all")),
        )
        window = canvas.create_window((0, 0), window=outer, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event, c=canvas, w=window: c.itemconfigure(w, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event, c=canvas):
            if c.winfo_exists():
                bbox = c.bbox("all")
                if bbox and bbox[3] > c.winfo_height():
                    c.yview_scroll(int(-1 * (event.delta / 120)), "units")

        container.bind("<Enter>", lambda _e, c=canvas, h=_on_mousewheel: c.bind_all("<MouseWheel>", h))
        container.bind("<Leave>", lambda _e, c=canvas: c.unbind_all("<MouseWheel>"))

        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)

        ttk.Label(outer, text="Discord API", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Label(
            outer,
            text=f"Token is loaded from {AUTH_FILE} and is never shown here.",
            wraplength=800,
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))

        action_frame = ttk.LabelFrame(outer, text="Request type", padding=8)
        action_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ttk.Radiobutton(
            action_frame, text="Send message", variable=self.action, value="message"
        ).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(
            action_frame, text="Invoke slash command", variable=self.action, value="interaction"
        ).pack(side="left")
        ttk.Radiobutton(
            action_frame, text="Click button", variable=self.action, value="component"
        ).pack(side="left", padx=(16, 0))

        self.form = ttk.Frame(outer)
        self.form.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        self.form.columnconfigure(0, weight=1)

        self.message_frame = ttk.LabelFrame(self.form, text="Message", padding=8)
        self.message_frame.columnconfigure(1, weight=1)
        self._entry(self.message_frame, 0, "Channel ID", self.channel_id)
        ttk.Label(self.message_frame, text="Message content").grid(
            row=1, column=0, sticky="nw", padx=(0, 8), pady=3
        )
        self.message_text = tk.Text(self.message_frame, height=3, wrap="word")
        self.message_text.grid(row=1, column=1, sticky="ew", pady=3)

        self.interaction_frame = ttk.LabelFrame(
            self.form, text="Slash command", padding=8
        )
        self.interaction_frame.columnconfigure(1, weight=1)
        self._entry(self.interaction_frame, 0, "Channel ID", self.channel_id)
        self._entry(self.interaction_frame, 1, "Session ID", self.session_id)
        self._entry(self.interaction_frame, 2, "Application ID", self.application_id)
        self._entry(self.interaction_frame, 3, "Guild ID", self.guild_id)
        self._entry(self.interaction_frame, 4, "Command ID", self.command_id)
        self._entry(self.interaction_frame, 5, "Command version", self.command_version)
        self._entry(self.interaction_frame, 6, "Command name", self.command_name)
        ttk.Label(self.interaction_frame, text="Options (JSON list)").grid(
            row=7, column=0, sticky="nw", padx=(0, 8), pady=3
        )
        self.options_text = tk.Text(self.interaction_frame, height=3, wrap="word")
        self.options_text.insert("1.0", "[]")
        self.options_text.grid(row=7, column=1, sticky="ew", pady=3)

        self.component_frame = ttk.LabelFrame(
            self.form, text="Button on a bot message", padding=8
        )
        self.component_frame.columnconfigure(1, weight=1)
        self._entry(self.component_frame, 0, "Channel ID", self.channel_id)
        self._entry(self.component_frame, 1, "Session ID", self.session_id)
        self._entry(self.component_frame, 2, "Application ID", self.application_id)
        self._entry(self.component_frame, 3, "Guild ID", self.guild_id)
        self._entry(self.component_frame, 4, "Message ID", self.message_id)
        self._entry(self.component_frame, 5, "Button custom_id", self.custom_id)
        ttk.Label(
            self.component_frame,
            text="Fetch scans recent messages from this application and lists their enabled buttons.",
            wraplength=700,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self.fetch_buttons_button = ttk.Button(
            self.component_frame,
            text="Fetch recent bot buttons",
            command=self._load_recent_buttons,
        )
        self.fetch_buttons_button.grid(row=7, column=0, sticky="w", pady=(8, 3))
        self._button_choice_frame = ttk.Frame(self.component_frame)
        self._button_choice_frame.grid(row=7, column=1, sticky="w", pady=(8, 3))

        self.action.trace_add("write", self._show_request_fields)
        self._show_request_fields()

        action_row = ttk.Frame(outer)
        action_row.grid(row=4, column=0, sticky="nsew")
        action_row.columnconfigure(0, weight=1)
        action_row.rowconfigure(1, weight=1)
        self.send_button = ttk.Button(action_row, text="Send request", command=self._send)
        self.send_button.grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(action_row, text="Response").grid(row=1, column=0, sticky="nw")
        self.output = ScrolledText(action_row, height=12, wrap="word", state="disabled")
        self.output.grid(row=2, column=0, sticky="nsew")
        action_row.rowconfigure(2, weight=1)

    @staticmethod
    def _entry(parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=3)

    def _show_request_fields(self, *_args: object) -> None:
        self.message_frame.grid_forget()
        self.interaction_frame.grid_forget()
        self.component_frame.grid_forget()
        if self.action.get() == "message":
            self.message_frame.grid(row=0, column=0, sticky="ew")
        elif self.action.get() == "interaction":
            self.interaction_frame.grid(row=0, column=0, sticky="ew")
        else:
            self.component_frame.grid(row=0, column=0, sticky="ew")

    def _interaction_payload(self) -> dict[str, Any]:
        try:
            options = json.loads(self.options_text.get("1.0", "end-1c"))
        except json.JSONDecodeError as exc:
            raise ValueError("Options must be valid JSON") from exc
        if not isinstance(options, list):
            raise ValueError("Options must be a JSON list")
        required_fields = {
            "Channel ID": self.channel_id.get().strip(),
            "Session ID": self.session_id.get().strip(),
            "Application ID": self.application_id.get().strip(),
            "Guild ID": self.guild_id.get().strip(),
            "Command ID": self.command_id.get().strip(),
            "Command version": self.command_version.get().strip(),
            "Command name": self.command_name.get().strip(),
        }
        missing = [label for label, value in required_fields.items() if not value]
        if missing:
            raise ValueError("Fill in: " + ", ".join(missing))

        data: dict[str, Any] = {
            "version": self.command_version.get().strip(),
            "id": self.command_id.get().strip(),
            "name": self.command_name.get().strip(),
        }
        if options:
            data["options"] = options
        return {
            "type": 2,
            "application_id": self.application_id.get().strip(),
            "guild_id": self.guild_id.get().strip(),
            "channel_id": self.channel_id.get().strip(),
            "session_id": self.session_id.get().strip(),
            "data": data,
        }

    @staticmethod
    def _message_buttons(
        components: list[dict[str, Any]],
    ) -> list[tuple[str, str, bool]]:
        buttons: list[tuple[str, str, bool]] = []
        for component in components:
            custom_id = component.get("custom_id")
            if custom_id:
                label = str(component.get("label") or "(unlabeled button)")
                buttons.append((label, str(custom_id), bool(component.get("disabled"))))
            children = component.get("components", [])
            if isinstance(children, list):
                buttons.extend(DiscordTab._message_buttons(children))
        return buttons

    @staticmethod
    def _message_timestamp(message: dict[str, Any]) -> float | None:
        value = message.get("edited_timestamp") or message.get("timestamp")
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    @staticmethod
    def _message_text(message: dict[str, Any]) -> str:
        parts = [str(message.get("content") or "")]
        for embed in message.get("embeds") or []:
            for key in ("author", "title", "description"):
                value = embed.get(key)
                if isinstance(value, dict):
                    value = value.get("name")
                if value:
                    parts.append(str(value))
            for field in embed.get("fields") or []:
                name = field.get("name")
                value = field.get("value")
                if name:
                    parts.append(str(name))
                if value:
                    parts.append(str(value))
            footer = embed.get("footer") or {}
            if footer.get("text"):
                parts.append(str(footer["text"]))
        return "\n".join(part for part in parts if part)

    @classmethod
    def _format_bot_message(
        cls, message: dict[str, Any], active_buttons: dict[str, str] | None = None
    ) -> str:
        author = message.get("author") or {}
        author_name = author.get("username") or author.get("global_name") or "Bot"
        lines = [f"Bot: {author_name}", f"Message ID: {message.get('id', '')}"]
        content = str(message.get("content") or "").strip()
        if content:
            lines.extend(("Content:", content))
        for index, embed in enumerate(message.get("embeds") or [], start=1):
            lines.append(f"Embed {index}:")
            author = embed.get("author") or {}
            if author.get("name"):
                lines.append(f"  {author['name']}")
            if embed.get("title"):
                lines.append(f"  {embed['title']}")
            if embed.get("description"):
                lines.append(f"  {embed['description']}")
            for field in embed.get("fields") or []:
                name = str(field.get("name") or "").strip()
                value = str(field.get("value") or "").strip()
                if name or value:
                    lines.append(f"  {name}: {value}" if name else f"  {value}")
            footer = embed.get("footer") or {}
            if footer.get("text"):
                lines.append(f"  {footer['text']}")
        if active_buttons:
            lines.append("Enabled buttons: " + ", ".join(active_buttons))
        return "\n".join(lines)

    @classmethod
    def _collect_bot_state(
        cls,
        messages: list[dict[str, Any]],
        application_id: str,
        action_time: float,
    ) -> tuple[tuple[str, dict[str, str], bool] | None, str, bool, bool]:
        newest_active: tuple[str, dict[str, str], bool] | None = None
        newest_after_action: tuple[str, dict[str, str], bool] | None = None
        newest_bot_message: dict[str, Any] | None = None
        newest_bot_after_action: dict[str, Any] | None = None

        for message in messages:
            author = message.get("author") or {}
            if not (
                message.get("application_id") == application_id
                or author.get("id") == application_id
            ):
                continue

            message_time = cls._message_timestamp(message)
            is_after_action = message_time is not None and message_time >= action_time
            current_buttons = {
                label.strip().casefold(): custom_id
                for label, custom_id, disabled in cls._message_buttons(
                    message.get("components") or []
                )
                if not disabled
            }
            if newest_bot_message is None:
                newest_bot_message = message
            if is_after_action and newest_bot_after_action is None:
                newest_bot_after_action = message
            if current_buttons:
                candidate = (
                    str(message.get("id", "")),
                    current_buttons,
                    is_after_action,
                )
                if newest_active is None:
                    newest_active = candidate
                if is_after_action and newest_after_action is None:
                    newest_after_action = candidate

        selected_reply = newest_after_action or newest_active
        selected_bot_message = newest_bot_after_action or newest_bot_message
        active_buttons = (
            selected_reply[1]
            if selected_bot_message is not None
            and selected_reply is not None
            and selected_reply[0] == str(selected_bot_message.get("id", ""))
            else None
        )
        if selected_bot_message is None:
            summary = "No messages from this application found in the 50 most recent channel messages."
        else:
            summary = cls._format_bot_message(selected_bot_message, active_buttons)
        used_fallback = newest_after_action is None and newest_active is not None
        has_new_response = newest_bot_after_action is not None
        return selected_reply, summary, used_fallback, has_new_response

    def _load_recent_buttons(self) -> None:
        channel_id = self.channel_id.get().strip()
        application_id = self.application_id.get().strip()
        action_time = self._last_interaction_at
        if not channel_id or not application_id:
            missing = []
            if not channel_id:
                missing.append("Channel ID")
            if not application_id:
                missing.append("Application ID")
            messagebox.showerror(
                "Invalid request", "Fill in: " + ", ".join(missing), parent=self.root
            )
            return
        if action_time is None:
            self._finish_fetch(
                "Send a slash command or click a bot button from this GUI first, "
                "then fetch its reply so older messages are excluded."
            )
            return

        try:
            engine = DiscordEngine(auth_file=AUTH_FILE)
        except Exception as exc:
            messagebox.showerror("Invalid request", str(exc), parent=self.root)
            return

        self.fetch_buttons_button.configure(state="disabled")
        self._show_output("Fetching recent bot messages…")

        def worker() -> None:
            try:
                messages = engine.get_channel_messages(channel_id, limit=50)
                state = self._collect_bot_state(
                    messages, application_id, action_time
                )
                self.root.after(
                    0,
                    lambda: self._show_current_buttons(
                        state[0],
                        used_fallback=state[2],
                        response_summary=state[1],
                    ),
                )
            except Exception as exc:
                error_message = f"{type(exc).__name__}: {exc}"
                self.root.after(0, lambda text=error_message: self._finish_fetch(text))

        threading.Thread(target=worker, daemon=True).start()

    def _show_current_buttons(
        self,
        reply: tuple[str, dict[str, str], bool] | None,
        *,
        used_fallback: bool = False,
        response_summary: str = "",
    ) -> None:
        self.fetch_buttons_button.configure(state="normal")
        self._current_buttons = {}
        if self._button_choice_frame is not None:
            for child in self._button_choice_frame.winfo_children():
                child.destroy()
        if reply is None:
            self.message_id.set("")
            self.custom_id.set("")
            self._show_output(
                f"{response_summary}\n\nNo enabled buttons found in the "
                "50 most recent messages."
            )
            return

        message_id, buttons, _is_after_action = reply
        self.message_id.set(message_id)
        self.custom_id.set("")
        self._current_buttons = buttons
        if self._button_choice_frame is not None:
            for label in buttons:
                ttk.Button(
                    self._button_choice_frame,
                    text=f"Send {label}",
                    command=lambda button_label=label: self._send_bot_button(button_label),
                ).pack(side="left", padx=(0, 8))
        if used_fallback:
            button_note = (
                f"Button target: {message_id} (older than the latest interaction; "
                "confirm it is still current before choosing)."
            )
        else:
            button_note = f"Button target: {message_id}. Choose an enabled button."
        self._show_output(f"{response_summary}\n\n{button_note}")

    def _send_bot_button(self, label: str) -> None:
        custom_id = self._current_buttons.get(label.casefold())
        if not custom_id or not self.message_id.get().strip():
            messagebox.showerror(
                "No current button",
                "Fetch the current bot reply first.",
                parent=self.root,
            )
            return
        self.custom_id.set(custom_id)
        self._send()

    def _finish_fetch(self, text: str) -> None:
        self.fetch_buttons_button.configure(state="normal")
        self._show_output(text)

    def _send(self) -> None:
        action = self.action.get()
        request_started_at = time.time()
        try:
            engine = DiscordEngine(auth_file=AUTH_FILE)
            if action == "message":
                channel_id = self.channel_id.get().strip()
                content = self.message_text.get("1.0", "end-1c").strip()
                request = lambda: engine.send_message(channel_id, content)
            elif action == "interaction":
                payload = self._interaction_payload()
                request = lambda: engine.invoke_interaction(payload)
            else:
                request = lambda: engine.click_component(
                    application_id=self.application_id.get().strip(),
                    guild_id=self.guild_id.get().strip(),
                    channel_id=self.channel_id.get().strip(),
                    message_id=self.message_id.get().strip(),
                    session_id=self.session_id.get().strip(),
                    custom_id=self.custom_id.get().strip(),
                )
        except Exception as exc:
            messagebox.showerror("Invalid request", str(exc), parent=self.root)
            return

        self.send_button.configure(state="disabled")
        if action in {"interaction", "component"}:
            self._current_buttons = {}
            if self._button_choice_frame is not None:
                for child in self._button_choice_frame.winfo_children():
                    child.destroy()
        self._show_output("Sending request…")

        def worker() -> None:
            try:
                result = request()
                display = json.dumps(result, ensure_ascii=False, indent=2) if result is not None else "Request succeeded (empty response)."
                self.root.after(
                    0,
                    lambda: self._finish_action(display, action, request_started_at),
                )
            except Exception as exc:
                error_message = f"{type(exc).__name__}: {exc}"
                self.root.after(0, lambda text=error_message: self._finish(text))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_action(self, text: str, action: str, action_time: float) -> None:
        if action in {"interaction", "component"}:
            self._last_interaction_at = action_time
            if action == "interaction":
                self.action.set("component")
            self._show_output(
                f"{text}\nWaiting briefly for the bot's response…"
            )
            self._poll_bot_response(action_time)
            return
        self._finish(text)

    def _poll_bot_response(self, action_time: float) -> None:
        channel_id = self.channel_id.get().strip()
        application_id = self.application_id.get().strip()
        try:
            engine = DiscordEngine(auth_file=AUTH_FILE, timeout=8)
        except Exception as exc:
            self._finish(f"Request accepted, but could not refresh bot messages: {exc}")
            return

        self.fetch_buttons_button.configure(state="disabled")

        def worker() -> None:
            state: tuple[tuple[str, dict[str, str], bool] | None, str, bool, bool] = (
                None,
                "No reply from this application found.",
                False,
                False,
            )
            try:
                for attempt in range(6):
                    messages = engine.get_channel_messages(channel_id, limit=50)
                    state = self._collect_bot_state(messages, application_id, action_time)
                    if state[3]:
                        break
                    if attempt < 5:
                        time.sleep(1)
                self.root.after(
                    0,
                    lambda: self._finish_polled_bot_response(state),
                )
            except Exception as exc:
                error_message = f"Request was accepted, but refreshing bot messages failed: {type(exc).__name__}: {exc}"
                self.root.after(0, lambda text=error_message: self._finish_poll_error(text))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_polled_bot_response(
        self,
        state: tuple[tuple[str, dict[str, str], bool] | None, str, bool, bool],
    ) -> None:
        reply, summary, used_fallback, has_new_response = state
        if has_new_response:
            self._show_current_buttons(
                reply,
                used_fallback=used_fallback,
                response_summary=summary,
            )
        else:
            self.fetch_buttons_button.configure(state="normal")
            self._current_buttons = {}
            if self._button_choice_frame is not None:
                for child in self._button_choice_frame.winfo_children():
                    child.destroy()
            self.message_id.set("")
            self.custom_id.set("")
            self._show_output(
                "Discord accepted the interaction (204), but no new message "
                "from this application arrived yet. Use Fetch recent bot buttons to refresh.\n\n"
                f"Last visible bot message:\n{summary}"
            )
        self.send_button.configure(state="normal")

    def _finish_poll_error(self, text: str) -> None:
        self.fetch_buttons_button.configure(state="normal")
        self._finish(text)

    def _show_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def _finish(self, text: str) -> None:
        self._show_output(text)
        self.send_button.configure(state="normal")