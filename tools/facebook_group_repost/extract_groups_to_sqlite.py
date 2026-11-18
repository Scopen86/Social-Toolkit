import argparse
import json
import os
import sys
import re
import sqlite3
import time
import unicodedata
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from lib.group_classifier import classify_consolidated_pair, consolidate_category
DATA_DIR = os.path.join(BASE_DIR, 'data')
AUTH_DIR = os.path.join(DATA_DIR, 'auth')
COOKIES_FILE = os.path.join(AUTH_DIR, 'facebook_cookies.json')
CREDENTIALS_FILE = os.path.join(AUTH_DIR, 'facebook_credentials.txt')
GROUPS_URL = 'https://www.facebook.com/groups/joins/'

parser = argparse.ArgumentParser(
    description="Extract Facebook groups from a saved HTML page into SQLite."
)
parser.add_argument(
    "html_path",
    nargs="?",
    default=os.path.join(PROJECT_ROOT, "Facebook.html"),
    help="Saved Facebook groups HTML page (default: Facebook.html in the project root)",
)
parser.add_argument(
    "--fetch",
    action="store_true",
    help="Open Chrome with saved cookies, load all groups, and save the HTML first",
)
parser.add_argument(
    "--fetch-only",
    action="store_true",
    help="Save the groups HTML page with Chrome and exit without touching the database",
)
parser.add_argument(
    "--auto",
    action="store_true",
    help="Accept the automatic categories without interactive review",
)
parser.add_argument(
    "--review-all",
    action="store_true",
    help="Review groups even when a saved category override exists",
)
args = parser.parse_args()

HTML_PATH = args.html_path
DB_PATH = os.path.join(DATA_DIR, 'facebook_groups.db')
CATEGORY_OVERRIDES_PATH = os.path.join(DATA_DIR, 'group_categories.json')


