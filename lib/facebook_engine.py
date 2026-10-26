import json
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def locate_element(driver, selectors, by=By.CSS_SELECTOR):
    for selector in selectors:
        elements = driver.find_elements(by, selector)
        enabled_elements = [el for el in elements if el.is_enabled()]
        if enabled_elements:
            return enabled_elements[0]
    return None

def login(
    driver,
    log=print,
    use_cookies=False,
    credential_file="facebook_credentials.txt",
    cookies_file="facebook_cookies.json",
    wait_for_verification=None,
):

    driver.get("https://www.facebook.com/")

    if use_cookies:
        if cookies_file and os.path.exists(cookies_file):
            with open(cookies_file, "r", encoding="utf-8") as file:
                cookies = json.load(file)

            for cookie in cookies:
                cookie = dict(cookie)
                if "expiry" in cookie:
                    cookie["expiry"] = int(cookie["expiry"])
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    # Ignore cookies rejected by the browser and continue.
                    pass

            driver.refresh()
            time.sleep(3)

            login_form_visible = bool(driver.find_elements(By.NAME, "email")) and bool(
                driver.find_elements(By.NAME, "pass")
            )
            if not login_form_visible:
                log("Facebook login completed using saved cookies.")
                return

            log("Saved cookies did not complete login; falling back to credentials.")
        else:
            log(f"Cookie file not found: {cookies_file}. Falling back to credentials.")

    if not os.path.exists(credential_file):
        raise FileNotFoundError(
            f"Credential file not found: {credential_file}. "
            "Create this file with email on line 1 and password on line 2."
        )

    with open(credential_file, "r", encoding="utf-8") as file:
        lines = file.read().splitlines()
    if len(lines) < 2:
        raise ValueError("credential file must contain email on line 1 and password on line 2")

    email = lines[0].strip()
    password = lines[1].strip()

    email_elem = driver.find_element(By.NAME, "email")
    pass_elem = driver.find_element(By.NAME, "pass")
    # login_btn = driver.find_element(By.NAME, "login")

    email_elem.send_keys(email)
    time.sleep(1)
    pass_elem.send_keys(password)
    time.sleep(1)
    # login_btn.click()
    pass_elem.send_keys(Keys.RETURN)

    log("Complete login verification in the browser.")
    if wait_for_verification is None:
        input("Press Enter after login is complete...")
    else:
        wait_for_verification()

    # If the login form is still present, login likely did not complete.
    login_form_visible = bool(driver.find_elements(By.NAME, "email")) and bool(
        driver.find_elements(By.NAME, "pass")
    )
    if login_form_visible:
        raise RuntimeError(
            "Facebook login appears incomplete (login form still visible). "
            "Check credentials or complete any required verification in the browser."
        )

    if cookies_file:
        cookies_dir = os.path.dirname(cookies_file)
        if cookies_dir:
            os.makedirs(cookies_dir, exist_ok=True)

        with open(cookies_file, "w", encoding="utf-8") as file:
            json.dump(driver.get_cookies(), file, ensure_ascii=False, indent=2)

        log(f"Saved login cookies to: {cookies_file}")

    log("Facebook login completed.")

def get_dialog(driver, url, log=print):
    driver.get(url)
    time.sleep(5)  # Wait for the page to load

    try:
        dialog = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
        return dialog
    except Exception:
        return log("Post dialog not found.")

def extract_post_message(dialog):
    selectors = [
        "div[data-ad-preview='message']",
        "div[data-ad-comet-preview='message']",
        "div[dir='auto']",
    ]

    for selector in selectors:
        elements = dialog.find_elements(By.CSS_SELECTOR, selector)
        texts = [element.text.strip() for element in elements if element.text and element.text.strip()]
        if texts:
            # Keep line breaks from distinct blocks while avoiding duplicates.
            seen = set()
            ordered_unique = []
            for text in texts:
                if text not in seen:
                    ordered_unique.append(text)
                    seen.add(text)
            return "\n".join(ordered_unique)

    raise RuntimeError("Could not extract post message from dialog")


