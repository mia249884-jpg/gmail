import imaplib
import email as email_lib
import requests
import time
import random
import string
import json
import os
import re
import threading
import sys
import io
from datetime import datetime
import html
# ANSI color codes for colorful terminal output
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
MAGENTA= "\033[95m"
BLUE   = "\033[94m"
WHITE  = "\033[97m"
DIM    = "\033[2m"

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# ==========================
# CONFIG
# ==========================
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "bot_token": "8695687684:AAHNbbptzR_eFYm3aFiTwkZXK5RQk6_lJgg",
    "admin_ids": [576819773],
    "gmail_list": ["rukuplusfarhantelegramotobot@gmail.com", "xazxmdrukuplutelegramotpbot@gmail.com", "rukuvaitelegramotpbot@gmail.com", "rukuvaitelegramtgotpbot@gmail.com", "hdnsjsksgskajsysgdiduhdbsu@gmail.com", "rukualuotpbotvsksggens@gmail.com"
],
    "imap_passwords": {
        "Gmail address": "Akram@890",
        
    },    "force_join": {"enabled": False, "channels": []},
    "auto_delete": {"user_seconds": 0, "group_seconds": 0},
    "otp_group": {"enabled": True, "link": "https://t.me/Gmail_otp_botx"},
    "group_bot": {
        "enabled": True,
        "token": "8695687684:AAHNbbptzR_eFYm3aFiTwkZXK5RQk6_lJgg",
        "group_id": "-1003939455952",
        "send_all_mail": True
    },
    "blocked_users": [],
    "sheet_title": "Alias Bot Data",
    "ad_button": {
        "enabled": True,
        "text": "TG Sell Bot",
        "url": "https://t.me/Virtual_Nuumberr_bot?startapp=Kldt1HRF"
    }
}

_config = None

def load_config():
    global _config
    if _config is not None:
        return _config
    if not os.path.exists(CONFIG_FILE):
        _config = DEFAULT_CONFIG.copy()
        save_config(_config)
        return _config
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        for key, val in DEFAULT_CONFIG.items():
            if key not in cfg:
                cfg[key] = val
        if "group_bot" in cfg:
            for k, v in DEFAULT_CONFIG["group_bot"].items():
                if k not in cfg["group_bot"]:
                    cfg["group_bot"][k] = v
        if "ad_button" in cfg:
            for k, v in DEFAULT_CONFIG["ad_button"].items():
                if k not in cfg["ad_button"]:
                    cfg["ad_button"][k] = v
        _config = cfg
        return _config
    except:
        return DEFAULT_CONFIG

def save_config(cfg):
    global _config
    _config = cfg
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ==========================
# LOCAL DATA STORAGE
# ==========================

# In-memory cache — alias/tag data local এ থাকে
_cache     = {}  # chat_id(str) -> {tag, email, tag_history, username, full_name, ...}
_tag_index = {}  # tag.lower() -> chat_id(str)

# Local JSON files
ALIAS_FILE = "alias_data.json"   # chat_id -> {tag, email, tag_history, username, full_name, joined_at}

def _load_alias_file():
    if not os.path.exists(ALIAS_FILE): return {}
    with open(ALIAS_FILE) as f: return json.load(f)

def _save_alias_file(data):
    with open(ALIAS_FILE, "w") as f: json.dump(data, f, indent=2)

def load_cache():
    """Local alias file থেকে memory তে load করে"""
    global _cache, _tag_index
    _cache = {}
    _tag_index = {}
    try:
        alias_data = _load_alias_file()
        for cid, adata in alias_data.items():
            _cache[cid] = {
                "chat_id":     cid,
                "username":    adata.get("username", ""),
                "full_name":   adata.get("full_name", ""),
                "joined_at":   adata.get("joined_at", ""),
                "tag":         adata.get("tag", ""),
                "email":       adata.get("email", ""),
                "tag_history": adata.get("tag_history", []),
                "row":         None
            }
            for t in adata.get("tag_history", []):
                _tag_index[t.lower()] = cid
            if adata.get("tag"):
                _tag_index[adata["tag"].lower()] = cid
        print(f"{GREEN}{BOLD}✅ Cache loaded:{RESET} {WHITE}{len(_cache)} users{RESET}")
    except Exception as e:
        print(f"{RED}[Cache load] {e}{RESET}")

def save_alias_local(cid):
    """Alias + user data local file এ save করে"""
    data = _cache.get(str(cid), {})
    alias_data = _load_alias_file()
    alias_data[str(cid)] = {
        "tag":         data.get("tag", ""),
        "email":       data.get("email", ""),
        "tag_history": data.get("tag_history", []),
        "username":    data.get("username", ""),
        "full_name":   data.get("full_name", ""),
        "joined_at":   data.get("joined_at", "")
    }
    _save_alias_file(alias_data)

def register_user(chat_id, username, full_name):
    """User প্রথমবার /start দিলে local file এ save করে"""
    cid = str(chat_id)
    if cid in _cache:
        return  # already registered
    joined_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "chat_id":     cid,
        "username":    username,
        "full_name":   full_name,
        "joined_at":   joined_at,
        "tag":         "",
        "email":       "",
        "tag_history": [],
        "row":         None
    }
    _cache[cid] = data
    # Background: local file এ save করো
    threading.Thread(target=lambda: save_alias_local(cid), daemon=True).start()

def get_user_data(chat_id):
    return _cache.get(str(chat_id))

def update_user_alias(chat_id, tag, email):
    """User এর alias update করে cache + local file এ (sheet এ না)"""
    cid  = str(chat_id)
    data = _cache.get(cid, {})
    history = data.get("tag_history", [])
    if tag.lower() not in [t.lower() for t in history]:
        history.append(tag)
    history = history[-10:]
    data["tag"]         = tag
    data["email"]       = email
    data["tag_history"] = history
    _cache[cid] = data
    _tag_index[tag.lower()] = cid
    # Local file এ save (background)
    threading.Thread(target=lambda: save_alias_local(cid), daemon=True).start()