def fetch_groups_html(output_path):
    """Save the logged-in Facebook groups page to ``output_path`` using Selenium."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from lib.facebook_engine import login, save_cookies

    print("Launching Chrome to fetch your groups page...")
    driver = webdriver.Chrome(options=Options())
    driver.maximize_window()

    def login_form_visible():
        return bool(driver.find_elements(By.NAME, 'email')) and bool(
            driver.find_elements(By.NAME, 'pass')
        )

    def wait_for_manual_login(timeout=300):
        """Wait while the user completes login or verification in the Chrome window."""
        print(
            "Waiting for Facebook login/verification. Complete it in the open Chrome "
            "window; this script continues automatically."
        )
        deadline = time.time() + timeout
        last_note = 0
        while time.time() < deadline:
            if not login_form_visible():
                print("Login detected; continuing.")
                return
            remaining = int(deadline - time.time())
            if last_note == 0 or time.time() - last_note >= 20:
                print(f"  Waiting for login... ({remaining}s left)")
                last_note = time.time()
            time.sleep(2)
        print("Timed out waiting for login.")

    try:
        try:
            login(
                driver,
                print,
                True,
                CREDENTIALS_FILE,
                COOKIES_FILE,
                wait_for_manual_login,
                True,
            )
        except Exception as exc:
            print(f"Warning: automatic login did not finish: {exc}")

        if login_form_visible():
            print("Saved cookies could not log in automatically.")
            wait_for_manual_login()
            if login_form_visible():
                print("ERROR: Facebook login was not completed.")
                sys.exit(1)
            try:
                save_cookies(driver, COOKIES_FILE, print)
            except Exception as exc:
                print(f"Warning: could not refresh cookies: {exc}")

        print(f"Opening {GROUPS_URL} ...")
        driver.get(GROUPS_URL)
        if login_form_visible():
            print("Saved cookies are not accepted on the groups page; trying saved credentials.")
            try:
                login(
                    driver,
                    print,
                    False,
                    CREDENTIALS_FILE,
                    COOKIES_FILE,
                    wait_for_manual_login,
                    True,
                )
            except Exception as exc:
                print(f"Warning: credential login did not finish: {exc}")
            driver.get(GROUPS_URL)
        if login_form_visible():
            wait_for_manual_login()
            if login_form_visible():
                print("ERROR: Facebook login was not completed.")
                sys.exit(1)
            driver.get(GROUPS_URL)

        deadline = time.time() + 45
        while time.time() < deadline and not driver.find_elements(
            By.CSS_SELECTOR, '[role="listitem"]'
        ):
            time.sleep(1)
        if not driver.find_elements(By.CSS_SELECTOR, '[role="listitem"]'):
            print("Warning: no group entries appeared on the page.")

        print("Scrolling to load all groups...")
        previous = -1
        stable_rounds = 0
        for _ in range(150):
            items = driver.find_elements(By.CSS_SELECTOR, '[role="listitem"]')
            if items:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'end'});", items[-1]
                )
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.2)
            count = len(driver.find_elements(By.CSS_SELECTOR, '[role="listitem"]'))
            if count == previous:
                stable_rounds += 1
                if stable_rounds >= 3:
                    break
            else:
                if count:
                    print(f"  {count} entries visible...")
                stable_rounds = 0
                previous = count

        html = driver.page_source
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(html)
        print(f"Saved groups page to {os.path.abspath(output_path)}")
    finally:
        driver.quit()


if args.fetch or args.fetch_only:
    fetch_groups_html(HTML_PATH)

if args.fetch_only:
    print("Fetch-only mode: stopping before extraction.")
    sys.exit(0)

if not os.path.isfile(HTML_PATH):
    print(f"ERROR: HTML file not found: {os.path.abspath(HTML_PATH)}")
    print(
        "Run with --fetch to save the page automatically, or open "
        "https://www.facebook.com/groups/joins/ in Chrome, scroll until all your groups "
        "are loaded, save the page (Ctrl+S) as Facebook.html in the project root, then "
        "run this script again."
    )
    sys.exit(1)

print(f"Reading {HTML_PATH}...")
with open(HTML_PATH, 'r', encoding='utf-8', errors='ignore') as f:
    soup = BeautifulSoup(f, 'lxml')

group_href_pattern = re.compile(r'/groups/([^/?#]+)')
excluded_slugs = {'feed', 'discover', 'joins', 'categories', 'create'}

def normalize_text(text):
    if not text:
        return ""
    # Normalize unicode (NFC)
    text = unicodedata.normalize('NFC', text)
    return text.strip()

# 1. Parse Sidebar for managed groups and last_active timestamps
managed_slugs = set()
sidebar_active_map = {}

# Locate 'Nhóm do bạn quản lý' in sidebar
h_managed = soup.find(string=re.compile(r'^Nhóm do bạn quản lý$'))
if h_managed:
    try:
        lvl2 = h_managed.parent.parent.parent
        lvl3 = lvl2.parent
        current_section = None
        for child in lvl3.children:
            text = child.get_text(strip=True)
            if 'Nhóm do bạn quản lý' in text:
                current_section = 'managed'
                continue
            elif 'Nhóm bạn đã tham gia' in text:
                current_section = 'joined'
                continue
            
            a = child.find('a', href=group_href_pattern)
            if a:
                m = group_href_pattern.search(a.get('href', ''))
                if m and m.group(1) not in excluded_slugs:
                    slug = m.group(1)
                    # Extract last active using abbr tag
                    abbr = child.find('abbr')
                    last_act = abbr.get_text(strip=True) if abbr else None
                    if not last_act:
                        m_act = re.search(r'Lần hoạt động gần nhất:\s*([^|\n]+)', child.get_text(separator=' | '))
                        if m_act:
                            last_act = m_act.group(1).strip()
                    
                    if last_act:
                        sidebar_active_map[slug] = normalize_text(last_act)
                    if current_section == 'managed':
                        managed_slugs.add(slug)
    except Exception as e:
        print(f"Warning parsing sidebar: {e}")

print(f"Found {len(managed_slugs)} managed groups and {len(sidebar_active_map)} sidebar activity entries.")

# 2. Parse Group Listitems
listitems = soup.find_all(attrs={'role': 'listitem'})
print(f"Found {len(listitems)} total listitems in document.")



def load_category_overrides():
    """Return saved per-group category choices keyed by group slug."""
    if not os.path.isfile(CATEGORY_OVERRIDES_PATH):
        return {}
    try:
        with open(CATEGORY_OVERRIDES_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except (OSError, ValueError) as exc:
        print(f"Warning: could not read saved categories: {exc}")
        return {}
    if isinstance(data, dict) and isinstance(data.get('groups'), dict):
        data = data['groups']
    if not isinstance(data, dict):
        return {}

    overrides = {}
    for slug, value in data.items():
        if isinstance(value, dict):
            category = str(value.get('category', '')).strip()
            subcategory = str(value.get('subcategory', '')).strip()
            name = str(value.get('name', '')).strip()
        elif isinstance(value, (list, tuple)) and value:
            category = str(value[0]).strip()
            subcategory = str(value[1]).strip() if len(value) > 1 else ''
            name = ''
        elif isinstance(value, str):
            category, _, subcategory = value.partition('|')
            category, subcategory = category.strip(), subcategory.strip()
            name = ''
        else:
            continue
        if category:
            overrides[str(slug)] = {
                'name': name,
                'category': category,
                'subcategory': subcategory,
            }
    return overrides


def save_category_overrides(overrides):
    os.makedirs(os.path.dirname(CATEGORY_OVERRIDES_PATH), exist_ok=True)
    with open(CATEGORY_OVERRIDES_PATH, 'w', encoding='utf-8') as file:
        json.dump(overrides, file, ensure_ascii=False, indent=2, sort_keys=True)


def _prompt_category_change(records, current_category, current_subcategory):
    """Ask for a category and subcategory for one group."""
    categories = sorted({row[4] for row in records if row[4]}, key=str.casefold)
    print("    Categories:")
    for index, category in enumerate(categories, 1):
        print(f"      {index}. {category}")
    try:
        raw = input(
            f"    Category number or new name [Enter = {current_category}]: "
        ).strip()
    except EOFError:
        print()
        return None
    if not raw:
        category = current_category
    elif raw.isdigit() and 1 <= int(raw) <= len(categories):
        category = categories[int(raw) - 1]
    else:
        category = raw

    subcategories = sorted(
        {row[5] for row in records if row[4] == category and row[5]},
        key=str.casefold,
    )
    if subcategories:
        print("    Subcategories:")
        for index, subcategory in enumerate(subcategories, 1):
            print(f"      {index}. {subcategory}")
    default_sub = current_subcategory if category == current_category else ''
    default_label = default_sub if default_sub else '(none)'
    try:
        raw = input(
            "    Subcategory number, new name, or 0 for none "
            f"[Enter = {default_label}]: "
        ).strip()
    except EOFError:
        print()
        return category, default_sub
    if not raw:
        subcategory = default_sub
    elif raw == '0':
        subcategory = ''
    elif raw.isdigit() and 1 <= int(raw) <= len(subcategories):
        subcategory = subcategories[int(raw) - 1]
    else:
        subcategory = raw
    return category, subcategory


def review_group_categories(records, overrides, review_all=False):
    """Let the user keep or edit the automatic category of each group."""
    pending = [
        record
        for record in records
        if review_all or record[0] not in overrides
    ]
    if not pending:
        print("All groups already have saved categories; nothing to review.")
        return

    saved_count = len(records) - len(pending)
    print("\n=== Category review (semi-automatic) ===")
    message = f"{len(pending)} group(s) to review"
    if saved_count:
        message += f", {saved_count} using saved categories"
    print(message + ".")
    print("Press Enter to keep the suggestion, c to change it, or q to keep all remaining.")
    print("Saved changes are reused automatically the next time you run this script.\n")

    for position, record in enumerate(pending, 1):
        name = record[1]
        category, subcategory = record[4], record[5]
        print(f"[{position}/{len(pending)}] {name}")
        print(f"    slug: {record[0]}")
        label = f"{category} › {subcategory}" if subcategory else category
        print(f"    suggested: {label}")
        try:
            answer = input(
                "    [Enter] keep · [c] change · [q] keep rest: "
            ).strip().lower()
        except EOFError:
            print()
            break
        if answer == 'q':
            break
        if answer == 'c':
            choice = _prompt_category_change(records, category, subcategory)
            if choice is None:
                continue
            record[4], record[5] = choice
            label = f"{record[4]} › {record[5]}" if record[5] else record[4]
            print(f"    set to: {label}")


# Extract records
records = []
seen_slugs = set()

for li in listitems:
    a_tags = li.find_all('a', href=group_href_pattern)
    valid_a = [a for a in a_tags if group_href_pattern.search(a.get('href', '')).group(1) not in excluded_slugs]
    if not valid_a:
        continue
    
    main_a = valid_a[0]
    href = main_a.get('href', '')
    m = group_href_pattern.search(href)
    slug = m.group(1) if m else ''
    
    if slug in seen_slugs:
        continue
    seen_slugs.add(slug)
    
    canonical_url = f"https://www.facebook.com/groups/{slug}/"
    is_numeric = 1 if slug.isdigit() else 0
    
    # Name
    name = None
    for a in valid_a:
        t = a.get_text(strip=True)
        if t and t != 'Xem nhóm':
            name = t
            break
    if not name:
        svg = li.find('svg', attrs={'aria-label': True})
        if svg:
            name = svg.get('aria-label')
    if not name:
        name = slug
    name = normalize_text(name)
    
    # Last Visited
    last_visited = None
    abbr = li.find('abbr')
    if abbr:
        last_visited = abbr.get_text(strip=True) or abbr.get('aria-label')
    if not last_visited:
        m_vis = re.search(r'Lần truy cập gần đây nhất:\s*([^\n|]+)', li.get_text(separator=' | '))
        if m_vis:
            last_visited = m_vis.group(1).strip()
    last_visited = normalize_text(last_visited) if last_visited else None
    
    # Last Active (from sidebar if present)
    last_active = sidebar_active_map.get(slug)
    
    # Is Managed
    is_managed = 1 if slug in managed_slugs else 0
    
    # Avatar URL
    avatar_url = None
    image_tag = li.find('image')
    if image_tag:
        avatar_url = image_tag.get('xlink:href') or image_tag.get('href')
    if not avatar_url:
        img_tag = li.find('img')
        if img_tag:
            avatar_url = img_tag.get('src')
            
    # Verified badge
    has_badge = 1 if ('✓' in name or '✅' in name) else 0
    
    # Raw text
    raw_text = li.get_text(separator=' | ', strip=True)
    
    # Categorization (commerce-focused buckets, with peripheral subcategories)
    category, subcategory = classify_consolidated_pair(slug, name)
    
    records.append((
        slug,
        name,
        canonical_url,
        is_numeric,
        category,
        subcategory,
        last_visited,
        last_active,
        is_managed,
        avatar_url,
        has_badge,
        raw_text
    ))

print(f"Extracted {len(records)} unique groups.")

if not records:
    print("ERROR: No groups were found in the page. The database was not modified.")
    print(
        "Run with --fetch, or make sure Facebook.html is a saved copy of "
        "https://www.facebook.com/groups/joins/ with your groups loaded."
    )
    sys.exit(1)

# 3. Apply saved category choices and optionally review them
auto_categories = {record[0]: (record[4], record[5]) for record in records}
category_overrides = load_category_overrides()
records = [list(record) for record in records]
if category_overrides:
    applied = 0
    for record in records:
        saved = category_overrides.get(record[0])
        if saved:
            record[4] = consolidate_category(saved['category'])
            record[5] = saved.get('subcategory', '')
            applied += 1
    print(f"Applied saved categories to {applied} group(s) from {CATEGORY_OVERRIDES_PATH}.")

interactive = bool(getattr(sys.stdin, 'isatty', lambda: False)())
if args.auto:
    print("Category review skipped (--auto).")
elif not interactive:
    print("No interactive terminal detected; keeping automatic categories.")
else:
    review_group_categories(records, category_overrides, args.review_all)
    updated_overrides = {
        slug: value
        for slug, value in category_overrides.items()
        if slug not in auto_categories
    }
    for record in records:
        if (record[4], record[5]) == auto_categories[record[0]]:
            continue
        updated_overrides[record[0]] = {
            'name': record[1],
            'category': record[4],
            'subcategory': record[5],
        }
    if updated_overrides != category_overrides:
        save_category_overrides(updated_overrides)
        print(f"Saved category choices to {CATEGORY_OVERRIDES_PATH}")
    else:
        print("No category changes to save.")

# 4. Create SQLite Database and Insert
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Preserve favorite/hidden flags across re-extraction (keyed by group slug).
existing_group_flags = {}
existing_category_prefs = []
if os.path.exists(DB_PATH):
    try:
        old_conn = sqlite3.connect(DB_PATH)
        columns = {row[1] for row in old_conn.execute("PRAGMA table_info(groups)")}
        select_columns = ["group_slug"]
        if "is_favorite" in columns:
            select_columns.append("is_favorite")
        if "is_hidden" in columns:
            select_columns.append("is_hidden")
        for values in old_conn.execute(
            f"SELECT {', '.join(select_columns)} FROM groups"
        ):
            data = dict(zip(select_columns, values))
            existing_group_flags[data["group_slug"]] = (
                data.get("is_favorite", 0),
                data.get("is_hidden", 0),
            )

        tables = {
            row[0]
            for row in old_conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "category_prefs" in tables:
            existing_category_prefs = [
                tuple(row)
                for row in old_conn.execute(
                    "SELECT category, subcategory, is_favorite, is_hidden "
                    "FROM category_prefs"
                )
            ]
        old_conn.close()
    except sqlite3.Error as exc:
        print(f"Warning: could not read existing preferences: {exc}")

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Enable WAL mode for performance
cursor.execute("PRAGMA journal_mode = WAL;")

cursor.execute("""
CREATE TABLE groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    is_numeric_id INTEGER NOT NULL DEFAULT 0,
    category TEXT NOT NULL,
    subcategory TEXT,
    last_visited TEXT,
    last_active TEXT,
    is_managed INTEGER NOT NULL DEFAULT 0,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    avatar_url TEXT,
    has_verified_badge INTEGER NOT NULL DEFAULT 0,
    raw_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