def extract_post_details(dialog, url):
    """Extract information visible in a Facebook post dialog."""
    message = extract_post_message(dialog)
    author = None
    timestamp = None

    post_id = _facebook_post_id(url)
    for link in dialog.find_elements(By.CSS_SELECTOR, "a[href]"):
        href = link.get_attribute("href")
        label = (link.text or "").strip()
        if not href:
            continue
        path = urlparse(href).path.lower()
        if not author and label and ("/user/" in path or "/profile.php" in path):
            author = label
        if timestamp is None and post_id and (
            f"/posts/{post_id}" in path or _facebook_post_id(href) == post_id
        ):
            for candidate in (
                link.get_attribute("aria-label"),
                link.get_attribute("title"),
                label,
            ):
                if candidate and _parse_facebook_timestamp(candidate):
                    timestamp = candidate.strip()
                    break

    if timestamp is None:
        timestamp = _absolute_timestamp_from_container(dialog)

    if not author:
        for heading in dialog.find_elements(By.CSS_SELECTOR, "h1, h2, h3"):
            text = (heading.text or "").strip()
            for prefix in ("Bài viết của ", "Post by "):
                if text.startswith(prefix):
                    author = text[len(prefix):].strip()
                    break
            if author:
                break

    return {
        "url": url,
        "post_id": post_id,
        "message": message,
        "author": author,
        "timestamp": timestamp,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def _facebook_post_id(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    # Group photo links often point at an attached image, while the actual
    # group post ID is carried in values such as ``set=gm.123456789`` or
    # ``set=pcb.123456789``.
    for value in query.get("set", []):
        group_post = re.search(r"(?:^|\.)(?:gm|pcb)\.(\d+)(?:$|\D)", value)
        if group_post:
            return group_post.group(1)
    # A photo's ``fbid`` identifies the attachment, not its containing post.
    if parsed.path.rstrip("/").endswith("/photo"):
        return None
    for key in ("story_fbid", "fbid", "post_id", "multi_permalinks"):
        if query.get(key):
            return query[key][0].split(",", 1)[0]
    parts = [part for part in parsed.path.split("/") if part]
    for marker in ("posts", "videos", "permalink", "photo"):
        if marker in parts and parts.index(marker) + 1 < len(parts):
            return parts[parts.index(marker) + 1]
    return None


def _parse_facebook_timestamp(value):
    """Parse absolute timestamps exposed in a post link's accessible label."""
    value = (value or "").strip()
    vietnamese = re.search(
        r"(\d{1,2})\s+tháng\s+(\d{1,2}),?\s*(\d{4})\s+lúc\s+(\d{1,2}):(\d{2})",
        value,
        re.IGNORECASE,
    )
    if vietnamese:
        day, month, year, hour, minute = map(int, vietnamese.groups())
        return datetime(year, month, day, hour, minute)
    for date_format in (
        "%A, %B %d, %Y at %I:%M %p",
        "%B %d, %Y at %I:%M %p",
        "%A, %B %d, %Y at %H:%M",
    ):
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone().replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        pass
    return None


def _absolute_timestamp_from_container(container):
    selectors = "[aria-label], [title], [data-tooltip-content], [data-utime], abbr, time"
    for element in container.find_elements(By.CSS_SELECTOR, selectors):
        candidates = [
            element.get_attribute("aria-label"),
            element.get_attribute("title"),
            element.get_attribute("data-tooltip-content"),
            element.get_attribute("datetime"),
            element.text,
        ]
        unix_time = element.get_attribute("data-utime")
        if unix_time and unix_time.isdigit():
            try:
                candidates.append(datetime.fromtimestamp(int(unix_time)).isoformat())
            except (OverflowError, OSError, ValueError):
                pass
        for candidate in candidates:
            if candidate and _parse_facebook_timestamp(candidate):
                return candidate.strip()
    return None


def scrape_user_group_posts(driver, profile_url, scrape_option, database_path, log=print):
    """Read authored posts from a Facebook group member page into the posts table."""
    profile = urlparse(profile_url)
    if "facebook.com" not in (profile.hostname or "") or not re.search(
        r"/groups/[^/]+/user/\d+", profile.path
    ):
        raise ValueError("Enter a Facebook group member URL ending in /groups/<group>/user/<id>.")

    if scrape_option == "10 newest":
        max_posts = 10
        cutoff = None
    elif scrape_option == "last 30 days":
        max_posts = None
        cutoff = datetime.now() - timedelta(days=30)
    else:
        raise ValueError("Scrape option must be '10 newest' or 'last 30 days'.")

    driver.get(profile_url)
    time.sleep(6)
    log(f"Opened group member page for {profile.path.split('/')[-1]}.")
    seen = set()
    saved_count = 0
    stale_scrolls = 0
    group_id = profile.path.split("/")[2]
    profile_handle = driver.current_window_handle
    while True:
        found_on_pass = 0
        post_headings = driver.find_elements(By.CSS_SELECTOR, "h2")
        for heading in post_headings:
            heading_text = (heading.text or "").strip()
            lower_heading = heading_text.lower()
            if not any(phrase in lower_heading for phrase in (
                "đã đăng lên", "posted in", "shared a post in",
            )):
                continue

            card = heading
            post_link = None
            for _ in range(15):
                post_links = card.find_elements(
                    By.CSS_SELECTOR,
                    "a[href*='/posts/'], a[href*='/photo/']",
                )
                post_link = next((link for link in post_links if _facebook_post_id(
                    link.get_attribute("href") or ""
                )), None)
                if post_link:
                    break
                try:
                    card = card.find_element(By.XPATH, "..")
                except Exception:
                    break
            if not post_link:
                continue

            post_id = _facebook_post_id(post_link.get_attribute("href") or "")
            if not post_id or post_id in seen:
                continue
            card_timestamp = _absolute_timestamp_from_container(card)
            seen.add(post_id)
            try:
                driver.switch_to.new_window("tab")
                post_url = (
                    f"https://www.facebook.com/groups/{group_id}/"
                    f"?multi_permalinks={post_id}&hoisted_section_header_type=recently_seen"
                )
                dialog = get_dialog(driver, post_url, log=log)
                if dialog is None:
                    log(f"Could not open post {post_id}; skipped.")
                    continue
                post = extract_post_details(dialog, post_url)
                if not post.get("timestamp"):
                    post["timestamp"] = card_timestamp
            except Exception as exc:
                log(f"Could not read post {post_id}: {exc}")
                continue
            finally:
                if driver.current_window_handle != profile_handle:
                    driver.close()
                    driver.switch_to.window(profile_handle)

            posted_at = _parse_facebook_timestamp(post.get("timestamp"))
            if cutoff and not posted_at:
                log(f"Could not parse absolute timestamp for post {post_id}; skipped.")
                continue
            if cutoff and posted_at < cutoff:
                log(f"Reached post older than 30 days; stopping at {post['timestamp']}.")
                return saved_count

            save_post_to_sqlite(post, database_path)
            saved_count += 1
            found_on_pass += 1
            log(f"Saved post {post_id} by {post.get('author')} ({post.get('timestamp')}).")
            if max_posts and saved_count >= max_posts:
                log(f"Reached the limit of {max_posts} newest posts.")
                return saved_count

        if not found_on_pass:
            stale_scrolls += 1
        else:
            stale_scrolls = 0
        if stale_scrolls >= 3:
            log("No additional authored group posts loaded after three scroll attempts.")
            break

        driver.switch_to.window(profile_handle)
        driver.execute_script("window.scrollBy(0, Math.max(window.innerHeight, 1000));")
        time.sleep(2.5)

    log(f"Finished scraping; saved {saved_count} post(s).")
    return saved_count


def save_post_to_sqlite(post, database_path):
    """Persist one post record in the posts table."""
    database_path = os.path.abspath(os.path.expanduser(database_path))
    os.makedirs(os.path.dirname(database_path), exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                post_id TEXT,
                url TEXT NOT NULL,
                message TEXT NOT NULL,
                author TEXT,
                timestamp TEXT,
                captured_at TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Uncategorized'
            )
        """)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(posts)")}
        if "category" not in columns:
            connection.execute(
                "ALTER TABLE posts ADD COLUMN category TEXT NOT NULL DEFAULT 'Uncategorized'"
            )
        if "data_json" in columns:
            connection.execute("ALTER TABLE posts DROP COLUMN data_json")
        if "timestamp_absolute" in columns:
            connection.execute(
                "UPDATE posts SET timestamp = timestamp_absolute "
                "WHERE timestamp_absolute IS NOT NULL"
            )
            connection.execute("ALTER TABLE posts DROP COLUMN timestamp_absolute")

        for table in ("post_links", "post_media", "post_engagement_labels"):
            connection.execute(f"DROP TABLE IF EXISTS {table}")

        values = (
            post.get("post_id"), post["url"], post["message"], post.get("author"),
            post.get("timestamp"), post["captured_at"], post.get("category"),
        )
        if post.get("post_id"):
            row = connection.execute(
                "SELECT id FROM posts WHERE post_id = ? ORDER BY id LIMIT 1",
                (post["post_id"],),
            ).fetchone()
            if row:
                connection.execute(
                    "DELETE FROM posts WHERE post_id = ? AND id != ?",
                    (post["post_id"], row[0]),
                )
        else:
            row = connection.execute("SELECT id FROM posts WHERE url = ?", (post["url"],)).fetchone()
        if row:
            connection.execute("""
                UPDATE posts SET post_id=?, url=?, message=?, author=?, timestamp=?,
                    captured_at=?, category=COALESCE(?, category) WHERE id=?
            """, (*values, row[0]))
        else:
            connection.execute("""
                INSERT INTO posts
                    (post_id, url, message, author, timestamp, captured_at, category)
                VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, 'Uncategorized'))
            """, values)

def like_post(dialog):
    try:
        selectors = [
            ".//div[@role='button' and @aria-label='Thích']",
            ".//div[@role='button' and @aria-label='Like']",
            ".//div[@aria-label='Thích']",
            ".//div[@aria-label='Like']",
        ]

        like_button = locate_element(dialog, selectors, by=By.XPATH)
        if not like_button:
            raise RuntimeError("Like button not found in post dialog")

        like_button.click()
    except Exception:
        print("Like button not found or could not be clicked.")

def comment_on_post(dialog, comment_text):
    selectors = [
        ".//div[@role='textbox' and @contenteditable='true' and contains(@aria-label,'bình luận')]",
        ".//div[@role='textbox' and @contenteditable='true' and contains(@aria-label,'comment')]",
        ".//div[@role='textbox' and @contenteditable='true' and contains(@aria-label,'Write a comment')]",
        ".//div[@role='textbox' and @contenteditable='true' and contains(@aria-placeholder,'Bình luận')]",
        ".//div[@role='textbox' and @contenteditable='true' and contains(@aria-placeholder,'comment')]",
        ".//div[@role='textbox' and @contenteditable='true' and contains(@placeholder,'Write a comment')]",
        ".//div[@role='textbox' and @contenteditable='true' and contains(@aria-placeholder,'Write a comment')]",
    ]

    comment_box = locate_element(dialog, selectors, by=By.XPATH)

    if not comment_box:
        raise RuntimeError("Comment input box not found in post dialog")

    comment_box.click()
    time.sleep(0.5)
    comment_box.send_keys(comment_text)
    time.sleep(0.2)
    comment_box.send_keys(Keys.RETURN)

def share_post(dialog, content):
    selectors = [
        ".//div[@role='button' and @aria-label='Send this to friends or post it on your profile.']",
        ".//div[@role='button' and contains(@aria-label,'Send this to friends')]",
        ".//div[@role='button' and contains(@aria-label,'Gửi nội dung này cho bạn bè')]",
        ".//div[@role='button' and contains(@aria-label,'đăng lên trang cá nhân của bạn')]",
        ".//div[@role='button' and contains(@aria-label,'Chia sẻ')]",
        ".//div[@role='button' and contains(@aria-label,'Share')]",
    ]

    share_button = locate_element(dialog, selectors, by=By.XPATH)

    if not share_button:
        raise RuntimeError("Share button not found in post dialog")

    share_button.click()
    time.sleep(3)

    selectors = [
        ".//div[@role='textbox' and @contenteditable='true' and contains(@aria-label,'Say something about this...')]",
    ]

    content_box = locate_element(dialog, selectors, by=By.XPATH)
    if not content_box:
        raise RuntimeError("Share content input box not found in share dialog")
    content_box.click()
    time.sleep(0.5)
    content_box.send_keys(content)
    time.sleep(0.5)

    selectors = [
        ".//div[@role='button' and @aria-label='Share now']"
    ]

    share_now_button = locate_element(dialog, selectors, by=By.XPATH)
    if not share_now_button:
        raise RuntimeError("Share Now button not found in share dialog")
    share_now_button.click()
    time.sleep(3)

def post_to_group(driver, group_link, post_content, image_paths=None, log=print):
    image_paths = image_paths or []

    driver.get(group_link)
    time.sleep(5)

    placeholder_selectors = [
        "//span[contains(text(), 'Bạn viết gì đi')]/parent::div",
        "//span[contains(text(), 'Write something')]/parent::div",
        "//div[@role='button' and contains(@aria-label,'bạn viết gì đi')]",
        "//div[@role='button' and contains(@aria-label,'Write something')]",
    ]
    post_placeholder = locate_element(driver, placeholder_selectors, by=By.XPATH)
    if not post_placeholder:
        raise RuntimeError(f"Could not find post placeholder in group: {group_link}")

    post_placeholder.click()
    time.sleep(2)

    post_area_selectors = [
        "//div[contains(@aria-placeholder, 'Tạo bài viết công khai') and @contenteditable='true']",
        "//div[contains(@aria-placeholder, 'Write something') and @contenteditable='true']",
        "//div[@role='textbox' and @contenteditable='true' and @data-lexical-editor='true' and contains(@aria-placeholder, 'Bạn viết gì đi')]",
    ]
    post_area = locate_element(driver, post_area_selectors, by=By.XPATH)
    if not post_area:
        raise RuntimeError(f"Could not find post editor in group: {group_link}")

    post_area.send_keys(post_content)

    if image_paths:
        for image_path in image_paths:
            upload_input = locate_element(
                driver,
                [
                    "//input[@accept='image/*,image/heif,image/heic,video/*,video/mp4,video/x-m4v,video/x-matroska,.mkv,.avi,.wmv,.mov,.flv,.webm,.3gp,.3g2,.mts,.m2ts,.vob,.divx,.f4v,.ogv']",
                ],
                by=By.XPATH,
            )
            if not upload_input:
                raise RuntimeError(f"Could not find upload input in group: {group_link}")
            upload_input.send_keys(image_path)
            time.sleep(5)

    post_button = locate_element(
        driver,
        [
            "//div[@aria-label='Đăng']",
            "//div[@aria-label='Post']",
        ],
        by=By.XPATH,
    )
    if not post_button:
        raise RuntimeError(f"Could not find post button in group: {group_link}")

    post_button.click()
    time.sleep(5)
    log(f"Posted content to group: {group_link}")
    