def find_user_by_tag(tag):
    """tag থেকে chat_id বের করো — O(1) memory lookup"""
    cid = _tag_index.get(tag.lower())
    if cid:
        try: return int(cid)
        except: pass
    return None

def get_all_users():
    return list(_cache.values())

# ==========================
# TELEGRAM
# ==========================
def get_bot_token():
    return load_config().get("bot_token", "")

last_update_id = 0
_processed_updates = set()
_user_locks = {}

def get_user_lock(chat_id):
    if chat_id not in _user_locks:
        _user_locks[chat_id] = threading.Lock()
    return _user_locks[chat_id]

_session = requests.Session()

def api(method, payload=None, params=None):
    token = get_bot_token()
    if not token: return {}
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if payload: 
            r = _session.post(url, json=payload, timeout=25)
        else:       
            # timeout parameter in params is for server-side long polling.
            # we set requests timeout slightly higher (40s) than the 30s long poll.
            r = _session.get(url, params=params, timeout=40)
        return r.json()
    except Exception as e:
        print(f"{RED}[API] {e}{RESET}")
        return {}

def send_msg(chat_id, text, markup=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if markup: p["reply_markup"] = markup
    return api("sendMessage", p)

def edit_msg(chat_id, msg_id, text, markup=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": parse_mode}
    if markup: p["reply_markup"] = markup
    return api("editMessageText", p)

def answer_cb(cb_id, text="", alert=False):
    api("answerCallbackQuery", {"callback_query_id": cb_id, "text": text, "show_alert": alert})

def delete_msg(chat_id, msg_id):
    api("deleteMessage", {"chat_id": chat_id, "message_id": msg_id})

def update_telegram_menu_button():
    menu_btn = {"type": "default"}
    r = api("setChatMenuButton", {"menu_button": menu_btn})
    return r

# ==========================
# ALIAS SYSTEM
# ==========================
def generate_tag():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def get_user_base_email(chat_id):
    cfg  = load_config()
    data = get_user_data(chat_id)
    if data and data.get("email") and data["email"] in cfg["gmail_list"]:
        return data["email"]
    if not cfg["gmail_list"]: return None
    chosen = random.choice(cfg["gmail_list"])
    return chosen

def randomize_local(local):
    """gmail local part এর case random করে — প্রতিবার আলাদা দেখাবে"""
    return ''.join(c.upper() if random.choice([True, False]) else c.lower() for c in local)

def get_or_create_alias(chat_id):
    data = get_user_data(chat_id)
    if data and data.get("tag") and data.get("email"):
        local, domain = data["email"].split("@")
        return f"{randomize_local(local)}+{data['tag']}@{domain}"
    # নতুন alias তৈরি করো
    base_email = get_user_base_email(chat_id)
    if not base_email: return None
    tag = generate_tag()
    update_user_alias(chat_id, tag, base_email)
    local, domain = base_email.split("@")
    return f"{randomize_local(local)}+{tag}@{domain}"

def regenerate_alias(chat_id, new_base_email=None):
    cfg  = load_config()
    if not new_base_email:
        gmails = cfg.get("gmail_list", [])
        new_base_email = random.choice(gmails) if gmails else get_user_base_email(chat_id)
    tag = generate_tag()
    update_user_alias(chat_id, tag, new_base_email)
    local, domain = new_base_email.split("@")
    return f"{randomize_local(local)}+{tag}@{domain}"

# user alias message_id — local dict (in-memory only, no need to persist)
_alias_msg_ids = {}  # chat_id -> message_id

def alias_keyboard(alias):
    cfg = load_config()
    kb  = [
        [{"text": alias, "copy_text": {"text": alias}}],
        [{"text": "🔄 Refresh", "callback_data": "refresh_alias"},
         {"text": "🔀 Change",  "callback_data": "next_alias"}]
    ]
    
    ad = cfg.get("ad_button", {})
    if ad.get("enabled") and ad.get("url"):
        kb.append([{"text": ad.get("text", "TG Sell Bot"), "url": ad.get("url")}])

    if cfg["otp_group"]["enabled"]:
        kb.append([{"text": "📨 OTP GROUP", "url": cfg["otp_group"]["link"]}])
    return {"inline_keyboard": kb}

def send_alias(chat_id):
    alias = get_or_create_alias(chat_id)
    if not alias:
        send_msg(chat_id, "⚠️ কোনো Gmail পাওয়া যায়নি।"); return
    old_id = _alias_msg_ids.get(chat_id)
    if old_id:
        res = edit_msg(chat_id, old_id,
                       "নিচের বাটনে ক্লিক করলেই copy হয়ে যাবে 👇",
                       markup=alias_keyboard(alias))
        if res.get("ok"): return
        _alias_msg_ids.pop(chat_id, None)
    res = send_msg(chat_id,
                   "নিচের বাটনে ক্লিক করলেই copy হয়ে যাবে 👇",
                   markup=alias_keyboard(alias))
    if res.get("ok"):
        _alias_msg_ids[chat_id] = res["result"]["message_id"]

def send_alias_new(chat_id):
    """প্রতিবার /start এ সম্পূর্ণ নতুন message পাঠায়, নতুন alias সহ"""
    cfg    = load_config()
    gmails = cfg.get("gmail_list", [])
    new_base = random.choice(gmails) if gmails else None
    alias = regenerate_alias(chat_id, new_base_email=new_base)
    if not alias:
        send_msg(chat_id, "⚠️ কোনো Gmail পাওয়া যায়নি।"); return
    res = send_msg(chat_id,
                   "নিচের বাটনে ক্লিক করলেই copy হয়ে যাবে 👇",
                   markup=alias_keyboard(alias))
    if res.get("ok"):
        _alias_msg_ids[chat_id] = res["result"]["message_id"]

def change_alias(chat_id, msg_id):
    cfg    = load_config()
    gmails = cfg.get("gmail_list", [])
    new_base = random.choice(gmails) if gmails else None
    alias  = regenerate_alias(chat_id, new_base_email=new_base)
    _alias_msg_ids[chat_id] = msg_id
    edit_msg(chat_id, msg_id,
             "নিচের বাটনে ক্লিক করলেই copy হয়ে যাবে 👇",
             markup=alias_keyboard(alias))

# ==========================
# OTP
# ==========================
def extract_otp(text):
    m = re.search(r"\b\d{4,8}\b", text)
    return m.group() if m else None

def extract_tag(to_field):
    m = re.search(r'\+([^@\s]+)@', to_field)
    return m.group(1) if m else None

_sent_otps = {}  # chat_id -> {otp: timestamp}

def is_duplicate_otp(chat_id, otp):
    key = str(chat_id)
    now = time.time()
    if key not in _sent_otps: _sent_otps[key] = {}
    _sent_otps[key] = {k: v for k, v in _sent_otps[key].items() if now - v < 60}
    if otp in _sent_otps[key]: return True
    _sent_otps[key][otp] = now
    return False

def parse_time_input(text):
    """M1 -> 60, S35 -> 35, 0 -> disabled"""
    text = text.strip().upper()
    if text.startswith("M"):
        try: return int(text[1:]) * 60
        except: return 0
    elif text.startswith("S"):
        try: return int(text[1:])
        except: return 0
    return 0

def auto_delete_msg(token, chat_id, msg_id, after_seconds):
    """নির্দিষ্ট সময় পরে message delete করে"""
    def _delete():
        time.sleep(after_seconds)
        try:
            if token:
                # Group bot এর message
                _session.post(
                    f"https://api.telegram.org/bot{token}/deleteMessage",
                    json={"chat_id": chat_id, "message_id": msg_id},
                    timeout=15
                )
            else:
                # Main bot এর message
                api("deleteMessage", {"chat_id": chat_id, "message_id": msg_id})
        except: pass
    threading.Thread(target=_delete, daemon=True).start()

def send_otp_to_user(chat_id, otp, tag=None, service="OTP"):
    if is_duplicate_otp(chat_id, otp): return
    tag_esc = html.escape(tag) if tag else ""
    tag_line = f" {tag_esc}" if tag else ""
    res = send_msg(
        chat_id,
        f"📨 <b>New {service}</b>{tag_line}\n\n🔐 <b>Code:</b> <code>{html.escape(otp)}</code>",
        markup={"inline_keyboard": [[
            {"text": f"🔑 {otp}", "copy_text": {"text": otp}}
        ]]}
    )
    # Auto delete
    cfg = load_config()
    secs = cfg.get("auto_delete", {}).get("user_seconds", 0)
    if secs and res.get("ok"):
        auto_delete_msg(None, chat_id, res["result"]["message_id"], secs)

# ==========================
# GROUP BOT
# Telegram Quote format = HTML <blockquote>
# ==========================
def send_mail_to_group(subject, from_, to_, body, otp=None, tag=None):
    cfg = load_config()
    gb  = cfg.get("group_bot", {})
    if not gb.get("enabled") or not gb.get("token") or not gb.get("group_id"):
        return
    if not otp and not gb.get("send_all_mail", True):
        return

    try: group_id = int(gb["group_id"])
    except: group_id = gb["group_id"]
    token = gb["token"]

    if otp:
        tag_esc = html.escape(tag) if tag else ""
        tag_line = f" {tag_esc}" if tag else ""
        text = f"📨 <b>New OTP</b>{tag_line}\n\n🔐 <b>Code:</b> <code>{html.escape(otp)}</code>"
        markup = {"inline_keyboard": [[
            {"text": f"🔑 {otp}", "copy_text": {"text": otp}}
        ]]}
    else:
        # from_ থেকে শুধু নাম বের করো
        from_name = re.sub(r'<[^>]+>', '', from_).strip().strip('"').strip("'") or from_

        # Body পরিষ্কার করো
        body_clean = body.strip().replace("\r\n", "\n").replace("\r", "\n")
        # খালি lines কমাও
        body_clean = re.sub(r'\n{3,}', '\n\n', body_clean)

        # HTML escaping
        subject_esc = html.escape(subject)
        from_name_esc = html.escape(from_name)
        body_esc = html.escape(body_clean[:2000])
        tag_esc = html.escape(tag) if tag else ""
        
        tag_line = f"\nTag: {tag_esc}" if tag else ""

        # Quote block — Telegram HTML blockquote
        quote_content = (
            f"Subject: {subject_esc}"
            f"{tag_line}"
            f"\nFrom: {from_name_esc}"
        )

        # Message = header + blockquote + full body
        text = (
            f"📧 <b>New Mail</b>\n\n"
            f"<blockquote>{quote_content}</blockquote>"
        )
        if body_clean:
            text += f"\n\n{body_esc}"

        markup = None

    try:
        r = _session.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": group_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": markup
            },
            timeout=20
        ).json()
        if not r.get("ok"):
            print(f"{RED}[Group bot Error] {r.get('description')}{RESET}")
            return
        # Auto delete group message
        cfg2  = load_config()
        gsecs = cfg2.get("auto_delete", {}).get("group_seconds", 0)
        if gsecs and r.get("result"):
            auto_delete_msg(token, group_id, r["result"]["message_id"], gsecs)
    except Exception as e:
        print(f"{RED}[Group bot Exception] {e}{RESET}")

