import os
import argparse
import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
AUTH_DIR = os.path.join(DATA_DIR, "auth")
DEFAULT_GROUPS_DB = os.path.join(DATA_DIR, "facebook_groups.db")
DEFAULT_LINKS_FILE = os.path.join(DATA_DIR, "Group Links", "test.txt")

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from lib.facebook_engine import login, post_to_group
from lib.groups_db import load_group_urls
from lib.upload_log import log_upload_failure


def repost_to_groups(driver, group_links, post_content, image_dir=None, log=print):
    image_paths = []
    if image_dir and os.path.isdir(image_dir):
        for name in sorted(os.listdir(image_dir)):
            full_path = os.path.join(image_dir, name)
            if os.path.isfile(full_path):
                image_paths.append(full_path)

    total = len(group_links)
    successes = 0
    failures = 0
    for index, group_link in enumerate(group_links, start=1):
        log(f"Posting to group {index}/{total}: {group_link}")
        try:
            post_to_group(
                driver=driver,
                group_link=group_link,
                post_content=post_content,
                image_paths=image_paths,
                log=log,
            )
            successes += 1
        except Exception as exc:
            failures += 1
            try:
                log_upload_failure(group_link, exc)
            except OSError as log_exc:
                log(f"ERROR: could not write failure log: {log_exc}")
            log(f"ERROR posting to {group_link}: {exc}")
            continue
    log(f"Finished repost: {successes} succeeded, {failures} failed out of {total}.")


def links_from_file(path):
    with open(path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file.read().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description="Facebook group repost script")
    parser.add_argument("-l", "--login", action="store_true", help="Force credential login (skip cookies)")
    parser.add_argument(
        "--credential_file",
        nargs="?",
        default=os.path.join(AUTH_DIR, "facebook_credentials.txt"),
        help="Path to the credential file",
    )
    parser.add_argument(
        "--cookies_file",
        nargs="?",
        default=os.path.join(AUTH_DIR, "facebook_cookies.json"),
        help="Path to the cookie file",
    )
    parser.add_argument(
        "--source",
        choices=("db", "file"),
        default="db",
        help="Choose groups from the SQLite database (default) or a links file",
    )
    parser.add_argument(
        "--groups_db",
        nargs="?",
        default=DEFAULT_GROUPS_DB,
        help="Path to the Facebook groups SQLite database",
    )
    parser.add_argument(
        "--group_category",
        default=None,
        help="Only repost to groups in this category",
    )
    parser.add_argument(
        "--group_subcategory",
        default=None,
        help="Only repost to groups in this subcategory",
    )
    parser.add_argument(
        "--managed_only",
        action="store_true",
        help="Only repost to groups you manage",
    )
    parser.add_argument(
        "-g",
        "--group_links_file",
        nargs="?",
        default=DEFAULT_LINKS_FILE,
        help="Path to the group links file (used when --source=file)",
    )
    parser.add_argument(
        "-c",
        "--content_file",
        nargs="?",
        default=os.path.join(DATA_DIR, "content.txt"),
        help="Path to the content file",
    )
    parser.add_argument(
        "--image_dir",
        nargs="?",
        default=os.path.join(DATA_DIR, "Images"),
        help="Path to the images folder",
    )
    args = parser.parse_args()

    if args.source == "db":
        try:
            group_links = load_group_urls(
                args.groups_db,
                category=args.group_category,
                subcategory=args.group_subcategory,
                managed_only=args.managed_only,
            )
        except FileNotFoundError as exc:
            parser.error(str(exc))
        print(f"Selected {len(group_links)} group(s) from {args.groups_db}")
        if not group_links:
            parser.error("No groups matched the database filters.")
    else:
        try:
            group_links = links_from_file(args.group_links_file)
        except OSError as exc:
            parser.error(str(exc))
        print(f"Loaded {len(group_links)} group link(s) from {args.group_links_file}")
        if not group_links:
            parser.error("The group links file is empty.")

    with open(args.content_file, "r", encoding="utf-8") as file:
        post_content = file.read()

    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()

    login(
        driver=driver,
        use_cookies=not args.login,
        credential_file=args.credential_file,
        cookies_file=args.cookies_file,
    )

    repost_to_groups(
        driver=driver,
        group_links=group_links,
        post_content=post_content,
        image_dir=args.image_dir,
    )

    input("Press Enter to exit...")
    driver.quit()


if __name__ == "__main__":
    main()
