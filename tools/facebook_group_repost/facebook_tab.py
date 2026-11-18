"""Tkinter GUI for the Facebook Selenium automation library."""

import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from lib.group_classifier import classify_consolidated
from lib.groups_db import load_groups, upsert_group
from lib.facebook_engine import (
    comment_on_post,
    extract_post_details,
    get_dialog,
    like_post,
    login,
    post_to_group,
    save_cookies,
    scrape_user_group_posts,
    save_post_to_sqlite,
    share_post,
)


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
AUTH_DIR = os.path.join(DATA_DIR, "auth")

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff"
}
VIDEO_EXTENSIONS = {
    ".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".wmv", ".flv",
    ".3gp", ".3g2", ".mts", ".m2ts", ".vob", ".divx", ".f4v", ".ogv",
    ".mpeg", ".mpg",
}


class FacebookTab(ttk.Frame):
    def __init__(self, parent, *, auto_start=False):
        super().__init__(parent)

        self.driver = None
        self._starting_browser = False
        self.task_queue = queue.Queue()
        self.task_thread = None
        self.current_action = None
        self.log_queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.status_text = tk.StringVar(value="Ready")

        self.credential_file = tk.StringVar(
            value=os.path.join(AUTH_DIR, "facebook_credentials.txt")
        )
        self.cookies_file = tk.StringVar(
            value=os.path.join(AUTH_DIR, "facebook_cookies.json")
        )
        self.post_url = tk.StringVar()
        self.group_member_url = tk.StringVar()
        self.scrape_option = tk.StringVar(value="10 newest")
        self.posts_db = tk.StringVar(value=os.path.join(DATA_DIR, "posts.db"))
        self.comment_text = tk.StringVar()
        self.share_text = tk.StringVar()
        self.group_url = tk.StringVar()
        self.groups_db = tk.StringVar(
            value=os.path.join(DATA_DIR, "facebook_groups.db")
        )
        self.group_filter = tk.StringVar(value="All categories")
        self.group_search = tk.StringVar()
        self.show_hidden = tk.BooleanVar(value=False)
        self._db_groups = []
        self._tree_urls = {}
        self.image_dir = tk.StringVar(value=os.path.join(DATA_DIR, "Images"))
        self._media_paths = []
        self._preview_paths = []
        self._preview_index = 0
        self._preview_photo = None

        self._build_ui()
        self.after(100, self._drain_log_queue)
        if auto_start:
            self.after(100, self.start_browser)

    def _make_scrollable_page(self, notebook, text):
        """Create a vertically scrollable notebook page and return its content frame."""
        container = ttk.Frame(notebook)
        canvas = tk.Canvas(container, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas, padding=10)

        content.bind(
            "<Configure>",
            lambda event, c=canvas: c.configure(scrollregion=c.bbox("all")),
        )
        window = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event, c=canvas, w=window: c.itemconfigure(w, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event, c=canvas):
            if not c.winfo_exists():
                return
            bbox = c.bbox("all")
            if bbox and bbox[3] > c.winfo_height():
                c.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(_event, c=canvas, handler=_on_mousewheel):
            c.bind_all("<MouseWheel>", handler)

        def _unbind_wheel(_event, c=canvas):
            c.unbind_all("<MouseWheel>")

        container.bind("<Enter>", _bind_wheel)
        container.bind("<Leave>", _unbind_wheel)

        notebook.add(container, text=text)
        return content

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
            toolbar, text="Login (cookies)", command=self.login_facebook, state="disabled"
        )
        self.login_button.pack(side="left", padx=6)
        self.save_cookies_button = ttk.Button(
            toolbar, text="Save cookies", command=self.save_cookies_now, state="disabled"
        )
        self.save_cookies_button.pack(side="left")
        self.cancel_button = ttk.Button(
            toolbar, text="Cancel task", command=self.cancel_task, state="disabled"
        )
        self.cancel_button.pack(side="left", padx=6)
        ttk.Label(toolbar, text="Status:").pack(side="left", padx=(18, 4))
        self.status_label = ttk.Label(toolbar, textvariable=self.status_text)
        self.status_label.pack(side="left")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.post_tab = self._make_scrollable_page(notebook, "Post actions")
        self.group_tab = self._make_scrollable_page(notebook, "Group post")
        self.repost_tab = self._make_scrollable_page(notebook, "Multi-group repost")

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
        ttk.Label(
            frame,
            text="Log in manually in Chrome, then click Save cookies. "
            "Login (cookies) reuses the saved session.",
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
        self._path_row(frame, 6, "Posts database:", self.posts_db)
        ttk.Label(frame, text="Group member URL:").grid(row=7, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.group_member_url, width=80).grid(
            row=7, column=1, columnspan=3, sticky="ew", padx=6
        )
        ttk.Label(frame, text="Scrape:").grid(row=8, column=0, sticky="w")
        ttk.Combobox(
            frame,
            textvariable=self.scrape_option,
            values=("10 newest", "last 30 days"),
            state="readonly",
            width=18,
        ).grid(row=8, column=1, sticky="w", padx=6, pady=8)
        ttk.Button(frame, text="Scrape user posts", command=self.scrape_user_posts).grid(
            row=8, column=2, sticky="w", pady=8
        )
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
        self._path_row(frame, 2, "Media folder:", self.image_dir, choose_directory=True)
        ttk.Button(frame, text="Post to group", command=self.post_group).grid(
            row=3, column=1, sticky="w", pady=8
        )
        frame.columnconfigure(1, weight=1)

    def _build_repost(self, parent):
        frame = ttk.LabelFrame(parent, text="Repost to multiple groups", padding=8)
        frame.pack(fill="both", expand=True)

        links_frame = ttk.LabelFrame(frame, text="Groups from database", padding=6)
        links_frame.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=3, pady=4)

        self._path_row(links_frame, 0, "Groups database:", self.groups_db)
        ttk.Button(links_frame, text="Load", command=self._load_db_groups).grid(
            row=0, column=3, padx=(6, 0), sticky="w"
        )

        filters = ttk.Frame(links_frame)
        filters.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Label(filters, text="Category:").pack(side="left")
        self.group_category = ttk.Combobox(
            filters, textvariable=self.group_filter, state="readonly", width=24
        )
        self.group_category.pack(side="left", padx=6)
        self.group_category.bind(
            "<<ComboboxSelected>>", lambda event: self._refresh_group_tree()
        )
        ttk.Label(filters, text="Search:").pack(side="left", padx=(10, 0))
        ttk.Entry(filters, textvariable=self.group_search, width=26).pack(
            side="left", padx=6
        )
        self.group_search.trace_add("write", lambda *_: self._refresh_group_tree())
        ttk.Checkbutton(
            filters,
            text="Show hidden",
            variable=self.show_hidden,
            command=self._refresh_group_tree,
        ).pack(side="left", padx=(10, 0))

        tree_frame = ttk.Frame(links_frame)
        tree_frame.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=(6, 0))
        self.group_tree = ttk.Treeview(
            tree_frame,
            columns=("category", "url"),
            show="tree headings",
            selectmode="extended",
            height=14,
        )
        self.group_tree.heading("#0", text="Group / category")
        self.group_tree.heading("category", text="Category")
        self.group_tree.heading("url", text="URL")
        self.group_tree.column("#0", width=320, minwidth=200, stretch=True)
        self.group_tree.column("category", width=160, minwidth=100, stretch=False)
        self.group_tree.column("url", width=300, minwidth=150, stretch=True)
        self.group_tree.tag_configure(
            "category", font=("Segoe UI", 9, "bold")
        )
        self.group_tree.tag_configure("favorite", foreground="#9a6700")
        self.group_tree.tag_configure("hidden", foreground="#888888")
        tree_scroll = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.group_tree.yview
        )
        self.group_tree.configure(yscrollcommand=tree_scroll.set)
        self.group_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.group_tree.bind(
            "<<TreeviewSelect>>", lambda event: self._update_group_count()
        )
        self.group_tree.bind("<MouseWheel>", self._on_tree_mousewheel)

        actions = ttk.Frame(links_frame)
        actions.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Button(
            actions, text="Select all visible", command=self._select_all_visible
        ).pack(side="left")
        ttk.Button(
            actions, text="Clear selection", command=self._clear_tree_selection
        ).pack(side="left", padx=6)
        ttk.Button(actions, text="Expand all", command=self._expand_all).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(actions, text="Collapse all", command=self._collapse_all).pack(
            side="left", padx=(6, 0)
        )

        add_row = ttk.Frame(links_frame)
        add_row.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Label(add_row, text="Add group by link:").pack(side="left")
        self.group_link_input = tk.StringVar()
        group_link_entry = ttk.Entry(add_row, textvariable=self.group_link_input)
        group_link_entry.pack(side="left", fill="x", expand=True, padx=6)
        group_link_entry.bind("<Return>", lambda event: self.add_group_link())
        ttk.Button(add_row, text="Fetch and add", command=self.add_group_link).pack(
            side="left"
        )

        self.group_count_text = tk.StringVar(value="0 selected")
        ttk.Label(links_frame, textvariable=self.group_count_text).grid(
            row=5, column=0, columnspan=4, sticky="w", pady=(6, 0)
        )
        ttk.Label(
            links_frame,
            text="Select one or more groups. Added links are fetched from Facebook and stored in the database.",
            foreground="#555555",
        ).grid(row=6, column=0, columnspan=4, sticky="w", pady=(2, 0))

        links_frame.columnconfigure(1, weight=1)
        links_frame.rowconfigure(2, weight=1)

        self.repost_content_file = tk.StringVar(value=os.path.join(DATA_DIR, "content.txt"))
        self._path_row(frame, 1, "Content file:", self.repost_content_file, start_column=0)
        content_frame = ttk.LabelFrame(frame, text="Post content", padding=6)
        content_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=3, pady=(8, 4))
        self.repost_content = tk.Text(content_frame, height=5, wrap="word")
        self.repost_content.pack(side="left", fill="both", expand=True)
        content_buttons = ttk.Frame(content_frame)
        content_buttons.pack(side="right", fill="y", padx=(8, 0))
        ttk.Button(content_buttons, text="Load file", command=self.load_content_file).pack(
            fill="x", pady=(0, 4)
        )
        ttk.Button(content_buttons, text="Save file", command=self.save_content_file).pack(
            fill="x"
        )

        self._path_row(frame, 3, "Media folder:", self.image_dir, choose_directory=True)
        preview_frame = ttk.LabelFrame(
            frame, text="Media preview · drag photos or videos here", padding=6
        )
        preview_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=3, pady=4)
        self.photo_preview = ttk.Label(
            preview_frame,
            text="No media selected. Choose a folder or drop photos and videos here.",
            anchor="center",
            relief="groove",
            width=60,
        )
        self.photo_preview.pack(fill="both", expand=True, ipady=30)
        self._register_drop_target(self.photo_preview, self._drop_media)
        preview_controls = ttk.Frame(preview_frame)
        preview_controls.pack(fill="x", pady=(5, 0))
        self.preview_previous = ttk.Button(
            preview_controls, text="Previous", command=lambda: self._step_preview(-1), state="disabled"
        )
        self.preview_previous.pack(side="left")
        self.preview_counter = ttk.Label(preview_controls, text="0 / 0")
        self.preview_counter.pack(side="left", padx=10)
        self.preview_next = ttk.Button(
            preview_controls, text="Next", command=lambda: self._step_preview(1), state="disabled"
        )
        self.preview_next.pack(side="left")
        ttk.Button(preview_controls, text="Add files", command=self.add_media_files).pack(
            side="left", padx=(12, 0)
        )
        ttk.Button(preview_controls, text="Move up", command=lambda: self._move_preview_media(-1)).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(preview_controls, text="Move down", command=lambda: self._move_preview_media(1)).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(preview_controls, text="Remove", command=self._remove_preview_media).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(preview_controls, text="Clear", command=self._clear_media).pack(
            side="left", padx=(6, 0)
        )
        self.preview_source = ttk.Label(preview_controls, text="")
        self.preview_source.pack(side="right")

        ttk.Button(frame, text="Repost to selected groups", command=self.repost).grid(
            row=5, column=1, sticky="w", pady=8
        )
        frame.columnconfigure(1, weight=1)
        self._load_db_groups()
        self._load_media_from_folder(self.image_dir.get().strip())
        self.load_content_file(show_errors=False)

    @staticmethod
    def _normalize_group_link(value):
        """Return ``value`` as an absolute Facebook URL, or an empty string."""
        link = (value or "").strip().strip("<>\"'")
        if not link:
            return ""
        if link.startswith("//"):
            link = "https:" + link
        elif "://" not in link:
            link = "https://" + link
        return link.rstrip("/")

    @staticmethod
    def _group_slug_from_link(link):
        """Extract the group slug from a Facebook group URL."""
        match = re.search(
            r"(?:facebook\.com|fb\.com)/groups/([^/?#]+)", link or "", re.IGNORECASE
        )
        return match.group(1) if match else ""

    def _load_db_groups(self):
        path = self.groups_db.get().strip()
        try:
            groups = load_groups(path)
        except Exception as exc:
            self._db_groups = []
            self._log(f"Could not load groups database: {exc}")
        else:
            self._db_groups = groups
            self._log(f"Loaded {len(groups)} group(s) from {path}")
        self._refresh_category_filter()
        self._refresh_group_tree()

    def _refresh_category_filter(self):
        if not hasattr(self, "group_category"):
            return
        categories = sorted(
            {(row.get("category") or "Other") for row in self._db_groups},
            key=str.casefold,
        )
        values = ["All categories"] + categories
        self.group_category["values"] = values
        if self.group_filter.get() not in values:
            self.group_filter.set("All categories")

    def _refresh_group_tree(self):
        if not hasattr(self, "group_tree"):
            return
        for item in self.group_tree.get_children(""):
            self.group_tree.delete(item)
        self._tree_urls = {}
        selected_category = self.group_filter.get()
        query = self.group_search.get().strip().casefold()
        show_hidden = self.show_hidden.get()

        groups_by_category = {}
        for row in self._db_groups:
            if not show_hidden and row.get("is_hidden"):
                continue
            category = row.get("category") or "Other"
            if (
                selected_category
                and selected_category != "All categories"
                and category != selected_category
            ):
                continue
            name = row.get("name") or row.get("group_slug") or ""
            url = row.get("url") or ""
            if query and query not in f"{name} {url}".casefold():
                continue
            groups_by_category.setdefault(category, []).append(row)

        for category in sorted(groups_by_category, key=str.casefold):
            rows = groups_by_category[category]
            parent = self.group_tree.insert(
                "",
                "end",
                text=f"{category} ({len(rows)})",
                open=True,
                tags=("category",),
            )
            for row in rows:
                name = row.get("name") or row.get("group_slug") or ""
                url = row.get("url") or ""
                favorite = bool(row.get("is_favorite"))
                hidden = bool(row.get("is_hidden"))
                tags = []
                if favorite:
                    tags.append("favorite")
                if hidden:
                    tags.append("hidden")
                display = ("★ " if favorite else "") + name
                item = self.group_tree.insert(
                    parent,
                    "end",
                    text=display,
                    values=(category, url),
                    tags=tuple(tags),
                )
                self._tree_urls[item] = url
        self._update_group_count()

    def _selected_group_urls(self):
        if not hasattr(self, "group_tree"):
            return []
        urls = []
        seen = set()
        for item in self.group_tree.selection():
            children = self.group_tree.get_children(item)
            for child in children or [item]:
                url = self._tree_urls.get(child) or ""
                key = url.casefold()
                if url and key not in seen:
                    seen.add(key)
                    urls.append(url)
        return urls

    def _update_group_count(self):
        if not hasattr(self, "group_count_text"):
            return
        selected = len(self._selected_group_urls())
        total = len(self._db_groups)
        self.group_count_text.set(
            f"{selected} selected · {total} group{'s' if total != 1 else ''} in database"
        )

    def _select_all_visible(self):
        items = []
        for parent in self.group_tree.get_children(""):
            items.extend(self.group_tree.get_children(parent))
        if items:
            self.group_tree.selection_set(*items)

    def _clear_tree_selection(self):
        selection = self.group_tree.selection()
        if selection:
            self.group_tree.selection_remove(*selection)

    def _expand_all(self):
        for parent in self.group_tree.get_children(""):
            self.group_tree.item(parent, open=True)

    def _collapse_all(self):
        for parent in self.group_tree.get_children(""):
            self.group_tree.item(parent, open=False)

    def _on_tree_mousewheel(self, event):
        self.group_tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _select_tree_url(self, url):
        target = (url or "").casefold()
        for item, item_url in self._tree_urls.items():
            if item_url.casefold() != target:
                continue
            parent = self.group_tree.parent(item)
            if parent:
                self.group_tree.item(parent, open=True)
            self.group_tree.selection_set(item)
            self.group_tree.see(item)
            self.group_tree.focus(item)
            break

    def add_group_link(self):
        raw = self.group_link_input.get().strip()
        if not raw:
            messagebox.showinfo("Add group", "Paste a Facebook group link first.")
            return
        link = self._normalize_group_link(raw)
        slug = self._group_slug_from_link(link)
        if not slug:
            messagebox.showerror(
                "Invalid group link",
                "Expected a link like https://www.facebook.com/groups/<group>.",
            )
            return
        url = f"https://www.facebook.com/groups/{slug}/"
        db_path = self.groups_db.get().strip()
        started = self._run(
            f"Add group {slug}",
            lambda: self._add_group_link_task(url, slug, db_path),
            success_status=self._on_group_added,
        )
        if started:
            self.group_link_input.set("")

    def _add_group_link_task(self, url, slug, db_path):
        self._raise_if_cancelled()
        self.driver.get(url)
        name = self._wait_for_group_name(slug)
        self._raise_if_cancelled()
        category = classify_consolidated(slug, name)[0]
        _group_id, created = upsert_group(
            db_path,
            slug=slug,
            name=name,
            url=url,
            category=category,
        )
        self._log(
            f"{'Added' if created else 'Updated'} group in database: "
            f"{name} ({category})"
        )
        return {"url": url, "name": name, "created": created}

    def _wait_for_group_name(self, slug):
        from selenium.webdriver.common.by import By

        deadline = time.time() + 20
        while time.time() < deadline:
            self._raise_if_cancelled()
            cleaned = self._clean_group_name(self.driver.title)
            if cleaned:
                return cleaned
            try:
                for heading in self.driver.find_elements(By.CSS_SELECTOR, "h1"):
                    cleaned = self._clean_group_name(heading.text)
                    if cleaned:
                        return cleaned
            except Exception:
                pass
            try:
                meta = self.driver.find_element(
                    By.CSS_SELECTOR, 'meta[property="og:title"]'
                )
                cleaned = self._clean_group_name(meta.get_attribute("content") or "")
                if cleaned:
                    return cleaned
            except Exception:
                pass
            time.sleep(0.5)
        raise RuntimeError(
            "Could not read the group name. Make sure the link opens a group "
            "you can access and that Facebook is logged in."
        )

    @staticmethod
    def _clean_group_name(value):
        name = re.sub(r"^\(\d+\+?\)\s*", "", (value or "").strip())
        for suffix in (" | Facebook", " - Facebook", " | Meta", " - Meta"):
            if name.endswith(suffix):
                name = name[: -len(suffix)].strip()
        lowered = name.casefold()
        if "log into facebook" in lowered or "đăng nhập facebook" in lowered:
            raise RuntimeError(
                "Facebook is not logged in. Log in first, then add the group link."
            )
        if lowered in {
            "",
            "facebook",
            "log in to facebook",
        }:
            return ""
        return name

    def _on_group_added(self, result):
        self.log_queue.put(("groups_changed", result.get("url", "")))
        verb = "Added" if result.get("created") else "Updated"
        return f"{verb} group: {result.get('name', '')}"

    def _path_row(
        self, parent, row, label, variable, choose_directory=False, start_column=0
    ):
        label_widget = ttk.Label(parent, text=label)
        label_widget.grid(row=row, column=start_column, sticky="w", pady=3)
        entry = ttk.Entry(parent, textvariable=variable, width=72)
        entry.grid(
            row=row, column=start_column + 1, sticky="ew", padx=6, pady=3
        )
        self._register_drop_target(
            entry, lambda event: self._drop_path(event, variable, choose_directory)
        )
        browse_button = ttk.Button(
            parent,
            text="Browse",
            command=lambda: self._browse(variable, choose_directory),
        )
        browse_button.grid(row=row, column=start_column + 2, sticky="w", pady=3)
        return label_widget, entry, browse_button

    def _browse(self, variable, choose_directory):
        path = (
            filedialog.askdirectory()
            if choose_directory
            else filedialog.askopenfilename()
        )
        if path:
            variable.set(path)
            if variable is self.image_dir:
                self._load_media_from_folder(path)
            elif variable is getattr(self, "repost_content_file", None):
                self.load_content_file(show_errors=True)

    def _register_drop_target(self, widget, handler):
        if hasattr(widget, "drop_target_register"):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", handler)

    def _drop_path(self, event, variable, choose_directory):
        paths = [str(path) for path in self.tk.splitlist(event.data)]
        if not paths:
            return "copy"
        path = paths[0]
        if variable is self.image_dir:
            if os.path.isfile(path) and self._is_media(path):
                self._drop_media(event)
                return "copy"
            if os.path.isdir(path):
                variable.set(path)
                self._load_media_from_folder(path)
        else:
            variable.set(path)
            if variable is getattr(self, "repost_content_file", None):
                self.load_content_file(show_errors=True)
        return "copy"

    @staticmethod
    def _is_image(path):
        return os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS

    @staticmethod
    def _is_video(path):
        return os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS

    @classmethod
    def _is_media(cls, path):
        return cls._is_image(path) or cls._is_video(path)

    @staticmethod
    def _format_size(size_bytes):
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.0f} KB"
        return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _folder_media_paths(self, folder):
        if not folder or not os.path.isdir(folder):
            return []
        return [
            os.path.join(folder, name)
            for name in sorted(os.listdir(folder))
            if os.path.isfile(os.path.join(folder, name)) and self._is_media(name)
        ]

    def _load_media_from_folder(self, folder):
        self._media_paths = self._folder_media_paths(folder)
        self._refresh_media_preview()

    def _append_media_paths(self, paths):
        existing = {os.path.normcase(os.path.abspath(p)) for p in self._media_paths}
        added = False
        for path in paths:
            if not (os.path.isfile(path) and self._is_media(path)):
                continue
            key = os.path.normcase(os.path.abspath(path))
            if key in existing:
                continue
            self._media_paths.append(path)
            existing.add(key)
            added = True
        if added:
            self._refresh_media_preview(keep_index=True)
        return added

    def add_media_files(self):
        paths = filedialog.askopenfilenames(
            title="Select photos or videos",
            filetypes=[
                ("Media files", "*.jpg *.jpeg *.png *.gif *.bmp *.webp *.tif *.tiff *.mp4 *.m4v *.mov *.webm *.mkv *.avi *.wmv *.flv *.3gp *.3g2 *.mts *.m2ts *.vob *.divx *.f4v *.ogv *.mpeg *.mpg"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return
        selected = [str(path) for path in paths if self._is_media(path)]
        if not selected:
            return
        self.image_dir.set(os.path.dirname(selected[0]))
        self._append_media_paths(selected)

    def _drop_media(self, event):
        paths = [str(path) for path in self.tk.splitlist(event.data)]
        directories = [path for path in paths if os.path.isdir(path)]
        media_paths = [
            path for path in paths if os.path.isfile(path) and self._is_media(path)
        ]
        if media_paths:
            self.image_dir.set(os.path.dirname(media_paths[0]))
            if not self._append_media_paths(media_paths):
                self._refresh_media_preview(keep_index=True)
        elif directories:
            self.image_dir.set(directories[0])
            self._load_media_from_folder(directories[0])
        return "copy"

    def _move_preview_media(self, direction):
        if not self._media_paths:
            return
        index = self._preview_index
        new_index = index + direction
        if new_index < 0 or new_index >= len(self._media_paths):
            return
        self._media_paths[index], self._media_paths[new_index] = (
            self._media_paths[new_index],
            self._media_paths[index],
        )
        self._preview_index = new_index
        self._refresh_media_preview(keep_index=True)

    def _remove_preview_media(self):
        if not self._media_paths or self._preview_index >= len(self._media_paths):
            return
        del self._media_paths[self._preview_index]
        if self._preview_index >= len(self._media_paths):
            self._preview_index = max(0, len(self._media_paths) - 1)
        self._refresh_media_preview(keep_index=True)

    def _clear_media(self):
        self._media_paths = []
        self._refresh_media_preview()

    def _refresh_media_preview(self, paths=None, keep_index=False):
        if not hasattr(self, "photo_preview"):
            return
        if paths is not None:
            self._media_paths = list(paths)
        # Keep list in sync but show only existing files
        self._media_paths = [p for p in self._media_paths if os.path.isfile(p)]
        self._preview_paths = list(self._media_paths)
        if not keep_index:
            self._preview_index = 0
        elif self._preview_paths:
            self._preview_index = min(self._preview_index, len(self._preview_paths) - 1)
        else:
            self._preview_index = 0
        self._show_preview_media()

    def _show_preview_media(self):
        count = len(self._preview_paths)
        if not count:
            self._preview_photo = None
            self.photo_preview.configure(
                image="",
                text="No media selected. Choose a folder or drop photos and videos here.",
            )
            self.preview_counter.configure(text="0 / 0")
            self.preview_source.configure(text="")
            self.preview_previous.configure(state="disabled")
            self.preview_next.configure(state="disabled")
            return
        self._preview_index = max(0, min(self._preview_index, count - 1))
        path = self._preview_paths[self._preview_index]
        name = os.path.basename(path)
        if self._is_video(path):
            self._preview_photo = None
            size = self._format_size(os.path.getsize(path))
            self.photo_preview.configure(
                image="",
                text=(
                    f"🎬 {name}\n"
                    f"Video · {size}\n"
                    "It will be uploaded with the post."
                ),
            )
            self.preview_source.configure(text=f"{name} (video)")
        else:
            try:
                with Image.open(path) as image:
                    image.thumbnail((640, 260), Image.Resampling.LANCZOS)
                    self._preview_photo = ImageTk.PhotoImage(image.copy())
                self.photo_preview.configure(image=self._preview_photo, text="")
                self.preview_source.configure(text=name)
            except Exception as exc:
                self._preview_photo = None
                self.photo_preview.configure(
                    image="", text=f"Could not preview {name}: {exc}"
                )
        self.preview_counter.configure(text=f"{self._preview_index + 1} / {count}")
        self.preview_previous.configure(state="normal" if count > 1 else "disabled")
        self.preview_next.configure(state="normal" if count > 1 else "disabled")

    def _step_preview(self, step):
        if self._preview_paths:
            self._preview_index = (self._preview_index + step) % len(self._preview_paths)
            self._show_preview_media()

    def load_content_file(self, show_errors=True):
        path = self.repost_content_file.get().strip()
        if not path or not os.path.isfile(path):
            if show_errors:
                messagebox.showerror("Content file not found", f"Choose an existing content file:\n{path}")
            return
        try:
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
            self.repost_content.delete("1.0", "end")
            self.repost_content.insert("1.0", content)
            self._log(f"Loaded post content from {path}")
        except OSError as exc:
            if show_errors:
                messagebox.showerror("Could not load content", str(exc))

    def save_content_file(self):
        path = self.repost_content_file.get().strip()
        if not path:
            messagebox.showerror("Content file missing", "Choose a content file path first.")
            return False
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as file:
                file.write(self.repost_content.get("1.0", "end-1c"))
            self._log(f"Saved post content to {path}")
            self._set_status("Content saved")
            return True
        except OSError as exc:
            messagebox.showerror("Could not save content", str(exc))
            return False

    def _run(self, action, function, *args, success_status=None):
        if not self.driver:
            if self._starting_browser:
                messagebox.showinfo(
                    "Browser starting",
                    "Chrome is still starting. Try again in a moment.",
                )
            else:
                messagebox.showerror("Browser not started", "Click Start browser first.")
            return False
        self.task_queue.put((action, function, args, success_status))
        pending = self.task_queue.qsize()
        if self.task_thread and self.task_thread.is_alive():
            self._log(f"Queued: {action}")
            self._set_status(f"Queued: {action} ({pending} waiting)")
        else:
            self._set_status(f"Running: {action}")
            self.task_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.task_thread.start()
        return True

    def _drain_task_queue(self):
        dropped = 0
        while True:
            try:
                self.task_queue.get_nowait()
            except queue.Empty:
                break
            else:
                self.task_queue.task_done()
                dropped += 1
        return dropped

    def _worker_loop(self):
        while True:
            task = self.task_queue.get()
            try:
                if task is None:
                    return
                action, function, args, success_status = task
                self.current_action = action
                self.cancel_event.clear()
                self._set_cancel_state(True)
                self._set_status(f"Running: {action}")
                self._log(f"Starting: {action}")
                try:
                    result = function(*args)
                    if self.cancel_event.is_set():
                        self._log("Task cancelled.")
                        self._set_status("Cancelled")
                    elif callable(success_status):
                        self._set_status(success_status(result))
                    else:
                        self._set_status(success_status or "Completed")
                except Exception as exc:
                    if self.cancel_event.is_set():
                        self._log("Task cancelled.")
                        self._set_status("Cancelled")
                    else:
                        self._log(f"ERROR: {exc}")
                        self._set_status(f"Failed: {exc}")
            finally:
                self.current_action = None
                self.task_queue.task_done()
                remaining = self.task_queue.qsize()
                if remaining:
                    self._set_status(f"Queued: {remaining} task(s) waiting")
                else:
                    self._set_cancel_state(False)

    def _cancelled(self):
        return self.cancel_event.is_set()

    def _raise_if_cancelled(self):
        if self._cancelled():
            raise RuntimeError("Task cancelled by user.")

    def cancel_task(self):
        pending = self.task_queue.qsize()
        if not self.current_action and not pending:
            return
        self.cancel_event.set()
        dropped = self._drain_task_queue()
        self._set_status("Cancelling...")
        self._log("Cancellation requested. The current browser step will finish safely.")
        if dropped:
            self._log(f"Removed {dropped} queued task(s).")

    def _log(self, message):
        self.log_queue.put(("log", str(message)))

    def _set_status(self, message):
        self.log_queue.put(("status", str(message)))

    def _set_cancel_state(self, enabled):
        self.log_queue.put(("cancel", "normal" if enabled else "disabled"))

    def _drain_log_queue(self):
        while not self.log_queue.empty():
            message_type, message = self.log_queue.get_nowait()
            if message_type == "status":
                self.status_text.set(message)
            elif message_type == "cancel":
                self.cancel_button.configure(state=message)
            elif message_type == "browser_started":
                self._browser_started(message)
            elif message_type == "browser_start_error":
                self._browser_start_failed(message)
            elif message_type == "groups_changed":
                self.group_filter.set("All categories")
                self.group_search.set("")
                self._load_db_groups()
                self._select_tree_url(message)
            else:
                self.log_text.configure(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        self.after(100, self._drain_log_queue)

    def _browser_started(self, driver):
        """Finish startup on the Tk thread once Chrome is ready."""
        self.driver = driver
        self._starting_browser = False
        self.close_button.configure(state="normal")
        self.login_button.configure(state="normal")
        self.save_cookies_button.configure(state="normal")
        self._log("Chrome browser started.")
        self._set_status("Browser ready")
        self.login_facebook()

    def _browser_start_failed(self, error):
        self._starting_browser = False
        self.start_button.configure(state="normal")
        self._log(f"ERROR: Could not start browser: {error}")
        self._set_status("Browser start failed")
        messagebox.showerror("Browser error", error)

    def start_browser(self):
        """Launch Chrome in the background so the window stays responsive."""
        if self._starting_browser or self.driver:
            return
        self._starting_browser = True
        self.start_button.configure(state="disabled")
        self._log("Launching Chrome...")
        self._set_status("Starting browser...")
        threading.Thread(target=self._launch_browser, daemon=True).start()

    def _launch_browser(self):
        try:
            options = Options()
            driver = webdriver.Chrome(options=options)
            driver.maximize_window()
        except Exception as exc:
            self.log_queue.put(("browser_start_error", str(exc)))
            return
        self.log_queue.put(("browser_started", driver))

    def close_browser(self):
        self.cancel_event.set()
        self._drain_task_queue()
        if self.driver:
            self.driver.quit()
            self.driver = None
        self.start_button.configure(state="normal")
        self.close_button.configure(state="disabled")
        self.login_button.configure(state="disabled")
        self.save_cookies_button.configure(state="disabled")
        self._log("Browser closed.")
        self._set_status("Browser closed")

    def login_facebook(self):
        credentials = self.credential_file.get()
        cookies = self.cookies_file.get()
        self._run(
            "Facebook cookie login",
            lambda: login(
                self.driver,
                self._log,
                True,
                credentials,
                cookies,
                None,
                False,
            ),
            success_status="Cookie login finished",
        )

    def _save_cookies_task(self, cookies_path):
        save_cookies(self.driver, cookies_path, self._log)
        return time.strftime("%H:%M:%S")

    def save_cookies_now(self):
        cookies_path = self.cookies_file.get().strip()
        self._run(
            "Save cookies",
            self._save_cookies_task,
            cookies_path,
            success_status=lambda stamp: f"Cookies saved at {stamp}",
        )

    def _post_dialog(self, url):
        self._raise_if_cancelled()
        if not url:
            raise ValueError("Enter a Facebook post URL.")
        dialog = get_dialog(self.driver, url, self._log)
        if dialog is None:
            raise RuntimeError("Post dialog was not found.")
        return dialog

    def read_post(self):
        url = self.post_url.get().strip()
        posts_db = self.posts_db.get().strip()
        self._run("Read and save post", self._read_and_save_post, url, posts_db)

    def scrape_user_posts(self):
        url = self.group_member_url.get().strip()
        if not url:
            messagebox.showerror("Missing URL", "Enter a Facebook group member URL.")
            return
        self._run(
            "Scrape group member posts",
            scrape_user_group_posts,
            self.driver,
            url,
            self.scrape_option.get(),
            self.posts_db.get().strip(),
            self._log,
        )

    def _read_and_save_post(self, url, posts_db):
        post = extract_post_details(self._post_dialog(url), url)
        save_post_to_sqlite(post, posts_db)
        self._log("Post text:\n" + post["message"])
        self._log(f"Saved post {post.get('post_id') or url} to {posts_db}")

    def like(self):
        url = self.post_url.get().strip()
        self._run(
            "Like post",
            lambda: (like_post(self._post_dialog(url)), self._log("Like action completed.")),
        )

    def comment(self):
        url = self.post_url.get().strip()
        text = self.comment_text.get().strip()
        if not text:
            messagebox.showerror("Missing comment", "Enter comment text.")
            return
        self._run(
            "Comment on post",
            lambda: (comment_on_post(self._post_dialog(url), text), self._log("Comment sent.")),
        )

    def share(self):
        url = self.post_url.get().strip()
        text = self.share_text.get().strip()
        if not text:
            messagebox.showerror("Missing share text", "Enter text to add when sharing.")
            return
        self._run(
            "Share post",
            lambda: (share_post(self._post_dialog(url), text), self._log("Share completed.")),
        )

    def _get_media(self):
        return [path for path in self._media_paths if os.path.isfile(path)]

    def post_group(self):
        url = self.group_url.get().strip()
        content = self.group_content.get("1.0", "end").strip()
        if not url or not content:
            messagebox.showerror("Missing data", "Enter a group URL and post content.")
            return
        media = self._get_media()
        self._run(
            "Post to group",
            lambda: post_to_group(
                self.driver, url, content, media, self._log
            ),
            success_status="Post finished",
        )

    def repost(self):
        links = self._selected_group_urls()
        if not links:
            messagebox.showerror(
                "No groups",
                "Select at least one group from the database first.",
            )
            return
        source = f"{len(links)} selected group{'s' if len(links) != 1 else ''}"

        content = self.repost_content.get("1.0", "end-1c")
        if not links or not content.strip():
            messagebox.showerror("Empty input", "The group selection and post content must not be empty.")
            return
        if not self.save_content_file():
            return
        media = self._get_media()
        self._run(
            f"Repost to {source}",
            lambda: self._repost_all_groups(links, content, media),
            success_status=f"Repost finished ({source})",
        )

    def _repost_all_groups(self, links, content, media):
        total = len(links)
        successes = 0
        failures = 0
        for index, link in enumerate(links, start=1):
            self._raise_if_cancelled()
            self._set_status(f"Reposting group {index}/{total}")
            self._log(f"Posting to group {index}/{total}: {link}")
            try:
                post_to_group(self.driver, link, content, media, self._log)
                successes += 1
            except Exception as exc:
                failures += 1
                self._log(f"ERROR posting to {link}: {exc}")
                continue
        self._log(
            f"Repost complete: {successes} succeeded, {failures} failed of {total}."
        )

    def shutdown(self):
        self.cancel_event.set()
        self.close_browser()