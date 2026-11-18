# Social Toolkit

A Windows-focused Tkinter app plus CLI tools for Facebook group reposting, post reading, and Discord interactions.

Everything runs locally. Session cookies, credentials, media, and SQLite databases stay in `tools/facebook_group_repost/data/` and are ignored by Git.

## Quick start

```bash
pip install -r requirements.txt
```

Launch the GUI **without a terminal window** on Windows:

- Double-click `run_gui.vbs` in the project root, or
- Double-click `tools/social_toolkit_gui.pyw`.

Both use the Python no-console launcher (`pyw.exe` / `pythonw.exe`). You can also run it with a visible terminal:

```bash
python tools/social_toolkit_gui.py
```

Chrome is required for the Facebook actions. Selenium Manager resolves a compatible ChromeDriver automatically.

## Project layout

```text
Social-Toolkit/
├── run_gui.vbs                      # hidden-console GUI launcher
├── Facebook.html                    # saved Facebook groups page (local data)
├── requirements.txt
├── lib/
│   ├── facebook_engine.py           # Selenium actions shared by GUI and CLI
│   ├── group_classifier.py          # category taxonomy and rules
│   ├── groups_db.py                 # groups DB read/write helpers
│   └── upload_log.py                # persistent failed-upload log
└── tools/
    ├── social_toolkit_gui.py         # unified GUI entry point
    ├── social_toolkit_gui.pyw        # same entry point, no console
    ├── discord_interaction/
    │   └── discord_tab.py
    └── facebook_group_repost/
        ├── facebook_tab.py           # Facebook GUI tab
        ├── repost.py                 # CLI repost tool
        ├── extract_groups_to_sqlite.py
        ├── categorize_groups_from_posts.py
        ├── README.md
        └── data/                     # local runtime data (gitignored)
```

## GUI

The app opens on the **Facebook** tab. The **Discord** tab supports plain messages, configured slash-command interactions, and clicking enabled buttons found in recent messages.

The toolbar has **Start browser**, **Close browser**, **Login (cookies)**, **Save cookies**, and **Cancel task**. Actions are queued: starting another action while one is running adds it to the queue rather than blocking the UI. The activity log at the bottom shows progress and errors.

### Facebook tab

**Post actions**

- Open a post URL and extract its text.
- Save visible post details to `tools/facebook_group_repost/data/posts.db` (URL, post ID, message, author, timestamp, capture time, category). Re-reading a URL updates its row but keeps the assigned category.
- Scrape a group member's recent posts (10 newest or last 30 days).
- Like, comment, share, or post to a single group.
- Log in manually in Chrome, then click **Save cookies** so later runs reuse the session.

**Multi-group repost**

- Groups are loaded from `tools/facebook_group_repost/data/facebook_groups.db` and shown as a tree grouped by category, with a subcategory column.
- Filter by category, search by name or URL, and optionally show hidden groups.
- Select individual groups or whole categories; **Select all visible** and **Clear selection** help with bulk actions.
- **Copy link(s)** (or Ctrl+C on the tree) copies selected group URLs to the clipboard, one per line.
- **Move selected to** plus the subcategory dropdown (or the right-click menu) reclassifies groups. Changes are saved to both the database and `group_categories.json`, so future extraction keeps them. Collapsed categories stay collapsed after a move.
- **Remove from DB** deletes selected groups after confirmation and removes their saved category choices.
- **Add group by link**: paste a Facebook group URL and click **Fetch and add**. The app opens it in the logged-in Chrome session, reads the name, classifies it, and inserts or updates the row in the database.

**Media order**

The media area uses a Facebook-style numbered thumbnail grid:

- Click a tile to preview it in the side panel.
- Drag a tile onto another to reorder freely; dragging onto the `＋ Add` tile moves it to the end.
- Each tile has an **×** button to remove just that item; **Remove selected** and **Clear all** are also available.
- Add more media with **Add files** or by dropping files on the grid or preview. Videos show a summary instead of a rendered frame.

The displayed grid order is the order in which files are uploaded.

**Shutdown when done**

Enable **Shutdown PC when done** in the toolbar. When the task queue empties, the GUI schedules a Windows shutdown with a 60-second countdown. Cancel it during the countdown with:

```cmd
shutdown /a
```

**Failure log**

Failed uploads are appended to `tools/facebook_group_repost/data/upload_failures.log` with a timestamp, group name, URL, and error. The **Failure log** button in the repost tab opens it in the default text editor.

### Categories

Groups use eight commerce-focused categories:

- Laptops & MacBooks
- PC Parts
- PC Peripherals
- Phones & Mobile
- Cameras
- Audio
- General Market
- Other

PC Peripherals groups also carry a subcategory: **Mouse**, **Keyboard**, or **General Peripheral**.

## CLI repost

```bash
python tools/facebook_group_repost/repost.py --source db \
  --group_category "Laptops & MacBooks" \
  --content_file tools/facebook_group_repost/data/content.txt \
  --image_dir tools/facebook_group_repost/data/Images
```

Useful flags:

- `-l`, `--login`: force credential login instead of cookie login
- `--credential_file`, `--cookies_file`: override auth paths
- `--source`: `db` (default) or `file`
- `--groups_db`: path to the groups database
- `--group_category`, `--group_subcategory`, `--managed_only`: database filters
- `-g`, `--group_links_file`: URL list used with `--source file`
- `-c`, `--content_file`, `--image_dir`: post content and media

Failed uploads are also written to `data/upload_failures.log`.

## Group database tools

Both scripts live in `tools/facebook_group_repost/` and operate on `data/facebook_groups.db`.

```bash
# Rebuild the groups DB from the saved Facebook groups HTML page
python tools/facebook_group_repost/extract_groups_to_sqlite.py --auto

# Refresh the page from Chrome with saved cookies first
python tools/facebook_group_repost/extract_groups_to_sqlite.py --fetch --auto

# Refine uncertain categories by reading recent posts
python tools/facebook_group_repost/categorize_groups_from_posts.py --report
```

`extract_groups_to_sqlite.py` defaults to `Facebook.html` in the project root, applies saved choices from `data/group_categories.json`, and writes low-confidence review items to `data/group_category_review.json` with `--report`. `categorize_groups_from_posts.py` saves high-confidence results automatically and can print the category list with `--categories-only`.

## Data and privacy

These local files are gitignored and should not be committed: cookies, credentials, `Facebook.html`, local media, `content.txt`, `*.db`, and generated logs/reports. The live group database is `tools/facebook_group_repost/data/facebook_groups.db`; `posts.db` stores read posts.

## Requirements

See `requirements.txt`: Selenium, google-genai, Pillow, tkinterdnd2, BeautifulSoup4, and lxml.
