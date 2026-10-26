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
      repost.py
  requirements.txt
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

- Cookie or credential login, including a button to continue after manual verification/2FA.
- Opening a post URL and extracting its text.
- Reading a post and saving its visible details to a local SQLite database (`tools/facebook_group_repost/data/posts.sqlite3` by default). The database path is editable in the Post actions tab.
- Scraping a group member's posts, limited to the 10 newest posts or the last 30 days.
- Like, comment, and share actions.
- Posting text and all media files in a selected folder to one group.
- Reposting one content file and media folder to every group URL in a selected links file.
- Editing and saving the multi-group `content.txt` in the GUI, with photo previews and drag-and-drop for content, link, and image files.
- A live status indicator showing the active action, verification wait, completion, and errors.
- A Cancel task button for cooperative cancellation, including stopping before the next reposted group.

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
- `-g`, `--group_links_file`: group links list file
- `-c`, `--content_file`: post content file
- `--image_dir`: folder containing images to attach

Example:

```bash
python tools/facebook_group_repost/repost.py \
  --credential_file tools/facebook_group_repost/data/auth/facebook_credentials.txt \
  --cookies_file tools/facebook_group_repost/data/auth/facebook_cookies.json \
  --group_links_file "tools/facebook_group_repost/data/Group Links/test.txt" \
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
