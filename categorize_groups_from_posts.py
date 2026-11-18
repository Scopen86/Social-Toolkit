"""Categorize Facebook groups from their recent posts.

The script prints the category list first, then opens each selected group in
Chrome using the saved Facebook session, reads a handful of recent posts, and
classifies the group from the name plus the post text. Confident results are
saved automatically; low-confidence results are shown to you for a decision
(or written to a review report when the terminal is not interactive).
"""

import argparse
import json
import os
import sqlite3
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from lib.group_classifier import (
    CONSOLIDATED_CATEGORIES,
    classify_consolidated,
    consolidate_category,
)

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(BASE_DIR, 'tools', 'facebook_group_repost', 'data')
DEFAULT_DB = os.path.join(DATA_DIR, 'facebook_groups.db')
OVERRIDES_PATH = os.path.join(DATA_DIR, 'group_categories.json')
REVIEW_PATH = os.path.join(DATA_DIR, 'group_category_review.json')
AUTH_DIR = os.path.join(DATA_DIR, 'auth')
COOKIES_FILE = os.path.join(AUTH_DIR, 'facebook_cookies.json')
CREDENTIALS_FILE = os.path.join(AUTH_DIR, 'facebook_credentials.txt')


def parse_args():
    parser = argparse.ArgumentParser(
        description="Categorize Facebook groups from their recent posts."
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="Groups SQLite database")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check every group instead of only the groups that need a decision",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stop after this many groups (0 = no limit)",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=6,
        help="Recent posts to read per group (default 6)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between groups (default 1.0)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-check groups that already have a post-based result",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Write low-confidence groups to a JSON report instead of prompting",
    )
    parser.add_argument(
        "--categories-only",
        action="store_true",
        help="Print the category list and exit",
    )
    return parser.parse_args()


def load_groups(db_path):
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"Groups database not found: {db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in connection.execute(
            "SELECT group_slug, name, url, category, subcategory "
            "FROM groups ORDER BY name COLLATE NOCASE"
        )
    ]
    connection.close()
    return rows


def load_overrides():
    try:
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        return {}
    if isinstance(data, dict) and isinstance(data.get("groups"), dict):
        data = data["groups"]
    return data if isinstance(data, dict) else {}


def save_overrides(overrides):
    os.makedirs(os.path.dirname(OVERRIDES_PATH), exist_ok=True)
    with open(OVERRIDES_PATH, "w", encoding="utf-8") as file:
        json.dump(overrides, file, ensure_ascii=False, indent=2, sort_keys=True)


def save_review(items):
    os.makedirs(os.path.dirname(REVIEW_PATH), exist_ok=True)
    with open(REVIEW_PATH, "w", encoding="utf-8") as file:
        json.dump(items, file, ensure_ascii=False, indent=2)


def current_pair(row):
    return (
        consolidate_category(row.get("category") or ""),
        row.get("subcategory") or "",
    )


def category_taxonomy(groups):
    """Return ``{category: group_count}`` for the consolidated buckets."""
    counts = {category: 0 for category in CONSOLIDATED_CATEGORIES}
    for row in groups:
        category, _ = current_pair(row)
        counts[category] = counts.get(category, 0) + 1
    return counts


def print_categories(taxonomy):
    print("\n=== Category list ===")
    ordered = sorted(taxonomy, key=str.casefold)
    for index, category in enumerate(ordered, 1):
        print(f"{index:>2}. {category} ({taxonomy[category]} groups)")
    print(f"\n{len(taxonomy)} categories.\n")


def needs_decision(row, overrides, refresh):
    slug = row["group_slug"]
    cached = overrides.get(slug)
    if isinstance(cached, dict) and cached.get("source") == "posts" and not refresh:
        return False
    if not isinstance(cached, dict):
        return True  # group was not in the previous extraction
    category, _ = current_pair(row)
    if not (row.get("category") or "").strip():
        return True
    auto = classify_consolidated(slug, row["name"])
    return auto != (category, "")


def wait_for_manual_login(driver, timeout=300):
    from selenium.webdriver.common.by import By

    def login_form_visible():
        return bool(driver.find_elements(By.NAME, "email")) and bool(
            driver.find_elements(By.NAME, "pass")
        )

    print(
        "Waiting for Facebook login/verification. Complete it in the open Chrome "
        "window; the script continues automatically."
    )
    deadline = time.time() + timeout
    last_note = 0
    while time.time() < deadline:
        if not login_form_visible():
            print("Login detected; continuing.")
            return
        if last_note == 0 or time.time() - last_note >= 20:
            print(f"  Waiting for login... ({int(deadline - time.time())}s left)")
            last_note = time.time()
        time.sleep(2)
    raise RuntimeError("Timed out waiting for Facebook login.")


def start_browser():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    from lib.facebook_engine import login

    driver = webdriver.Chrome(options=Options())
    driver.maximize_window()
    login(
        driver,
        print,
        True,
        CREDENTIALS_FILE,
        COOKIES_FILE,
        lambda: wait_for_manual_login(driver),
        True,
    )
    return driver


def collect_post_text(driver, url, max_posts):
    from selenium.webdriver.common.by import By

    driver.get(url)
    deadline = time.time() + 20
    while time.time() < deadline:
        if driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]'):
            break
        time.sleep(0.5)

    driver.execute_script("window.scrollBy(0, 1600);")
    time.sleep(1.5)

    texts = []
    for article in driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]'):
        text = (article.text or "").strip()
        if text:
            texts.append(text[:1200])
        if len(texts) >= max_posts:
            break
    if not texts:
        feeds = driver.find_elements(By.CSS_SELECTOR, 'div[role="feed"]')
        if feeds:
            text = (feeds[0].text or "").strip()
            if text:
                texts.append(text[:4000])
    return texts


