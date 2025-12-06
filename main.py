import time
import os
import json

from bot_manager import BotManager
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

if os.getenv("GITHUB_ACTIONS") == "true":
    PAGE_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
    PAGE_ID = os.getenv("FB_PAGE_ID")
else:
    from dotenv import load_dotenv
    load_dotenv()
    PAGE_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
    PAGE_ID = os.getenv("FB_PAGE_ID")

# ملف الردود الموجود بجانب السكريبت
RESPONSES_FILE = os.path.join(os.path.dirname(__file__), "responses.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")
SEEN_FILE = os.path.join(os.path.dirname(__file__), "seen_comments.json")

if not PAGE_ACCESS_TOKEN or not PAGE_ID:
    raise ValueError("❌ Please set FB_ACCESS_TOKEN and FB_PAGE_ID in environment.")

# إدارة التعليقات المعالجة
def load_seen_comments():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen_comments(seen_comments):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_comments), f, ensure_ascii=False, indent=2)

        # تحميل الردود
def load_responses():
    if not os.path.exists(RESPONSES_FILE):
        default_data = {"global_responses": {}, "post_responses": {}}
        with open(RESPONSES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data
    with open(RESPONSES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("📂 Responses file loaded successfully:", os.path.abspath(RESPONSES_FILE))
    return data

# تشغيل البوت
def run_bot_once():
    seen_comments = load_seen_comments()
    
    try:
        botManager = BotManager(access_token=PAGE_ACCESS_TOKEN, page_id=PAGE_ID)
        responses_data = load_responses()        
        posts = botManager.get_all_posts(limit=50) 
        print(f"📊 Fetched {len(posts)} posts from the page.")
        if not posts:
            return 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(botManager.process_post, post, responses_data, seen_comments) for post in posts]

            processed_count = 0
            for future in as_completed(futures):
                try:
                    future.result(timeout=300)
                    processed_count += 1                    
                    print(f"📊 Progress: {processed_count}/{len(posts)} posts processed")
                except Exception as e:
                    print(f"Error {e}")

        save_seen_comments(seen_comments)
        return processed_count
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        raise

def main():
    start_time = time.time()
    print(f"started at {time.ctime(start_time)}")
    
    try:
        posts_processed = run_bot_once()
        end_time = time.time()
        duration = end_time - start_time

        print(f"completed in {duration:.2f} seconds")
        print(f"📊 Total posts processed: {posts_processed}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()
