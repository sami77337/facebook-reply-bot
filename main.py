import requests
import time
import re
import json
import os

from database_manager import DatabaseManager
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# إعدادات الصفحة
load_dotenv()
PAGE_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
PAGE_ID = os.getenv("FB_PAGE_ID")

manager = DatabaseManager() 

# ملف الردود الموجود بجانب السكريبت
RESPONSES_FILE = os.path.join(os.path.dirname(__file__), "responses.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")
SEEN_FILE = os.path.join(os.path.dirname(__file__), "seen_comments.json")

if not PAGE_ACCESS_TOKEN or not PAGE_ID:
    raise ValueError("❌ Please set FB_ACCESS_TOKEN and FB_PAGE_ID in environment.")


def match_comment(comment, name, post_id=None):
        # Fetch relevant rules
        rules = manager.get_global_rules()
        if post_id:
            rules += manager.get_post_rules(post_id)

        matched_rules = []
        for rule in rules:
            try:
                if re.search(rule['patterns'], comment, re.IGNORECASE):
                    matched_rules.append(rule)
            except re.error as e:
                # Skip invalid regex
                print(f"Invalid regex in rule {rule['id']}: {e}")
                continue

        if not matched_rules:
            return None

        matched_rules.sort(key=lambda r: r['priority'], reverse=True)

        combined = []
        seen_responses = set()
        for rule in matched_rules:
            resp = rule['response']
            if resp:
                resp_text = resp.replace("{name}", name)
                if resp_text not in seen_responses:
                    combined.append(resp_text)
                    seen_responses.add(resp_text)

        return "\n".join(combined)

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

# إدارة التعليقات المعالجة
def load_seen_comments():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen_comments(seen_comments):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_comments), f, ensure_ascii=False, indent=2)

# Session واحد لكل الطلبات
session = requests.Session()
session.params = {"access_token": PAGE_ACCESS_TOKEN}

# جلب المنشورات
def get_all_posts(limit=50):
    posts = []
    url = f"https://graph.facebook.com/{PAGE_ID}/posts?fields=id,message&limit={limit}"
    while url:
        try:
            resp = session.get(url)
            resp.raise_for_status()
            data = resp.json()
            posts.extend(data.get("data", []))
            url = data.get("paging", {}).get("next")
        except Exception:
            break
    return posts

# جلب التعليقات
def get_all_comments(post_id):
    comments = []
    url = f"https://graph.facebook.com/{post_id}/comments?limit=100"
    while url:
        try:
            resp = session.get(url)
            resp.raise_for_status()
            data = resp.json()
            comments.extend(data.get("data", []))
            url = data.get("paging", {}).get("next")
        except Exception:
            break
    return comments

# الرد على التعليقات
def reply_to_comment(comment_id, message):
    if not message.strip():
        return False
    try:
        r = session.post(f"https://graph.facebook.com/{comment_id}/comments", data={"message": message})
        if r.status_code == 200:
            print(f"✅ Replied successfully to comment {comment_id}")
            with open(LOG_FILE, "a", encoding="utf-8") as log:
                log.write(f"{time.ctime()} - Replied to {comment_id}: {message}\n")
            return True
        return False
    except Exception:
        return False

# منطق الرد الخاص والعام
def get_post_patterns(post_id, responses_data):
    global_res = responses_data.get("global_responses", {})
    post_responses = responses_data.get("post_responses", {})

    full_id = str(post_id)
    short_id = full_id.split("_")[-1]

    post_specific = {}
    if full_id in post_responses:
        post_specific = post_responses[full_id]
    elif short_id in post_responses:
        post_specific = post_responses[short_id]

    return {**global_res, **post_specific}

def match_and_reply(post_id, comment, responses_data):
    comment_id = comment.get("id")
    message = comment.get("message", "").strip()
    if not message:
        return False
    patterns = get_post_patterns(post_id, responses_data)

    for pattern, reply in patterns.items():
        if re.search(pattern, message, re.IGNORECASE):
            return reply_to_comment(comment_id, reply)
    return False

def process_post(post, responses_data, seen_comments):
    post_id = post.get("id")
    comments = get_all_comments(post_id)
    for comment in comments:
        comment_id = comment.get("id")
        if comment_id not in seen_comments:
            if match_and_reply(post_id, comment, responses_data):
                seen_comments.add(comment_id)

# تشغيل البوت
def run_bot():
    print("🤖 Bot is running... (Ctrl + C to stop)")
    seen_comments = load_seen_comments()
    last_reload_time = 0
    reload_interval = 60

    with ThreadPoolExecutor(max_workers=5) as executor:
        while True:
            try:
                current_time = time.time()
                if current_time - last_reload_time > reload_interval:
                    responses_data = load_responses()
                    last_reload_time = current_time

                posts = get_all_posts(limit=50)
                futures = [executor.submit(process_post, post, responses_data, seen_comments) for post in posts]
                for future in as_completed(futures):
                    future.result()

                save_seen_comments(seen_comments)
                time.sleep(10)

            except Exception:
                time.sleep(30)

# نقطة البداية
if __name__ == "__main__":
    run_bot()
