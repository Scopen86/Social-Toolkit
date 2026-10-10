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

The repository also includes a GUI covering the same workflow and the shared library's post actions:

```bash
python tools/facebook_gui.py
```

The GUI status bar shows the current operation, including which group is being processed during a
multi-group repost.

Use **Cancel task** to stop before the next operation or reposted group. A Selenium browser action
already in progress is allowed to finish safely.

Optional overrides:

```bash
python tools/facebook_group_repost/repost.py \
	--credential_file tools/facebook_group_repost/data/auth/facebook_credentials.txt \
	--cookies_file tools/facebook_group_repost/data/auth/facebook_cookies.json \
	--group_links_file "tools/facebook_group_repost/data/Group Links/test.txt" \
	--content_file tools/facebook_group_repost/data/content.txt \
	--image_dir tools/facebook_group_repost/data/Images
```