cursor.execute("CREATE INDEX idx_groups_slug ON groups(group_slug);")
cursor.execute("CREATE INDEX idx_groups_category ON groups(category);")
cursor.execute("CREATE INDEX idx_groups_subcategory ON groups(subcategory);")
cursor.execute("CREATE INDEX idx_groups_is_managed ON groups(is_managed);")
cursor.execute("CREATE INDEX idx_groups_is_favorite ON groups(is_favorite);")
cursor.execute("CREATE INDEX idx_groups_is_hidden ON groups(is_hidden);")

cursor.execute("""
CREATE TABLE category_prefs (
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL DEFAULT '',
    is_favorite INTEGER NOT NULL DEFAULT 0,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (category, subcategory)
);
""")
if existing_category_prefs:
    cursor.executemany(
        "INSERT INTO category_prefs "
        "(category, subcategory, is_favorite, is_hidden) VALUES (?, ?, ?, ?)",
        existing_category_prefs,
    )

insert_rows = [
    (*record, *existing_group_flags.get(record[0], (0, 0))) for record in records
]

cursor.executemany("""
INSERT INTO groups (
    group_slug,
    name,
    url,
    is_numeric_id,
    category,
    subcategory,
    last_visited,
    last_active,
    is_managed,
    avatar_url,
    has_verified_badge,
    raw_text,
    is_favorite,
    is_hidden
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
""", insert_rows)

conn.commit()

# Create a summary view for categories
cursor.execute("""
CREATE VIEW v_category_summary AS
SELECT 
    category,
    COUNT(*) AS total_groups,
    SUM(is_managed) AS managed_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM groups), 2) AS percentage
FROM groups
GROUP BY category
ORDER BY total_groups DESC;
""")
conn.commit()

# Print statistics
print("\n=== INSERTION COMPLETED SUCCESSFULLY ===")
cursor.execute("SELECT COUNT(*) FROM groups;")
total_count = cursor.fetchone()[0]
print(f"Total rows in groups table: {total_count}")

print("\n=== Category Distribution ===")
cursor.execute("SELECT category, total_groups, managed_count, percentage FROM v_category_summary;")
for row in cursor.fetchall():
    print(f" - {row[0]}: {row[1]} groups ({row[3]}%) [Managed: {row[2]}]")

conn.close()
print(f"\nSQLite Database created at: {os.path.abspath(DB_PATH)}")