# ==========================
# PROCESS UNSEEN EMAILS
# ==========================
def process_unseen(mail_conn, base_email):
    try:
        mail_conn.select("inbox")
        status, msgs = mail_conn.search(None, 'UNSEEN')
        if status != "OK" or not msgs[0].strip(): return
        last = _last_uid.get(base_email, 0)
        for num in msgs[0].split():
            # Bot start এর আগের mail skip
            if last and int(num) <= last:
                mail_conn.store(num, '+FLAGS', '\\Seen')
                continue
            status2, data = mail_conn.fetch(num, "(RFC822)")
            if status2 != "OK": continue
            msg     = email_lib.message_from_bytes(data[0][1])
            from_   = msg.get("from", "")
            to_     = msg.get("to", "")
            subject = msg.get("subject", "")
            body    = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            otp = extract_otp(subject + "\n" + body)
            tag = extract_tag(to_)

            # Telegram OTP → user কে পাঠাও
            if "noreply@telegram.org" in from_.lower() and otp and tag:
                user = find_user_by_tag(tag)
                if user:
                    send_otp_to_user(user, otp, tag=tag, service="Telegram OTP")

            # IMO OTP → user কে পাঠাও
            if ("otp-noreply" in from_.lower() or "imo verification code" in subject.lower()) and otp and tag:
                user = find_user_by_tag(tag)
                if user:
                    send_otp_to_user(user, otp, tag=tag, service="IMO OTP")

            # WhatsApp OTP → user কে পাঠাও
            if ("whatsapp.com" in from_.lower() or "whatsapp" in subject.lower()) and otp and tag:
                user = find_user_by_tag(tag)
                if user:
                    send_otp_to_user(user, otp, tag=tag, service="WhatsApp OTP")

            # Group এ পাঠাও (সব mail)
            send_mail_to_group(subject, from_, to_, body, otp=otp, tag=tag)

            # এই mail process হয়েছে — uid update করো
            _last_uid[base_email] = max(_last_uid.get(base_email, 0), int(num))
            mail_conn.store(num, '+FLAGS', '\\Seen')
    except Exception as e:
        print(f"{YELLOW}[IMAP] {e}{RESET}")

