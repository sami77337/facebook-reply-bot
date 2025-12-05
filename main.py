import time
import os
import json

from bot_manager import BotManager
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# إعدادات الصفحة
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
def run_bot():    
    print("🤖 Bot is running... (Ctrl + C to stop)")
    seen_comments = load_seen_comments()
    last_reload_time = 0
    reload_interval = 60

    with ThreadPoolExecutor(max_workers=5) as executor:
        while True:
            try:
                botManager = BotManager()
                current_time = time.time()
                if current_time - last_reload_time > reload_interval:
                    responses_data = load_responses()
                    last_reload_time = current_time

                posts = botManager.get_all_posts(limit=50)
                futures = [executor.submit(botManager.process_post, post, responses_data, seen_comments) for post in posts]
                for future in as_completed(futures):
                    future.result()

                save_seen_comments(seen_comments)
                time.sleep(10)

            except Exception:
                time.sleep(30)

# نقطة البداية
if __name__ == "__main__":
    run_bot()
