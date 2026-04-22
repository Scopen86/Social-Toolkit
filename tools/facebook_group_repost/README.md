# Facebook Group Repost Tool

Repost content to multiple Facebook groups using Selenium.

## Project structure

- Shared automation library: `lib/facebook_engine.py`
- Tool entrypoint: `tools/facebook_group_repost/repost.py`
- Runtime data: `tools/facebook_group_repost/data/`

## Run

From repository root:

```bash
python tools/facebook_group_repost/repost.py
```

Optional overrides:

```bash
python tools/facebook_group_repost/repost.py \
	--credential_file tools/facebook_group_repost/data/auth/facebook_credentials.txt \
	--cookies_file tools/facebook_group_repost/data/auth/facebook_cookies.json \
	--group_links_file "tools/facebook_group_repost/data/Group Links/test.txt" \
	--content_file tools/facebook_group_repost/data/content.txt \
	--image_dir tools/facebook_group_repost/data/Images
```