def decide(current, name_guess, post_guess, post_count):
    """Return ``(guess, confidence)`` for the post-based classification."""
    if not post_count:
        return post_guess, "low"
    if post_guess == name_guess:
        # Name and post text independently agree: strong signal.
        return post_guess, "high"
    if post_guess == current:
        return post_guess, "high"
    if not current[0]:
        return post_guess, "medium"
    # The post-based result disagrees with both the current category and the name.
    return post_guess, "low"


def choose_category(taxonomy, suggested):
    categories = sorted(taxonomy, key=str.casefold)
    print("    Categories:")
    for index, category in enumerate(categories, 1):
        print(f"      {index}. {category}")
    raw = input(
        f"    Category number or new name [Enter = {suggested[0]}]: "
    ).strip()
    if not raw:
        return suggested[0]
    if raw.isdigit() and 1 <= int(raw) <= len(categories):
        return categories[int(raw) - 1]
    return raw


def update_group(db_path, slug, category, subcategory):
    connection = sqlite3.connect(db_path)
    connection.execute(
        "UPDATE groups SET category = ?, subcategory = ? WHERE group_slug = ?",
        (category, subcategory, slug),
    )
    connection.commit()
    connection.close()


def main():
    args = parse_args()
    groups = load_groups(args.db)
    taxonomy = category_taxonomy(groups)
    print_categories(taxonomy)
    if args.categories_only:
        return

    overrides = load_overrides()
    targets = [
        row for row in groups if args.all or needs_decision(row, overrides, args.refresh)
    ]
    if args.limit:
        targets = targets[: args.limit]

    print(f"Groups needing a post check: {len(targets)} of {len(groups)}.")
    if not targets:
        print("Nothing to do. Use --all or --refresh to re-check groups.")
        return

    estimate = len(targets) * (args.delay + 6) / 60
    print(f"Estimated time: about {estimate:.0f} minute(s).")
    print("The category list is above; review decisions happen as groups are processed.")

    driver = start_browser()
    interactive = bool(getattr(sys.stdin, "isatty", lambda: False)()) and not args.report
    review_items = []
    auto_count = 0
    manual_count = 0
    kept_count = 0

    try:
        for index, row in enumerate(targets, 1):
            slug = row["group_slug"]
            name = row["name"]
            current = current_pair(row)
            print(f"\n[{index}/{len(targets)}] {name}")
            try:
                posts = collect_post_text(driver, row["url"], args.max_posts)
            except Exception as exc:
                print(f"    Could not read posts: {exc}")
                posts = []
            post_text = "\n".join(posts)
            name_guess = classify_consolidated(slug, name)
            post_guess = classify_consolidated(slug, f"{name}\n{post_text}")
            guess, confidence = decide(current, name_guess, post_guess, len(posts))
            print(f"    posts read: {len(posts)}")
            print(f"    name guess: {name_guess[0]}")
            print(f"    post guess: {guess[0]}")
            print(f"    confidence: {confidence}")

            if confidence in ("high", "medium"):
                category, subcategory = guess
                update_group(args.db, slug, category, subcategory)
                overrides[slug] = {
                    "name": name,
                    "category": category,
                    "subcategory": subcategory,
                    "source": "posts",
                    "confidence": confidence,
                }
                save_overrides(overrides)
                auto_count += 1
                print(f"    saved: {category}")
            elif interactive:
                print("    Needs your decision.")
                answer = input(
                    "    [Enter] use guess · [c] choose · [k] keep current · [s] skip: "
                ).strip().lower()
                if answer == "c":
                    category = choose_category(taxonomy, guess)
                    subcategory = ""
                elif answer == "k" or answer == "s":
                    kept_count += 1
                    if posts:
                        review_items.append(
                            {
                                "slug": slug,
                                "name": name,
                                "url": row["url"],
                                "current": list(current),
                                "name_guess": list(name_guess),
                                "post_guess": list(guess),
                            }
                        )
                    continue
                else:
                    category, subcategory = guess
                update_group(args.db, slug, category, subcategory)
                overrides[slug] = {
                    "name": name,
                    "category": category,
                    "subcategory": subcategory,
                    "source": "posts",
                    "confidence": "manual",
                }
                save_overrides(overrides)
                manual_count += 1
                taxonomy[category] = taxonomy.get(category, 0) + 1
                print(f"    saved: {category}")
            else:
                review_items.append(
                    {
                        "slug": slug,
                        "name": name,
                        "url": row["url"],
                        "current": list(current),
                        "name_guess": list(name_guess),
                        "post_guess": list(guess),
                        "posts_read": len(posts),
                    }
                )
                print("    queued for review")
            time.sleep(args.delay)
    except KeyboardInterrupt:
        print("\nInterrupted; progress so far is saved.")
    finally:
        driver.quit()
        save_overrides(overrides)
        if review_items:
            save_review(review_items)

    print("\n=== Summary ===")
    print(f"Automatic (high/medium): {auto_count}")
    print(f"Manual: {manual_count}")
    print(f"Kept current / skipped: {kept_count}")
    print(f"Queued for review: {len(review_items)}")
    if review_items:
        print(f"Review file: {REVIEW_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()
