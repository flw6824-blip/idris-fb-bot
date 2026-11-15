import time
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# إعدادات البوت والمدير
TELEGRAM_BOT_TOKEN = "9149355355:AAFLNSpWnYz9FMUiT-FbWfOKmV7KvuKxYRw"
ADMIN_ID = 6634523155  # الآيدي الخاص بك لاستقبال الإشعارات والتحكم

USER_DATA_FILE = "database.json"

def load_db():
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"subscriptions": {}, "tokens": {}, "accounts": {}, "codes": {}, "notified_users": []}

def save_db(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f)

db = load_db()

DEFAULT_FB_TOKEN = "EAAAAUaZA8jlABSx5iF2jj2ZAgVrXsNS04WYKmsStdkwlI7GkZBnBi8MIUCt1adqtGZA1CwSkeIUC2uUZC7BvFE8Pd3ZCZBLnV85HVXzWFbpmKzZAMZAgbMqupTnBbeI1WsTI2ITzRZAl4ZA8UR2Lq4KwkMRJSmX4eDH4LIvR6Gw12gpGHBsOBN4TgwVIgUUwMtAF4qhd2u1lQZDZD"

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    data = urllib.parse.urlencode(payload).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram API Error: {e}")

def extract_id(url):
    patterns = [
        r'posts/([0-9]+)',
        r'fbid=([0-9]+)',
        r'story_fbid=([0-9]+)',
        r'permalink/([0-9]+)',
        r'videos/([0-9]+)',
        r'profile\.php\?id=([0-9]+)',
        r'com/([a-zA-Z0-9\.]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    if url.isdigit():
        return url
    return None

def extract_facebook_token(email, password):
    try:
        url = "https://b-api.facebook.com/method/auth.login"
        payload = {
            "email": email,
            "password": password,
            "access_token": "350685531728%7C62f8ce9f74b12f84c153cc23479a4a3c",
            "format": "JSON",
            "generate_session_cookies": "1"
        }
        req = urllib.request.Request(url, data=urllib.parse.urlencode(payload).encode('utf-8'), headers={'User-Agent': 'Mozilla/5.0'})
        res = json.loads(urllib.request.urlopen(req, timeout=15).read().decode('utf-8'))
        if "access_token" in res:
            return res["access_token"]
    except Exception as e:
        print(f"Token Error: {e}")
    return None

def execute_facebook_task(user_id, task_type, target_id, count=1, extra_data=None):
    token = db["tokens"].get(str(user_id), DEFAULT_FB_TOKEN)
    success_count = 0
    for _ in range(count):
        try:
            if task_type == "followers":
                url = f"https://graph.facebook.com/{target_id}/subscribers"
                payload = {"access_token": token}
                req = urllib.request.Request(url, data=urllib.parse.urlencode(payload).encode('utf-8'))
                urllib.request.urlopen(req, timeout=10)
                success_count += 1
            elif task_type == "comment":
                url = f"https://graph.facebook.com/{target_id}/comments"
                payload = {"access_token": token, "message": extra_data}
                req = urllib.request.Request(url, data=urllib.parse.urlencode(payload).encode('utf-8'))
                res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
                if "id" in res: success_count += 1
            elif task_type == "share":
                url = f"https://graph.facebook.com/me/feed"
                payload = {"access_token": token, "link": f"https://www.facebook.com/{target_id}"}
                req = urllib.request.Request(url, data=urllib.parse.urlencode(payload).encode('utf-8'))
                res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
                if "id" in res: success_count += 1
            elif task_type == "reaction":
                url = f"https://graph.facebook.com/{target_id}/reactions"
                payload = {"access_token": token, "type": extra_data}
                req = urllib.request.Request(url, data=urllib.parse.urlencode(payload).encode('utf-8'))
                res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
                if res.get("success"): success_count += 1
        except Exception as e:
            print(f"FB Error: {e}")
        time.sleep(1)
    return success_count

def is_subscribed(user_id):
    if user_id == ADMIN_ID:
        return True
    sub_time = db["subscriptions"].get(str(user_id))
    if sub_time:
        if datetime.now().timestamp() < float(sub_time):
            return True
        else:
            del db["subscriptions"][str(user_id)]
            save_db(db)
    return False

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?timeout=30"
    if offset:
        url += f"&offset={offset}"
    try:
        req = urllib.request.Request(url)
        return json.loads(urllib.request.urlopen(req, timeout=35).read().decode('utf-8'))
    except:
        return None

def main():
    print("تم تشغيل البوت بنجاح...")
    offset = None
    user_states = {}

    while True:
        updates = get_updates(offset)
        if updates and "result" in updates:
            for update in updates["result"]:
                offset = update["update_id"] + 1

                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"].get("text", "")
                    user = update["message"]["from"]
                    user_id = user["id"]
                    first_name = user.get("first_name", "مستخدم")
                    username = f"@{user.get('username')}" if user.get("username") else "بدون معرف"

                    if user_id != ADMIN_ID and str(user_id) not in db.get("notified_users", []):
                        db.setdefault("notified_users", []).append(str(user_id))
                        save_db(db)
                        admin_notification = (
                            f"🚨 **دخول مستخدم جديد!**\n\n"
                            f"👤 الإسم: `{first_name}`\n"
                            f"🆔 الآيدي: `{user_id}`\n"
                            f"🔗 اليوزر: {username}\n\n"
                            f"للتفعيل أرسل:\n`/gencode الكود 10`"
                        )
                        send_telegram_message(ADMIN_ID, admin_notification)

                    if user_id == ADMIN_ID:
                        if text.startswith("/gencode "):
                            parts = text.split()
                            code = parts[1]
                            minutes = int(parts[2]) if len(parts) > 2 else 10
                            db["codes"][code] = minutes
                            save_db(db)
                            send_telegram_message(chat_id, f"✅ تم إنشاء الكود `{code}` صالح لمدة `{minutes}` دقيقة.")
                            continue

                    if not is_subscribed(user_id):
                        if text.startswith("/redeem "):
                            code = text.split()[1]
                            if code in db["codes"]:
                                minutes = db["codes"][code]
                                expire_time = datetime.now() + timedelta(minutes=minutes)
                                db["subscriptions"][str(user_id)] = expire_time.timestamp()
                                del db["codes"][code]
                                save_db(db)
                                send_telegram_message(chat_id, f"🎉 مبروك! تم تفعيل اشتراكك بنجاح لمدة {minutes} دقائق.")
                            else:
                                send_telegram_message(chat_id, "❌ الكود غير صالح أو تم استخدامه مسبقاً.")
                            continue

                        welcome_unsub_msg = (
                            "✨ **مرحباً بك في لوحة إدريس لتزويد السوشال ميديا المزخرفة والأسطورية!** 🚀\n\n"
                            "⛔ **عذراً، حسابك غير مفعل حالياً.**\n"
                            "💬 لتفعيل حسابك والحصول على صلاحية استخدام الخدمات، يرجى مراسلة المطور مباشرة عبر الرابط التالي:\n"
                            "👉 https://t.me/E_D_RS\n\n"
                            "🔑 إذا كان لديك كود تفعيل، أرسله بهذا الشكل:\n"
                            "`/redeem كود_التفعيل`"
                        )
                        send_telegram_message(chat_id, welcome_unsub_msg)
                        continue

                    if text == "/start":
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "👤 ⦗ زيادة متابعين ⦗", "callback_data": "btn_followers"}],
                                [{"text": "💬 ⦗ إرسال تعليقات ⦗", "callback_data": "btn_comment"}],
                                [{"text": "🔄 ⦗ شير منشور ⦗", "callback_data": "btn_share"}],
                                [{"text": "❤️ ⦗ إرسال تفاعلات ⦗", "callback_data": "btn_reaction"}],
                                [{"text": "🔑 ⦗ إضافة توكن فيسبوك ⦗", "callback_data": "btn_set_token"}],
                                [{"text": "⚡ ⦗ استخراج توكن (بريد وكلمة سر) ⦗", "callback_data": "btn_extract_token"}],
                                [{"text": "➕ ⦗ إضافة حساب جديد ⦗", "callback_data": "btn_add_account"}]
                            ]
                        }
                        start_msg = (
                            "🔥 **أهلاً بك مجدداً في لوحة إدريس الأسطورية لتزويد السوشال ميديا!** 🌟\n\n"
                            "حسابك مفعل وجاهز بالكامل للأوامر.\n"
                            "اختر الخدمة المطلوبة من الأزرار أدناه:"
                        )
                        send_telegram_message(chat_id, start_msg, keyboard)

                    elif chat_id in user_states:
                        state = user_states[chat_id]

                        if state == "waiting_token":
                            db["tokens"][str(user_id)] = text.strip()
                            save_db(db)
                            send_telegram_message(chat_id, "✅ تم حفظ التوكن بنجاح!")
                            del user_states[chat_id]

                        elif state == "waiting_credentials":
                            parts = text.split()
                            if len(parts) >= 2:
                                send_telegram_message(chat_id, "⏳ جاري استخراج التوكن...")
                                token = extract_facebook_token(parts[0], parts[1])
                                if token:
                                    db["tokens"][str(user_id)] = token
                                    save_db(db)
                                    send_telegram_message(chat_id, f"✅ تم استخراج وحفظ التوكن بنجاح:\n`{token}`")
                                else:
                                    send_telegram_message(chat_id, "❌ فشل الاستخراج. تأكد من البيانات.")
                            del user_states[chat_id]

                        elif state == "waiting_account":
                            parts = text.split()
                            if len(parts) >= 2:
                                db["accounts"][str(user_id)] = {"email": parts[0], "password": parts[1]}
                                token = extract_facebook_token(parts[0], parts[1])
                                if token:
                                    db["tokens"][str(user_id)] = token
                                    save_db(db)
                                    send_telegram_message(chat_id, "✅ تمت إضافة الحساب وتفعيل توكنه!")
                            del user_states[chat_id]

                        else:
                            parts = text.split()
                            target_id = extract_id(parts[0])
                            count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
                            extra = parts[2] if len(parts) > 2 else "LIKE"

                            if not target_id:
                                send_telegram_message(chat_id, "❌ الرابط غير صحيح.")
                                del user_states[chat_id]
                                continue

                            send_telegram_message(chat_id, f"⏳ جاري تنفيذ الخدمة ({state})...")
                            executed = execute_facebook_task(user_id, state, target_id, count, extra)
                            send_telegram_message(chat_id, f"✅ تم التنفيذ بنجاح ({executed}/{count}).")
                            del user_states[chat_id]

                elif "callback_query" in update:
                    query = update["callback_query"]
                    chat_id = query["message"]["chat"]["id"]
                    user_id = query["from"]["id"]
                    data = query["data"]

                    if not is_subscribed(user_id):
                        send_telegram_message(chat_id, "⛔ حسابك غير مفعل. يرجى مراسلة المطور عبر https://t.me/E_D_RS للتفعيل.")
                        continue

                    if data == "btn_set_token":
                        user_states[chat_id] = "waiting_token"
                        send_telegram_message(chat_id, "🔑 أرسل توكن فيسبوك الخاص بك:")
                    elif data == "btn_extract_token":
                        user_states[chat_id] = "waiting_credentials"
                        send_telegram_message(chat_id, "⚡ أرسل **البريد وكلمة المرور** مفصولين بمسافة:")
                    elif data == "btn_add_account":
                        user_states[chat_id] = "waiting_account"
                        send_telegram_message(chat_id, "➕ أرسل **البريد وكلمة المرور** للحساب الجديد:")
                    else:
                        service_map = {"btn_followers": "followers", "btn_comment": "comment", "btn_share": "share", "btn_reaction": "reaction"}
                        if data in service_map:
                            user_states[chat_id] = service_map[data]
                            send_telegram_message(chat_id, "📝 أرسل الآن **الرابط والعدد** (مثال: `رابط_المنشور 5`):")

        time.sleep(1)

if __name__ == "__main__":
    main()
