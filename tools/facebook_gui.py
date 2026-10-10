"""Tkinter GUI for the Facebook Selenium automation library."""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from lib.facebook_engine import (
    comment_on_post,
    extract_post_message,
    get_dialog,
    like_post,
    login,
    post_to_group,
    share_post,
)


DATA_DIR = os.path.join(os.path.dirname(__file__), "facebook_group_repost", "data")
AUTH_DIR = os.path.join(DATA_DIR, "auth")


class FacebookGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Social Toolkit - Facebook")
        self.geometry("980x760")
        self.minsize(820, 620)

        self.driver = None
        self.worker = None
        self.log_queue = queue.Queue()
        self.verification_event = None
        self.cancel_event = threading.Event()
        self.status_text = tk.StringVar(value="Ready")

        self.cookie_login = tk.BooleanVar(value=True)
        self.credential_file = tk.StringVar(
            value=os.path.join(AUTH_DIR, "facebook_credentials.txt")
        )
        self.cookies_file = tk.StringVar(
            value=os.path.join(AUTH_DIR, "facebook_cookies.json")
        )
        self.post_url = tk.StringVar()
        self.comment_text = tk.StringVar()
        self.share_text = tk.StringVar()
        self.group_url = tk.StringVar()
        self.image_dir = tk.StringVar(value=os.path.join(DATA_DIR, "Images"))

        self._build_ui()
        self.after(100, self._drain_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        self.start_button = ttk.Button(toolbar, text="Start browser", command=self.start_browser)
        self.start_button.pack(side="left", padx=(0, 6))
        self.close_button = ttk.Button(
            toolbar, text="Close browser", command=self.close_browser, state="disabled"
        )
        self.close_button.pack(side="left")
        self.login_button = ttk.Button(
            toolbar, text="Login", command=self.login_facebook, state="disabled"
        )
        self.login_button.pack(side="left", padx=6)
        self.continue_button = ttk.Button(
            toolbar,
            text="Verification complete",
            command=self.finish_verification,
            state="disabled",
        )
        self.continue_button.pack(side="left")
        self.cancel_button = ttk.Button(
            toolbar, text="Cancel task", command=self.cancel_task, state="disabled"
        )
        self.cancel_button.pack(side="left", padx=6)
        ttk.Label(toolbar, text="Status:").pack(side="left", padx=(18, 4))
        self.status_label = ttk.Label(toolbar, textvariable=self.status_text)
        self.status_label.pack(side="left")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.post_tab = ttk.Frame(notebook, padding=10)
        self.group_tab = ttk.Frame(notebook, padding=10)
        self.repost_tab = ttk.Frame(notebook, padding=10)
        notebook.add(self.post_tab, text="Post actions")
        notebook.add(self.group_tab, text="Group post")
        notebook.add(self.repost_tab, text="Multi-group repost")

        self._build_auth_section(self.post_tab)
        self._build_post_actions(self.post_tab)
        self._build_group_post(self.group_tab)
        self._build_repost(self.repost_tab)

        log_frame = ttk.LabelFrame(self, text="Activity log", padding=6)
        log_frame.pack(fill="both", expand=False, padx=8, pady=(0, 8))
        self.log_text = tk.Text(log_frame, height=9, state="disabled", wrap="word")
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _build_auth_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Authentication", padding=8)
        frame.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(
            frame,
            text="Use saved cookies (fallback to credentials)",
            variable=self.cookie_login,
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        self._path_row(frame, 1, "Credentials:", self.credential_file)
        self._path_row(frame, 2, "Cookies:", self.cookies_file)

    def _build_post_actions(self, parent):
        frame = ttk.LabelFrame(parent, text="Post URL actions", padding=8)
        frame.pack(fill="x")
        ttk.Label(frame, text="Post URL:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.post_url, width=80).grid(
            row=0, column=1, columnspan=3, sticky="ew", padx=6
        )
        ttk.Button(frame, text="Read post", command=self.read_post).grid(row=1, column=0, pady=8)
        ttk.Button(frame, text="Like", command=self.like).grid(row=1, column=1, pady=8, sticky="w")
        ttk.Label(frame, text="Comment:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.comment_text, width=60).grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=6
        )
        ttk.Button(frame, text="Comment", command=self.comment).grid(row=3, column=0, pady=8)
        ttk.Label(frame, text="Share text:").grid(row=4, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.share_text, width=60).grid(
            row=4, column=1, columnspan=3, sticky="ew", padx=6
        )
        ttk.Button(frame, text="Share", command=self.share).grid(row=5, column=0, pady=8)
        frame.columnconfigure(1, weight=1)

    def _build_group_post(self, parent):
        frame = ttk.LabelFrame(parent, text="Post to one group", padding=8)
        frame.pack(fill="x")
        ttk.Label(frame, text="Group URL:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.group_url, width=80).grid(
            row=0, column=1, columnspan=3, sticky="ew", padx=6
        )
        ttk.Label(frame, text="Content:").grid(row=1, column=0, sticky="nw", pady=6)
        self.group_content = tk.Text(frame, height=7, width=70, wrap="word")
        self.group_content.grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=6)
        self._path_row(frame, 2, "Image folder:", self.image_dir, choose_directory=True)
        ttk.Button(frame, text="Post to group", command=self.post_group).grid(
            row=3, column=1, sticky="w", pady=8
        )
        frame.columnconfigure(1, weight=1)

    def _build_repost(self, parent):
        frame = ttk.LabelFrame(parent, text="Repost to multiple groups", padding=8)
        frame.pack(fill="x")
        self.group_links_file = tk.StringVar(
            value=os.path.join(DATA_DIR, "Group Links", "test.txt")
        )
        self._path_row(frame, 0, "Group links file:", self.group_links_file, start_column=0)
        self.repost_content_file = tk.StringVar(value=os.path.join(DATA_DIR, "content.txt"))
        self._path_row(frame, 1, "Content file:", self.repost_content_file, start_column=0)
        self._path_row(frame, 2, "Image folder:", self.image_dir, choose_directory=True)
        ttk.Button(frame, text="Repost to all groups", command=self.repost).grid(
            row=3, column=1, sticky="w", pady=8
        )
        frame.columnconfigure(1, weight=1)

    def _path_row(
        self, parent, row, label, variable, choose_directory=False, start_column=0
    ):
        ttk.Label(parent, text=label).grid(row=row, column=start_column, sticky="w", pady=3)
        ttk.Entry(parent, textvariable=variable, width=72).grid(
            row=row, column=start_column + 1, sticky="ew", padx=6, pady=3
        )
        ttk.Button(
            parent,
            text="Browse",
            command=lambda: self._browse(variable, choose_directory),
        ).grid(row=row, column=start_column + 2, sticky="w", pady=3)

    @staticmethod
    def _browse(variable, choose_directory):
        path = (
            filedialog.askdirectory()
            if choose_directory
            else filedialog.askopenfilename()
        )
        if path:
            variable.set(path)

    def _run(self, action, function, *args):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Busy", "Another Facebook operation is already running.")
            return
        if not self.driver:
            messagebox.showerror("Browser not started", "Click Start browser first.")
            return
        self._set_status(f"Running: {action}")
        self._log(f"Starting: {action}")
        self.cancel_event.clear()
        self.cancel_button.configure(state="normal")
        self.worker = threading.Thread(target=self._worker, args=(function, args), daemon=True)
        self.worker.start()

    def _worker(self, function, args):
        try:
            function(*args)
            if self.cancel_event.is_set():
                self._set_status("Cancelled")
                self._log("Task cancelled.")
            else:
                self._set_status("Completed")
        except Exception as exc:
            if self.cancel_event.is_set():
                self._log("Task cancelled.")
                self._set_status("Cancelled")
            else:
                self._log(f"ERROR: {exc}")
                self._set_status(f"Failed: {exc}")
        finally:
            self.after(0, lambda: self.cancel_button.configure(state="disabled"))

    def _cancelled(self):
        return self.cancel_event.is_set()

    def _raise_if_cancelled(self):
        if self._cancelled():
            raise RuntimeError("Task cancelled by user.")

    def cancel_task(self):
        if self.worker and self.worker.is_alive():
            self.cancel_event.set()
            if self.verification_event:
                self.verification_event.set()
            self._set_status("Cancelling...")
            self._log("Cancellation requested. The current browser step will finish safely.")

    def _log(self, message):
        self.log_queue.put(("log", str(message)))

    def _set_status(self, message):
        self.log_queue.put(("status", str(message)))

    def _drain_log_queue(self):
        while not self.log_queue.empty():
            message_type, message = self.log_queue.get_nowait()
            if message_type == "status":
                self.status_text.set(message)
            else:
                self.log_text.configure(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        self.after(100, self._drain_log_queue)

    def start_browser(self):
        try:
            options = Options()
            self.driver = webdriver.Chrome(options=options)
            self.driver.maximize_window()
            self.start_button.configure(state="disabled")
            self.close_button.configure(state="normal")
            self.login_button.configure(state="normal")
            self._log("Chrome browser started.")
            self._set_status("Browser ready")
        except Exception as exc:
            self._set_status(f"Failed to start browser: {exc}")
            messagebox.showerror("Browser error", str(exc))

    def close_browser(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
        self.start_button.configure(state="normal")
        self.close_button.configure(state="disabled")
        self.login_button.configure(state="disabled")
        self._log("Browser closed.")
        self._set_status("Browser closed")

    def login_facebook(self):
        self.verification_event = threading.Event()
        self.continue_button.configure(state="normal")
        self._run(
            "Facebook login",
            login,
            self.driver,
            self._log,
            self.cookie_login.get(),
            self.credential_file.get(),
            self.cookies_file.get(),
            self._wait_for_verification,
        )

    def _wait_for_verification(self):
        self._log("Complete Facebook verification in Chrome, then click 'Verification complete'.")
        self._set_status("Waiting for Facebook verification")
        self.verification_event.wait()
        self.verification_event = None
        self.after(0, lambda: self.continue_button.configure(state="disabled"))

    def finish_verification(self):
        if self.verification_event:
            self._log("Verification continuation requested.")
            self.verification_event.set()

    def _post_dialog(self):
        self._raise_if_cancelled()
        url = self.post_url.get().strip()
        if not url:
            raise ValueError("Enter a Facebook post URL.")
        dialog = get_dialog(self.driver, url, self._log)
        if dialog is None:
            raise RuntimeError("Post dialog was not found.")
        return dialog

    def read_post(self):
        self._run(
            "Read post",
            lambda: self._log("Post text:\n" + extract_post_message(self._post_dialog())),
        )

    def like(self):
        self._run(
            "Like post",
            lambda: (like_post(self._post_dialog()), self._log("Like action completed.")),
        )

    def comment(self):
        text = self.comment_text.get().strip()
        if not text:
            messagebox.showerror("Missing comment", "Enter comment text.")
            return
        self._run(
            "Comment on post",
            lambda: (comment_on_post(self._post_dialog(), text), self._log("Comment sent.")),
        )

    def share(self):
        text = self.share_text.get().strip()
        if not text:
            messagebox.showerror("Missing share text", "Enter text to add when sharing.")
            return
        self._run(
            "Share post",
            lambda: (share_post(self._post_dialog(), text), self._log("Share completed.")),
        )

    def _get_images(self):
        folder = self.image_dir.get().strip()
        if not folder or not os.path.isdir(folder):
            return []
        return [
            os.path.join(folder, name)
            for name in sorted(os.listdir(folder))
            if os.path.isfile(os.path.join(folder, name))
        ]

    def post_group(self):
        url = self.group_url.get().strip()
        content = self.group_content.get("1.0", "end").strip()
        if not url or not content:
            messagebox.showerror("Missing data", "Enter a group URL and post content.")
            return
        self._run(
            "Post to group",
            lambda: post_to_group(
                self.driver, url, content, self._get_images(), self._log
            )
        )

    def repost(self):
        links_file = self.group_links_file.get().strip()
        content_file = self.repost_content_file.get().strip()
        if not os.path.isfile(links_file) or not os.path.isfile(content_file):
            messagebox.showerror("Missing file", "Choose an existing links file and content file.")
            return
        with open(links_file, "r", encoding="utf-8") as file:
            links = [line.strip() for line in file if line.strip()]
        with open(content_file, "r", encoding="utf-8") as file:
            content = file.read()
        if not links or not content.strip():
            messagebox.showerror("Empty input", "The links file and content file must not be empty.")
            return
        self._run(
            f"Repost to {len(links)} groups",
            lambda: [
                self._post_repost_group(link, content, index, len(links))
                for index, link in enumerate(links, start=1)
            ]
        )

    def _post_repost_group(self, link, content, index, total):
        self._raise_if_cancelled()
        self._set_status(f"Reposting group {index}/{total}")
        self._log(f"Posting to group {index}/{total}: {link}")
        post_to_group(self.driver, link, content, self._get_images(), self._log)

    def _on_close(self):
        if self.verification_event:
            self.verification_event.set()
        self.close_browser()
        self.destroy()


if __name__ == "__main__":
    app = FacebookGui()
    app.mainloop()