# ==========================
# IMAP THREAD
# ==========================
# Bot start এর পর প্রতিটা gmail এর highest UID track করি
# এই UID এর আগের সব mail ignore হবে
_last_uid = {}  # base_email -> last processed UID

def imap_thread(base_email, app_password):
    while True:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(base_email, app_password)
            mail.select("inbox")

            # প্রথমবার — শুধু current highest UID mark করো, process করো না
            if base_email not in _last_uid:
                status, msgs = mail.search(None, 'ALL')
                if status == "OK" and msgs[0].strip():
                    all_uids = msgs[0].split()
                    _last_uid[base_email] = int(all_uids[-1])
                else:
                    _last_uid[base_email] = 0

            noop_counter = 0
            while True:
                time.sleep(3)
                noop_counter += 1
                mail.select("inbox")
                process_unseen(mail, base_email)
                if noop_counter >= 100:
                    mail.noop()
                    noop_counter = 0
        except Exception:
            try: mail.logout()
            except: pass
            time.sleep(5)

# ==========================
# FORCE JOIN
# ==========================
def check_joined(chat_id):
    cfg = load_config()
    if not cfg["force_join"]["enabled"]: return True, []
    missing = []
    for ch in cfg["force_join"]["channels"]:
        try:
            part = ch["link"].strip().rstrip("/").split("t.me/")[-1]
            if part.startswith("+"): continue
            r = api("getChatMember", {"chat_id": "@"+part, "user_id": chat_id})
            if r.get("result",{}).get("status","left") in ["left","kicked"]:
                missing.append(ch)
        except: missing.append(ch)
    return len(missing)==0, missing

def send_force_join(chat_id, channels):
    btns = [[{"text": f"👉 {ch.get('name','Join')}", "url": ch["link"]}] for ch in channels]
    btns.append([{"text": "✅ Join করেছি, চেক করুন", "callback_data": "check_join"}])
    send_msg(chat_id, "🔒 Bot ব্যবহার করতে নিচের Channel/Group এ Join করুন:",
             markup={"inline_keyboard": btns})

# ==========================
# PENDING STATE
# ==========================
PENDING_FILE = "pending.json"

def load_pending():
    if not os.path.exists(PENDING_FILE): return {}
    with open(PENDING_FILE) as f: return json.load(f)

def set_pending(chat_id, action, mid=None, extra=None):
    p = load_pending()
    p[str(chat_id)] = {"action": action, "panel_msg_id": mid, "extra": extra}
    with open(PENDING_FILE, "w") as f: json.dump(p, f)

def get_pending(chat_id):
    val = load_pending().get(str(chat_id))
    if not val: return None, None, None
    if isinstance(val, dict):
        return val.get("action"), val.get("panel_msg_id"), val.get("extra")
    return val, None, None

def clear_pending(chat_id):
    p = load_pending()
    p.pop(str(chat_id), None)
    with open(PENDING_FILE, "w") as f: json.dump(p, f)

# ==========================
# ADMIN PANEL
# ==========================
def is_admin(chat_id):
    return chat_id in load_config()["admin_ids"]

