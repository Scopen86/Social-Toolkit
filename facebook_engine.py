from asyncio import log
import json
import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def locate_element(driver, selectors, by=By.CSS_SELECTOR):
    for selector in selectors:
        elements = driver.find_elements(by, selector)
        visible_elements = [el for el in elements if el.is_displayed() and el.is_enabled()]
        if visible_elements:
            return visible_elements[0]
    return None

def login(driver, log=print, use_cookies=False):
    credential_file = "facebook_credentials.txt"
    cookies_file = "facebook_cookies.json"

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
    input("Press Enter after login is complete...")

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

def get_dialog(driver, url):
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

def share_post(dialog):
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

