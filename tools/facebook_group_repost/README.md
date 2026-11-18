# Facebook Group Repost Tool

Repost content to multiple Facebook groups using Selenium.

## Project structure

- Shared automation library: `lib/facebook_engine.py`
- Groups database reader: `lib/groups_db.py`
- Tool entrypoint: `tools/facebook_group_repost/repost.py`
- Runtime data: `tools/facebook_group_repost/data/`
- Groups database: `tools/facebook_group_repost/data/facebook_groups.db`

## Run

From repository root:

```bash
python tools/facebook_group_repost/repost.py
```

The repository also includes a GUI covering the same workflow and the shared library's post actions:

```bash
python tools/social_toolkit_gui.py
```

The Multi-group repost tab loads groups from `tools/facebook_group_repost/data/facebook_groups.db`
and displays them under their categories. Filter by category, search by name or URL, show hidden
groups, and select individual groups or whole categories before reposting. To add a group that is
not in the database, paste its Facebook group link and click **Fetch and add**: the tool opens the
link in the logged-in Chrome session, reads the group name, classifies it, and saves it to the
database so it is available for later runs. To re-categorize groups, select them and choose a
target in **Move selected to** (or right-click a group/category and pick a target): the move updates
the database and the saved category choices so future extraction keeps it. Log in manually in
Chrome, then click **Save cookies** to store the session for **Login (cookies)**; the status bar
reports when the cookies were saved, alongside the other action statuses.

Drag photos or videos onto the media preview, or point the media folder at a directory containing
them, and they are uploaded with the post. The numbered upload-order list shows every file with a
thumbnail: click a row to preview it and drag rows (or use **Move to first/up/down/last**) to change
the order. Videos show a summary instead of a rendered frame.

The GUI status bar shows the current operation, including which group is being processed during a
multi-group repost. Actions run through a queue: clicking another action while one is running adds
it to the queue instead of interrupting or blocking the UI, and the status bar shows how many
tasks are waiting.

Use **Cancel task** to stop the current operation and clear anything still queued. A Selenium
browser action already in progress is allowed to finish safely.

By default the script selects groups from the SQLite database. Use `--source file` with
`--group_links_file` to read a plain URL list instead.

Optional overrides:

```bash
python tools/facebook_group_repost/repost.py \
	--credential_file tools/facebook_group_repost/data/auth/facebook_credentials.txt \
	--cookies_file tools/facebook_group_repost/data/auth/facebook_cookies.json \
	--group_links_file "tools/facebook_group_repost/data/Group Links/test.txt" \
	--content_file tools/facebook_group_repost/data/content.txt \
	--image_dir tools/facebook_group_repost/data/Images
```

Database selection:

```bash
python tools/facebook_group_repost/repost.py --source db \
	--groups_db tools/facebook_group_repost/data/facebook_groups.db \
	--group_category "Laptops & MacBooks" \
	--content_file tools/facebook_group_repost/data/content.txt
```

Optional database filters: `--group_category`, `--group_subcategory`, `--managed_only`.
The `--image_dir` folder may contain both photos and videos; every supported media file in it is
attached to each post.