def admin_panel(chat_id, msg_id=None):
    cfg = load_config()
    fj  = "✅" if cfg["force_join"]["enabled"]                       else "❌"
    og  = "✅" if cfg["otp_group"]["enabled"]                        else "❌"
    gb  = "✅" if cfg.get("group_bot",{}).get("enabled")             else "❌"
    gm  = "✅" if cfg.get("group_bot",{}).get("send_all_mail", True) else "❌"
    total = len(_cache)
    ad    = cfg.get("auto_delete", {})
    ud    = ad.get("user_seconds", 0)
    gd    = ad.get("group_seconds", 0)
    ud_txt = f"{ud}s" if ud else "Off"
    gd_txt = f"{gd}s" if gd else "Off"
    ad_btn = cfg.get("ad_button", {"enabled": False, "text": "🚀 Open App", "url": ""})
    ad_status = "✅" if ad_btn.get("enabled") else "❌"
    ad_text = ad_btn.get("text", "🚀 Open App")
    ad_url = ad_btn.get("url", "")

    txt = (
        f"⚙️ <b>Admin Panel</b>\n\n"
        f"📧 Gmail: <code>{len(cfg['gmail_list'])}</code>\n"
        f"👥 Users: <code>{total}</code>\n"
        f"🔒 Force Join: {fj}\n"
        f"💬 OTP Group Button: {og}\n"
        f"🤖 Group Bot: {gb}\n"
        f"📧 Group All Mail: {gm}\n"
        f"⏱ User OTP Delete: <code>{ud_txt}</code>\n"
        f"⏱ Group OTP Delete: <code>{gd_txt}</code>\n"
        f"🚫 Blocked: <code>{len(cfg['blocked_users'])}</code>\n\n"
        f"📢 Ad Button: {ad_status}\n"
        f"✍️ Ad Text: <code>{html.escape(ad_text)}</code>\n"
        f"🔗 Ad Link: <code>{html.escape(ad_url)}</code>"
    )
    kb = {"inline_keyboard": [
        [{"text": "➕ Gmail যোগ",        "callback_data": "adm_add_gmail"},
         {"text": "🗑 Gmail মুছুন",      "callback_data": "adm_del_gmail"}],
        [{"text": f"🔒 Force Join {fj}", "callback_data": "adm_toggle_fj"},
         {"text": "➕ Channel যোগ",      "callback_data": "adm_add_ch"}],
        [{"text": "🗑 Channel মুছুন",    "callback_data": "adm_del_ch"},
         {"text": f"💬 OTP Button {og}", "callback_data": "adm_toggle_otp"}],
        [{"text": "🔗 OTP Link",         "callback_data": "adm_otp_link"}],
        [{"text": f"🤖 Group Bot {gb}",  "callback_data": "adm_group_bot"},
         {"text": f"📧 All Mail {gm}",   "callback_data": "adm_toggle_group_mail"}],
        [{"text": "📢 Broadcast",        "callback_data": "adm_broadcast"},
         {"text": "📊 Statistics",       "callback_data": "adm_stats"}],
        [{"text": "⏱ User OTP Delete",  "callback_data": "adm_del_user"},
         {"text": "⏱ Group OTP Delete", "callback_data": "adm_del_group"}],
        [{"text": "🚫 Block",            "callback_data": "adm_block"},
         {"text": "✅ Unblock",          "callback_data": "adm_unblock"}],
        [{"text": "👥 User List",        "callback_data": "adm_users"},
         {"text": "🔑 Sheet Title",      "callback_data": "adm_sheet_title"}],
        [{"text": f"📢 Ad Button {ad_status}", "callback_data": "adm_toggle_ad"},
         {"text": "✍️ Ad Text",         "callback_data": "adm_ad_text"}],
        [{"text": "🔗 Ad Link",         "callback_data": "adm_ad_link"}]
    ]}
    if msg_id:
        edit_msg(chat_id, msg_id, txt, markup=kb)
    else:
        send_msg(chat_id, txt, markup=kb)

