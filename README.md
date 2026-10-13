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

## Facebook GUI

Start the graphical interface from the repository root:

```bash
python tools/facebook_gui.py
```

The GUI provides:

- Cookie or credential login, including a button to continue after manual verification/2FA.
- Opening a post URL and extracting its text.
- Reading a post and saving its visible details to a local SQLite database (`tools/facebook_group_repost/data/posts.sqlite3` by default). The database path is editable in the Post actions tab.
- Like, comment, and share actions.
- Posting text and all media files in a selected folder to one group.
- Reposting one content file and media folder to every group URL in a selected links file.
- A live status indicator showing the active action, verification wait, completion, and errors.
- A Cancel task button for cooperative cancellation, including stopping before the next reposted group.

Start Chrome, log in, and keep the browser open while using the post or group tabs. Selenium Manager
will find a compatible ChromeDriver when supported by the installed Selenium version.

The post reader stores each post's URL, Facebook post ID (including IDs supplied through
`multi_permalinks`), message, visible author, absolute timestamp, and capture time in the
`posts` SQLite table. Facebook only exposes information rendered to the logged-in browser, so fields
unavailable in the page are left empty. Re-reading the same URL updates its row.

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
