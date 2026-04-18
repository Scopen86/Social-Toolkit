# Facebook Group Repost Tool

Repost content to multiple Facebook groups using Selenium.

## Project structure

- Shared automation library: `lib/facebook_engine.py`
- Tool entrypoint: `tools/facebook_group_repost/repost.py`
- Runtime data: `data/facebook_group_repost/`

## Run

From repository root:

```bash
python tools/facebook_group_repost/repost.py
```

Optional overrides:

```bash
python tools/facebook_group_repost/repost.py \
	--credential_file data/facebook_group_repost/facebook_credentials.txt \
	--cookies_file data/facebook_group_repost/facebook_cookies.json \
	--group_links_file data/facebook_group_repost/group_links.txt \
	--content_file data/facebook_group_repost/content.txt \
	--image_dir data/facebook_group_repost/Images
```