# ==========================
# PENDING HANDLER
# ==========================
def process_pending(chat_id, text):
    action, pmid, extra = get_pending(chat_id)
    if not action: return False
    cfg = load_config()
    clear_pending(chat_id)

    if action == "add_gmail":
        ei = text.strip()
        if "@" not in ei:
            send_msg(chat_id, "❌ সঠিক Gmail দিন।")
        elif ei in cfg["gmail_list"]:
            send_msg(chat_id, f"⚠️ <code>{ei}</code> আগে থেকেই আছে।")
        else:
            set_pending(chat_id, f"add_gmail_pass:{ei}", pmid)
            send_msg(chat_id, f"📧 Gmail: <code>{ei}</code>\n\n🔑 App Password পাঠান:")
            return True
        admin_panel(chat_id)

    elif action.startswith("add_gmail_pass:"):
        new_email = action.split("add_gmail_pass:", 1)[1]
        app_pass  = text.strip().replace(" ", "")
        try:
            t = imaplib.IMAP4_SSL("imap.gmail.com")
            t.login(new_email, app_pass)
            t.logout()
            cfg["gmail_list"].append(new_email)
            cfg.setdefault("imap_passwords", {})[new_email] = app_pass
            save_config(cfg)
            threading.Thread(target=imap_thread, args=(new_email, app_pass), daemon=True).start()
            send_msg(chat_id, f"✅ <code>{new_email}</code> যোগ হয়েছে। IMAP চালু।")
        except Exception as e:
            send_msg(chat_id, f"❌ Login ব্যর্থ!\n<code>{e}</code>")
        admin_panel(chat_id)

    elif action == "del_gmail":
        em = text.strip()
        if em in cfg["gmail_list"]:
            cfg["gmail_list"].remove(em)
            cfg.get("imap_passwords", {}).pop(em, None)
            save_config(cfg)
            send_msg(chat_id, f"✅ <code>{em}</code> মুছে ফেলা হয়েছে।")
        else:
            send_msg(chat_id, "❌ নেই।")
        admin_panel(chat_id)

    elif action == "add_channel":
        if "-" in text and "https://" in text:
            idx = text.index("-")
            cfg["force_join"]["channels"].append({
                "name": text[:idx].strip(), "link": text[idx+1:].strip()
            })
            save_config(cfg)
            send_msg(chat_id, "✅ Channel যোগ হয়েছে।")
        else:
            send_msg(chat_id, "❌ Format: <code>নাম-https://t.me/link</code>")
        admin_panel(chat_id)

    elif action == "del_channel":
        cfg["force_join"]["channels"] = [
            c for c in cfg["force_join"]["channels"] if c["name"] != text.strip()
        ]
        save_config(cfg)
        send_msg(chat_id, "✅ মুছে ফেলা হয়েছে।")
        admin_panel(chat_id)

    elif action == "otp_link":
        cfg["otp_group"]["link"] = text.strip()
        save_config(cfg)
        send_msg(chat_id, "✅ Link পরিবর্তন হয়েছে।")
        admin_panel(chat_id)

    elif action == "broadcast_msg":
        # Confirm step
        set_pending(chat_id, "broadcast_confirm", pmid, extra=text)
        send_msg(
            chat_id,
            f"আপনি কি এই message broadcast করতে চান?\n\n<blockquote>{text}</blockquote>",
            markup={"inline_keyboard": [[
                {"text": "✅ Send",   "callback_data": "bc_confirm"},
                {"text": "❌ Cancel", "callback_data": "bc_cancel"}
            ]]}
        )

    elif action == "block":
        try:
            uid = int(text.strip())
            if uid not in cfg["blocked_users"]:
                cfg["blocked_users"].append(uid); save_config(cfg)
                send_msg(chat_id, f"🚫 <code>{uid}</code> blocked।")
            else: send_msg(chat_id, "⚠️ Already blocked।")
        except: send_msg(chat_id, "❌ Chat ID দিন।")
        admin_panel(chat_id)

    elif action == "unblock":
        try:
            uid = int(text.strip())
            if uid in cfg["blocked_users"]:
                cfg["blocked_users"].remove(uid); save_config(cfg)
                send_msg(chat_id, f"✅ <code>{uid}</code> unblocked।")
            else: send_msg(chat_id, "⚠️ Blocked না।")
        except: send_msg(chat_id, "❌ Chat ID দিন।")
        admin_panel(chat_id)

    elif action == "sheet_title":
        cfg["sheet_title"] = text.strip(); save_config(cfg)
        send_msg(chat_id, f"✅ Sheet: <code>{text.strip()}</code>")
        admin_panel(chat_id)

    elif action == "set_ad_text":
        cfg.setdefault("ad_button", {})["text"] = text.strip()
        save_config(cfg)
        update_telegram_menu_button()
        send_msg(chat_id, f"✅ Ad Button Text পরিবর্তন হয়েছে: <code>{html.escape(text.strip())}</code>")
        admin_panel(chat_id)

    elif action == "set_ad_link":
        cfg.setdefault("ad_button", {})["url"] = text.strip()
        save_config(cfg)
        update_telegram_menu_button()
        send_msg(chat_id, f"✅ Ad Button Link পরিবর্তন হয়েছে: <code>{html.escape(text.strip())}</code>")
        admin_panel(chat_id)

    elif action == "group_bot_token":
        token = text.strip()
        try:
            r = _session.get(
                f"https://api.telegram.org/bot{token}/getMe", timeout=15
            ).json()
            if not r.get("ok"): raise Exception("Invalid token")
            bot_name = r["result"].get("username", "")
            cfg.setdefault("group_bot", {})["token"] = token
            save_config(cfg)
            set_pending(chat_id, "group_bot_groupid", pmid)
            send_msg(chat_id, f"✅ @{bot_name}\n\n📢 Group ID পাঠান:\n<code>-1001234567890</code>")
            return True
        except Exception as e:
            send_msg(chat_id, f"❌ Token invalid!\n<code>{e}</code>")
            admin_panel(chat_id)

    elif action == "group_bot_groupid":
        cfg.setdefault("group_bot", {})["group_id"]      = text.strip()
        cfg["group_bot"]["enabled"]       = True
        cfg["group_bot"]["send_all_mail"] = True
        save_config(cfg)
        send_msg(chat_id, f"✅ Group Bot চালু!\nID: <code>{text.strip()}</code>\n\nBot কে group এর admin করুন।")
        admin_panel(chat_id)

    elif action == "set_del_user":
        secs = parse_time_input(text)
        cfg.setdefault("auto_delete", {})["user_seconds"] = secs
        save_config(cfg)
        msg = f"✅ User OTP <code>{secs}s</code> পরে delete হবে।" if secs else "✅ User OTP auto delete বন্ধ।"
        send_msg(chat_id, msg)
        admin_panel(chat_id)

    elif action == "set_del_group":
        secs = parse_time_input(text)
        cfg.setdefault("auto_delete", {})["group_seconds"] = secs
        save_config(cfg)
        msg = f"✅ Group OTP <code>{secs}s</code> পরে delete হবে।" if secs else "✅ Group OTP auto delete বন্ধ।"
        send_msg(chat_id, msg)
        admin_panel(chat_id)

    return True

def do_broadcast(admin_id, message_text):
    """সব user কে broadcast করে result দেখায়"""
    users = get_all_users()
    ok = fail = 0
    for u in users:
        try:
            cid = int(u["chat_id"])
            send_msg(cid, f"📢 <b>Admin Notice:</b>\n\n{message_text}")
            ok += 1
            time.sleep(0.05)
        except: fail += 1
    send_msg(admin_id, f"📢 Broadcast শেষ!\n\n✅ {ok}\n❌ {fail}")

