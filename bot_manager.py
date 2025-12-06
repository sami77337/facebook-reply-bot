import requests
import time
import re
import os

#from database_manager import DatabaseManager

RESPONSES_FILE = os.path.join(os.path.dirname(__file__), "responses.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")
SEEN_FILE = os.path.join(os.path.dirname(__file__), "seen_comments.json")

class BotManager:
    def __init__(self, access_token=None, page_id=None):
        self.access_token = access_token or os.getenv("FB_ACCESS_TOKEN")
        self.page_id = page_id or os.getenv("FB_PAGE_ID")
        #self.manager = DatabaseManager()
        self.session = requests.Session()
        self.session.params = {"access_token": self.access_token}
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; AutoResponseBot/1.0)', 'Accept': 'application/json'})

    # جلب المنشورات
    def get_all_posts(self, limit=50):
        posts = []
        url = f"https://graph.facebook.com/{self.page_id}/posts?fields=id,message&limit={limit}"
        print(f"🔄 Fetching posts from URL: {url}")
        while url:
            try:
                resp = self.session.get(url)
                resp.raise_for_status()
                data = resp.json()
                posts.extend(data.get("data", []))
                url = data.get("paging", {}).get("next")
            except Exception as e:
                print("❌ Error fetching posts. ", e)
                break
        return posts

    # جلب التعليقات
    def get_all_comments(self, post_id):
        comments = []
        url = f"https://graph.facebook.com/{post_id}/comments?limit=100"
        print(f"🔄 Fetching comments from URL: {url}")
        while url:
            try:
                resp = self.session.get(url)
                resp.raise_for_status()
                data = resp.json()
                comments.extend(data.get("data", []))
                url = data.get("paging", {}).get("next")
            except Exception:
                break
        return comments

    # الرد على التعليقات
    def reply_to_comment(self, comment_id, message):
        if not message.strip():
            return False
        try:
            print(f"✅ Replying to comment {comment_id}")
            r = self.session.post(f"https://graph.facebook.com/{comment_id}/comments", data={"message": message})
            if r.status_code == 200:
                print(f"✅ Replied successfully to comment {comment_id}")
                with open(LOG_FILE, "a", encoding="utf-8") as log:
                    log.write(f"{time.ctime()} - Replied to {comment_id}: {message}\n")
                return True
            return False
        except Exception:
            return False

    def match_and_reply(self, post_id, comment, responses_data):        
        comment_id = comment.get("id")
        message = comment.get("message", "").strip()
        if not message:
            return False
        patterns = get_post_patterns(post_id, responses_data)
    
        for pattern, reply in patterns.items():
            if re.search(pattern, message, re.IGNORECASE):
                return self.reply_to_comment(comment_id, reply)
        return False

    def process_post(self, post, responses_data, seen_comments):
        print(f"🔍 Processing post {post.get('id')}")
        post_id = post.get("id")
        comments = self.get_all_comments(post_id)
        for comment in comments:
            comment_id = comment.get("id")
            if comment_id not in seen_comments:
                if self.match_and_reply(post_id, comment, responses_data):
                    seen_comments.add(comment_id)

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