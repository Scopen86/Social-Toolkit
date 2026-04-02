import json
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from facebook_engine import *

def analyze_post_and_save_data(driver, url, log=print):
    dialog = get_dialog(driver, url)
    if not dialog:
        raise RuntimeError("Could not open post dialog")

    message = extract_post_message(dialog)
    log(f"Extracted post message:\n{message}")

    analysis = request_llm_analysis(message, log=log)
    save_data(analysis, filename="facebook_data.json", log=log)
    return analysis

def request_llm_analysis(message, log=print):
    log(f"LLM analysis requested for message: {message}")

    try:
        from google import genai
        from google.genai import types
    except ImportError as error:
        raise ImportError(
            "google-genai is required. Install it with: pip install google-genai"
        ) from error

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    model_id = "gemini-3.1-flash-lite-preview"

    prompt = (
        "Extract information from the message and return only valid JSON using this schema. "
        "Do not include markdown or extra keys.\\n\\n"
        f"Message:\\n{message}"
    )

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
    ]

    schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "From": types.Schema(type=types.Type.STRING, nullable=True),
            "Time": types.Schema(type=types.Type.STRING, nullable=True),
            "Reward": types.Schema(type=types.Type.STRING, nullable=True),
            "Requirements": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
            ),
            "End time": types.Schema(type=types.Type.STRING, nullable=True),
            "Additional notes": types.Schema(type=types.Type.STRING, nullable=True),
        },
        required=[
            "From",
            "Time",
            "Reward",
            "Requirements",
            "End time",
            "Additional notes",
        ],
    )

    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
        response_mime_type="application/json",
        response_schema=schema,
    )

    text_chunks = []
    try:
        for chunk in client.models.generate_content_stream(
            model=model_id,
            contents=contents,
            config=generate_content_config,
        ):
            if getattr(chunk, "text", None):
                text_chunks.append(chunk.text)
    except Exception as error:
        raise RuntimeError(f"Gemini API request failed: {error}") from error

    if not text_chunks:
        raise RuntimeError("Gemini API returned no text content")

    llm_text = "".join(text_chunks).strip()

    try:
        extracted = json.loads(llm_text)
    except json.JSONDecodeError:
        start = llm_text.find("{")
        end = llm_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError(f"Could not parse JSON from LLM response: {llm_text}")
        extracted = json.loads(llm_text[start : end + 1])

    requirements = extracted.get("Requirements")
    if requirements is None:
        requirements = []
    elif not isinstance(requirements, list):
        requirements = [str(requirements)]

    result = {
        "From": extracted.get("From"),
        "Time": extracted.get("Time"),
        "Reward": extracted.get("Reward"),
        "Requirements": requirements,
        "End time": extracted.get("End time"),
        "Additional notes": extracted.get("Additional notes"),
    }

    log("LLM analysis completed.")
    return result

def save_data(data, filename="facebook_data.json", log=print):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    log(f"Data saved to {filename}")

def main():
    url = "https://www.facebook.com/share/p/18C9fiya7N/"
    
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        # Test 1: Login
        print("\n=== TEST 1: Login ===")
        login(driver=driver, use_cookies=True)
        print("✓ Login test passed")
        
        # Test 2: Get Dialog
        print("\n=== TEST 2: Get Dialog ===")
        dialog = get_dialog(driver, url)
        if dialog:
            print("✓ Get dialog test passed")
        else:
            print("✗ Get dialog test failed - dialog is None")
            return
        
        # Test 3: Extract Post Message
        print("\n=== TEST 3: Extract Post Message ===")
        try:
            message = extract_post_message(dialog)
            print(f"✓ Extract post message test passed")
            print(f"Message preview: {message[:100]}...")
        except Exception as e:
            print(f"✗ Extract post message test failed: {e}")
        
        # Test 4: Like Post
        print("\n=== TEST 4: Like Post ===")
        try:
            like_post(dialog)
            print("✓ Like post test passed")
        except Exception as e:
            print(f"✗ Like post test failed: {e}")
        
        # Test 5: Comment on Post
        print("\n=== TEST 5: Comment on Post ===")
        try:
            comment_text = "a"
            comment_on_post(dialog, comment_text)
            print(f"✓ Comment on post test passed - posted: '{comment_text}'")
        except Exception as e:
            print(f"✗ Comment on post test failed: {e}")
        
        # Test 6: Share Post
        print("\n=== TEST 6: Share Post ===")
        try:
            share_post(dialog)
            print("✓ Share post test passed")
        except Exception as e:
            print(f"✗ Share post test failed: {e}")
        
        print("\n=== ALL TESTS COMPLETED ===")
        
    except Exception as e:
        print(f"Test execution error: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