# ==========================
# BOT LOOP
# ==========================
def run_bot():
    global last_update_id
    print(f"{CYAN}{BOLD}🤖 Polling started...{RESET}")
    while True:
        try:
            res = api("getUpdates", params={"offset": last_update_id+1, "timeout": 30})
            updates = res.get("result", [])
            if updates:
                print(f"{BLUE}📥 {len(updates)} updates{RESET}")
            for update in updates:
                uid = update["update_id"]
                if uid in _processed_updates: continue
                _processed_updates.add(uid)
                if len(_processed_updates) > 1000:
                    for x in sorted(_processed_updates)[:500]:
                        _processed_updates.discard(x)
                last_update_id = uid
                cfg = load_config()

                # ── MESSAGE ──
                if "message" in update and "text" in update["message"]:
                    msg     = update["message"]
                    chat_id = msg["chat"]["id"]
                    text    = msg["text"].strip()
                    user    = msg["from"]
                    uname   = user.get("username", "")
                    fname   = f"{user.get('first_name','')} {user.get('last_name','')}".strip()

                    if chat_id in cfg["blocked_users"]:
                        send_msg(chat_id, "🚫 আপনি এই bot ব্যবহার করতে পারবেন না।")
                        continue

                    if is_admin(chat_id):
                        if text == "/admin": admin_panel(chat_id); continue
                        if process_pending(chat_id, text): continue

                    if text == "/start":
                        lock = get_user_lock(chat_id)
                        if not lock.acquire(blocking=False): continue
                        try:
                            register_user(chat_id, uname, fname)
                            joined, missing = check_joined(chat_id)
                            if not joined:
                                send_force_join(chat_id, missing)
                                continue
                            send_alias_new(chat_id)
                        finally:
                            lock.release()
                        continue

                    if text == "/gen":
                        joined, missing = check_joined(chat_id)
                        if not joined: send_force_join(chat_id, missing); continue
                        send_alias(chat_id)
                        continue

                # ── CALLBACK ──
                if "callback_query" in update:
                    cb      = update["callback_query"]
                    chat_id = cb["message"]["chat"]["id"]
                    msg_id  = cb["message"]["message_id"]
                    data    = cb["data"]

                    if chat_id in cfg["blocked_users"]:
                        answer_cb(cb["id"], "🚫 Blocked", alert=True); continue

                    # Broadcast confirm/cancel
                    if data == "bc_confirm":
                        action, _, extra = get_pending(chat_id)
                        if action == "broadcast_confirm" and extra:
                            clear_pending(chat_id)
                            answer_cb(cb["id"], "📢 Sending...")
                            delete_msg(chat_id, msg_id)
                            threading.Thread(
                                target=do_broadcast, args=(chat_id, extra), daemon=True
                            ).start()
                        continue

                    if data == "bc_cancel":
                        clear_pending(chat_id)
                        answer_cb(cb["id"], "❌ Cancelled")
                        delete_msg(chat_id, msg_id)
                        continue

                    if data == "refresh_alias":
                        joined, missing = check_joined(chat_id)
                        if not joined:
                            answer_cb(cb["id"], "❌ Channel ছেড়ে দিয়েছেন!", alert=True)
                            send_force_join(chat_id, missing)
                        else:
                            d   = get_user_data(chat_id)
                            tag = d.get("tag","") if d else ""
                            answer_cb(cb["id"], f"⏳ {tag} — OTP আসার অপেক্ষায়...")

                    elif data == "next_alias":
                        joined, missing = check_joined(chat_id)
                        if not joined:
                            answer_cb(cb["id"], "❌ Channel ছেড়ে দিয়েছেন!", alert=True)
                            send_force_join(chat_id, missing)
                        else:
                            change_alias(chat_id, msg_id)
                            answer_cb(cb["id"])

                    elif data == "check_join":
                        joined, missing = check_joined(chat_id)
                        if joined:
                            answer_cb(cb["id"], "✅ Verified!")
                            delete_msg(chat_id, msg_id)
                            send_alias(chat_id)
                        else:
                            answer_cb(cb["id"], "❌ এখনো Join করেননি!", alert=True)

                    elif is_admin(chat_id):
                        answer_cb(cb["id"])

                        if data == "adm_add_gmail":
                            set_pending(chat_id, "add_gmail", msg_id)
                            delete_msg(chat_id, msg_id)
                            send_msg(chat_id, "📧 Gmail পাঠান:\n<code>example@gmail.com</code>")

                        elif data == "adm_del_gmail":
                            lst = "\n".join([f"• <code>{g}</code>" for g in cfg["gmail_list"]]) or "❌ নেই।"
                            set_pending(chat_id, "del_gmail", msg_id)
                            send_msg(chat_id, f"<b>Gmail List:</b>\n{lst}\n\nমুছতে Gmail পাঠান:")

                        elif data == "adm_toggle_fj":
                            cfg["force_join"]["enabled"] = not cfg["force_join"]["enabled"]
                            save_config(cfg); admin_panel(chat_id, msg_id)

                        elif data == "adm_add_ch":
                            set_pending(chat_id, "add_channel", msg_id)
                            delete_msg(chat_id, msg_id)
                            send_msg(chat_id, "➕ Format:\n<code>নাম-https://t.me/link</code>")

                        elif data == "adm_del_ch":
                            lst = "\n".join([f"• <code>{c['name']}</code>" for c in cfg["force_join"]["channels"]]) or "❌ নেই।"
                            set_pending(chat_id, "del_channel", msg_id)
                            send_msg(chat_id, f"<b>Channels:</b>\n{lst}\n\nমুছতে নাম পাঠান:")

                        elif data == "adm_toggle_otp":
                            cfg["otp_group"]["enabled"] = not cfg["otp_group"]["enabled"]
                            save_config(cfg); admin_panel(chat_id, msg_id)

                        elif data == "adm_otp_link":
                            set_pending(chat_id, "otp_link", msg_id)
                            send_msg(chat_id, f"🔗 বর্তমান: <code>{cfg['otp_group']['link']}</code>\nনতুন link পাঠান:")

                        elif data == "adm_group_bot":
                            gb = cfg.get("group_bot", {})
                            if gb.get("enabled"):
                                cfg["group_bot"]["enabled"] = False
                                save_config(cfg)
                                send_msg(chat_id, "❌ Group Bot বন্ধ।")
                                admin_panel(chat_id, msg_id)
                            else:
                                if gb.get("token") and gb.get("group_id"):
                                    cfg["group_bot"]["enabled"] = True
                                    save_config(cfg)
                                    send_msg(chat_id, "✅ Group Bot চালু।")
                                    admin_panel(chat_id, msg_id)
                                else:
                                    set_pending(chat_id, "group_bot_token", msg_id)
                                    delete_msg(chat_id, msg_id)
                                    send_msg(chat_id, "🤖 Group Bot Token পাঠান:")

                        elif data == "adm_toggle_group_mail":
                            current = cfg.get("group_bot", {}).get("send_all_mail", True)
                            cfg.setdefault("group_bot", {})["send_all_mail"] = not current
                            save_config(cfg)
                            status = "✅ চালু" if not current else "❌ বন্ধ"
                            send_msg(chat_id, f"📧 All Mail {status}।")
                            admin_panel(chat_id, msg_id)

                        elif data == "adm_broadcast":
                            set_pending(chat_id, "broadcast_msg", msg_id)
                            delete_msg(chat_id, msg_id)
                            send_msg(chat_id, "📢 Message পাঠান:")

                        elif data == "adm_stats":
                            send_msg(chat_id,
                                f"📊 <b>Statistics</b>\n\n"
                                f"👥 Users: <code>{len(_cache)}</code>\n"
                                f"📧 Gmails: <code>{len(cfg['gmail_list'])}</code>\n"
                                f"🚫 Blocked: <code>{len(cfg['blocked_users'])}</code>")

                        elif data == "adm_del_user":
                            ud = cfg.get("auto_delete", {}).get("user_seconds", 0)
                            ud_txt = f"{ud}s" if ud else "Off"
                            set_pending(chat_id, "set_del_user", msg_id)
                            send_msg(chat_id,
                                f"⏱ <b>User OTP Auto Delete</b>\n"
                                f"বর্তমান: <code>{ud_txt}</code>\n\n"
                                f"Format: <code>M1</code> = 1 মিনিট, <code>S35</code> = 35 সেকেন্ড\n"
                                f"বন্ধ করতে: <code>S0</code>")

                        elif data == "adm_del_group":
                            gd = cfg.get("auto_delete", {}).get("group_seconds", 0)
                            gd_txt = f"{gd}s" if gd else "Off"
                            set_pending(chat_id, "set_del_group", msg_id)
                            send_msg(chat_id,
                                f"⏱ <b>Group OTP Auto Delete</b>\n"
                                f"বর্তমান: <code>{gd_txt}</code>\n\n"
                                f"Format: <code>M1</code> = 1 মিনিট, <code>S35</code> = 35 সেকেন্ড\n"
                                f"বন্ধ করতে: <code>S0</code>")

                        elif data == "adm_block":
                            set_pending(chat_id, "block", msg_id)
                            delete_msg(chat_id, msg_id)
                            send_msg(chat_id, "🚫 Block করতে Chat ID পাঠান:")

                        elif data == "adm_unblock":
                            if not cfg["blocked_users"]:
                                send_msg(chat_id, "✅ কোনো blocked user নেই।")
                            else:
                                lst = "\n".join([f"• <code>{u}</code>" for u in cfg["blocked_users"]])
                                set_pending(chat_id, "unblock", msg_id)
                                send_msg(chat_id, f"<b>Blocked:</b>\n{lst}\n\nUnblock Chat ID:")

                        elif data == "adm_users":
                            users = get_all_users()
                            if not users:
                                send_msg(chat_id, "❌ কোনো user নেই।")
                            else:
                                lines = [
                                    f"<code>{u['chat_id']}</code> @{u.get('username','N/A')} {u.get('full_name','')}"
                                    for u in users[:50]
                                ]
                                send_msg(chat_id, "👥 <b>Users:</b>\n\n" + "\n".join(lines))

                        elif data == "adm_sheet_title":
                            set_pending(chat_id, "sheet_title", msg_id)
                            send_msg(chat_id, f"📋 বর্তমান: <code>{cfg['sheet_title']}</code>\nনতুন title পাঠান:")

                        elif data == "adm_toggle_ad":
                            cfg.setdefault("ad_button", {})["enabled"] = not cfg.get("ad_button", {}).get("enabled", False)
                            save_config(cfg)
                            update_telegram_menu_button()
                            admin_panel(chat_id, msg_id)

                        elif data == "adm_ad_text":
                            current_text = cfg.get("ad_button", {}).get("text", "🚀 Open App")
                            set_pending(chat_id, "set_ad_text", msg_id)
                            send_msg(chat_id, f"✍️ বর্তমান বাটন টেক্সট: <code>{html.escape(current_text)}</code>\nনতুন টেক্সট পাঠান:")

                        elif data == "adm_ad_link":
                            current_url = cfg.get("ad_button", {}).get("url", "")
                            set_pending(chat_id, "set_ad_link", msg_id)
                            send_msg(chat_id, f"🔗 বর্তমান বাটন লিংক: <code>{html.escape(current_url)}</code>\nনতুন লিংক পাঠান:")

        except Exception as e:
            print(f"{RED}[Bot] {e}{RESET}")
            time.sleep(3)

