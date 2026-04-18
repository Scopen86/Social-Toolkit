# Social Toolkit

Python automation utilities for social platform workflows.

Current tool included:
- Facebook Group Repost automation using Selenium.

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
  data/
    facebook_group_repost/
      auth/
      Group Links/
      Images/
      content.txt
  lib/
    facebook_engine.py
  tools/
    facebook_group_repost/
      repost.py
  requirements.txt
```

## Facebook Group Repost

Run from the repository root:

```bash
python tools/facebook_group_repost/repost.py
```

### Useful flags

- `-l`, `--login`: force credential login instead of cookie login
- `--credential_file`: path to credentials file (default: `data/facebook_group_repost/auth/facebook_credentials.txt`)
- `--cookies_file`: path to cookie file (default: `data/facebook_group_repost/auth/facebook_cookies.json`)
- `-g`, `--group_links_file`: group links list file
- `-c`, `--content_file`: post content file
- `--image_dir`: folder containing images to attach

Example:

```bash
python tools/facebook_group_repost/repost.py \
  --credential_file data/facebook_group_repost/auth/facebook_credentials.txt \
  --cookies_file data/facebook_group_repost/auth/facebook_cookies.json \
  --group_links_file "data/facebook_group_repost/Group Links/test.txt" \
  --content_file data/facebook_group_repost/content.txt \
  --image_dir data/facebook_group_repost/Images
```

## Data and Security Notes

- Do not commit credentials, cookies, private group links, or local media.
- `.gitignore` is configured to ignore common sensitive/runtime files under `data/facebook_group_repost/`.
- Keep account and automation usage compliant with platform terms and local laws.

## Troubleshooting

- If browser launch fails, update Chrome and ChromeDriver.
- If login loops, run once with `--login` and complete verification manually to refresh cookies.
- If posting elements are not found, Facebook UI selectors may have changed and may need updates in `lib/facebook_engine.py`.