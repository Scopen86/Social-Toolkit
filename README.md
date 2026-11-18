# Social Toolkit

Python automation utilities for social platform workflows.

Current tool included:
- Facebook Group Repost automation using Selenium.
- Tkinter GUI for Facebook login, post actions, group posting, and multi-group reposting.

## Requirements

- Windows, macOS, or Linux
- Python 3.10+
- Google Chrome installed
- Matching ChromeDriver available in your PATH (or Selenium Manager support)

## Installation

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

## Project Structure

```text
Social-Toolkit/
  lib/
    facebook_engine.py
  tools/
    facebook_group_repost/
      data/
        auth/
        Group Links/
        Images/
        content.txt
        facebook_groups.db
      repost.py
  requirements.txt
```

## Extracting Groups from Facebook

The script can fetch your groups page automatically. Make sure your login cookies are fresh (open
the GUI, click **Start browser**, log in manually, then **Save cookies**), then run:

```bash
python extract_groups_to_sqlite.py --fetch
```

It opens Chrome, logs in with the saved cookies, scrolls the groups page until all groups are
loaded, saves the page as `Facebook.html` in the project root, and then extracts the groups. If
Facebook asks for verification, complete it in the Chrome window; the script continues
automatically. Use `--fetch-only` to save the page without touching the database.

You can also fetch the page yourself: open `https://www.facebook.com/groups/joins/` in Chrome,
scroll until every group is loaded, save the page (`Ctrl+S`) as `Facebook.html`, then run:

```bash
python extract_groups_to_sqlite.py
```

The script classifies each group into one of six commerce-focused buckets:
**Laptops & MacBooks**, **PC Parts & Peripherals**, **Phones & Mobile**, **Cameras & Audio**,
**General Market**, or **Other**. It then walks through groups that have no saved category choice and asks you to
**keep** the suggestion (`Enter`), **change** it (`c`, then pick a category by number or type a
new one), or **keep all remaining** suggestions (`q`). Choices you change are stored in
`tools/facebook_group_repost/data/group_categories.json` and reused on later runs, so only new
groups need review. Add `--auto` to accept every automatic category without prompting, or
`--review-all` to review groups that already have saved choices. The results are written to
`tools/facebook_group_repost/data/facebook_groups.db`.

For extra accuracy, `categorize_groups_from_posts.py` opens each uncertain group, reads a few
recent posts, and refines the category from the post text. High-confidence results are saved;
low-confidence groups are prompted in the terminal or written to
`tools/facebook_group_repost/data/group_category_review.json` when run with `--report`:

```bash
python categorize_groups_from_posts.py --report
```

## Facebook Group Repost

Run from the repository root:

```bash
python tools/facebook_group_repost/repost.py
```

## Unified GUI

Start the combined Discord and Facebook interface from the repository root:

```bash
python tools/social_toolkit_gui.py
```

The combined interface has separate Discord and Facebook tabs and opens on Facebook by default.
The Facebook browser starts when you click **Start browser** in its tab. The Discord tab supports
plain messages, configurable slash command interactions, and clicking enabled buttons discovered on
recent messages from the configured application.

The GUI provides:

- Manual login in Chrome, then **Save cookies** to store that session. The toolbar shows when
  cookies were last saved, and **Login (cookies)** reuses them on later runs.
- Opening a post URL and extracting its text.
- Reading a post and saving its visible details to a local SQLite database (`tools/facebook_group_repost/data/posts.db` by default). The database path is editable in the Post actions tab.
- Scraping a group member's posts, limited to the 10 newest posts or the last 30 days.
- Like, comment, and share actions.
- Posting text and all media files in a selected folder to one group.
- Reposting one content file and media folder to groups selected from `facebook_groups.db`. The
  Multi-group repost tab loads the database, groups entries by category, and supports filtering,
  searching, and selecting whole categories. To add a group that is not in the database, paste its
  Facebook group link and click **Fetch and add**: the GUI opens the link with the logged-in Chrome
  session, reads the group name, classifies it, and inserts or updates the row in the database.
  Groups can be re-categorized in the UI with **Move selected to** or the right-click menu; the
  change is saved to both the database and the saved category choices.
- Editing and saving the multi-group `content.txt` in the GUI. The media section shows a numbered,
  thumbnail-backed upload-order list: click a row to preview it and drag rows or use the move
  buttons to reorder. Content, links, photos, and videos can also be added by drag-and-drop.
- A live status indicator showing the active action, queued task count, cookie saves, completion, and errors. Actions queue instead of blocking, so you can line up consecutive jobs.
- A Cancel task button for cooperative cancellation, clearing the queue and stopping before the next reposted group.

Start Chrome, log in, and keep the browser open while using the post or group tabs. Selenium Manager
will find a compatible ChromeDriver when supported by the installed Selenium version.

The post reader stores each post's URL, Facebook post ID (including IDs supplied through
`multi_permalinks`), message, visible author, absolute timestamp, and capture time in the
`posts` SQLite table, along with a category. New posts start as `Uncategorized`; categories can be
assigned from the message content. Facebook only exposes information rendered to the logged-in
browser, so fields unavailable in the page are left empty. Re-reading the same URL updates its row
while preserving an existing category.
Use the Group member URL field in the Post actions tab to start a user-post scrape. The selected range
is saved to the same `posts` table.

### Useful flags

- `-l`, `--login`: force credential login instead of cookie login
- `--credential_file`: path to credentials file (default: `tools/facebook_group_repost/data/auth/facebook_credentials.txt`)
- `--cookies_file`: path to cookie file (default: `tools/facebook_group_repost/data/auth/facebook_cookies.json`)
- `--source`: choose groups from `db` (default) or `file`
- `--groups_db`: path to the groups SQLite database (default: `tools/facebook_group_repost/data/facebook_groups.db`)
- `--group_category`: only include groups in this category
- `--group_subcategory`: only include groups in this subcategory
- `--managed_only`: only include groups you manage
- `-g`, `--group_links_file`: group links list file (used with `--source file`)
- `-c`, `--content_file`: post content file
- `--image_dir`: folder containing photos and videos to attach

Example:

```bash
python tools/facebook_group_repost/repost.py \
  --credential_file tools/facebook_group_repost/data/auth/facebook_credentials.txt \
  --cookies_file tools/facebook_group_repost/data/auth/facebook_cookies.json \
  --group_links_file "tools/facebook_group_repost/data/Group Links/test.txt" \
  --content_file tools/facebook_group_repost/data/content.txt \
  --image_dir tools/facebook_group_repost/data/Images
```

Repost to groups from the database, filtered by category:

```bash
python tools/facebook_group_repost/repost.py --source db \
  --group_category "Laptops & MacBooks" \
  --content_file tools/facebook_group_repost/data/content.txt \
  --image_dir tools/facebook_group_repost/data/Images
```

## Data and Security Notes

- Do not commit credentials, cookies, private group links, or local media.
- `.gitignore` is configured to ignore common sensitive/runtime files under `tools/facebook_group_repost/data/`.
- Keep account and automation usage compliant with platform terms and local laws.

## Troubleshooting

- If browser launch fails, update Chrome and ChromeDriver.
- If login loops, run once with `--login` and complete verification manually to refresh cookies.
- If posting elements are not found, Facebook UI selectors may have changed and may need updates in `lib/facebook_engine.py`.
