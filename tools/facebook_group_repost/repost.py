import os
import argparse
import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data", "facebook_group_repost")
AUTH_DIR = os.path.join(DATA_DIR, "auth")

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from lib.facebook_engine import login, post_to_group


def repost_to_groups(driver, group_links, post_content, image_dir=None, log=print):
    image_paths = []
    if image_dir and os.path.isdir(image_dir):
        for name in sorted(os.listdir(image_dir)):
            full_path = os.path.join(image_dir, name)
            if os.path.isfile(full_path):
                image_paths.append(full_path)

    for group_link in group_links:
        post_to_group(
            driver=driver,
            group_link=group_link,
            post_content=post_content,
            image_paths=image_paths,
            log=log,
        )

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
        "-g",
        "--group_links_file",
        nargs="?",
        default=os.path.join(DATA_DIR, "Group Links", "test.txt"),
        help="Path to the group links file",
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

    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()

    with open(args.group_links_file, "r", encoding="utf-8") as file:
        group_links = [line.strip() for line in file.read().splitlines() if line.strip()]

    with open(args.content_file, "r", encoding="utf-8") as file:
        post_content = file.read()

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