# ==========================
# START
# ==========================
if __name__ == "__main__":
    print(f"{MAGENTA}{BOLD}{'='*45}{RESET}")
    print(f"{MAGENTA}{BOLD}   📬  Gmail OTP Bot  —  Starting Up   {RESET}")
    print(f"{MAGENTA}{BOLD}{'='*45}{RESET}")

    cfg = load_config()
    print(f"{CYAN}⚙️  Config loaded{RESET}")

    # Local data load
    load_cache()

    # IMAP threads
    print(f"{CYAN}{'─'*45}{RESET}")
    for gmail in cfg["gmail_list"]:
        pw = cfg.get("imap_passwords", {}).get(gmail, "")
        if pw and "YOUR_APP_PASSWORD" not in pw:
            threading.Thread(target=imap_thread, args=(gmail, pw), daemon=True).start()
            print(f"{GREEN}✅ IMAP:{RESET} {WHITE}{gmail}{RESET}")
        else:
            print(f"{YELLOW}⚠️  Password নেই:{RESET} {DIM}{gmail}{RESET}")

    print(f"{CYAN}{'─'*45}{RESET}")
    print(f"{GREEN}{BOLD}🤖 Bot চালু...{RESET}")
    try:
        update_telegram_menu_button()
    except Exception as e:
        print(f"{RED}[Menu Button Init Error] {e}{RESET}")
    run_bot()
