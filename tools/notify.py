#!/usr/bin/env python3
"""Send a short message to the owner's Telegram bot. Does nothing (returns False) when not configured.

Config: config/secrets/telegram.json {"token": "...", "chat_id": "..."} (chmod 600, never printed),
or the environment variables TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID.

Usage:
  notify.py "text"          send a message
  notify.py --setup         after you sent any message to the bot: find your chat id and save it
  notify.py --test          send a test message

From Python:  from tools import notify; notify.send("text"); notify.link("001-bach-dang", "images")
"""
import json
import os
import sys
import urllib.parse
import urllib.request

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = os.path.join(WS, "config", "secrets", "telegram.json")
STUDIO = os.path.join(WS, "config", "studio.json")


def _conf():
    c = {}
    try:
        with open(CONF, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError):
        pass
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or c.get("token", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID") or str(c.get("chat_id", ""))
    return token.strip(), chat.strip(), c


def _call(token, method, params):
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen("https://api.telegram.org/bot%s/%s" % (token, method), data=data, timeout=15) as r:
        return json.load(r)


def studio_url():
    try:
        with open(STUDIO, encoding="utf-8") as f:
            port = json.load(f).get("port", 8765)
    except (OSError, ValueError):
        port = 8765
    return "http://127.0.0.1:%d" % port


def link(project_id=None, screen=""):
    """Studio link for a project screen (or the home page when project_id is None)."""
    if not project_id:
        return studio_url() + "/#/"
    return "%s/#/p/%s%s" % (studio_url(), project_id, "/" + screen if screen else "")


def send(text):
    """Best effort: never raises, so a Telegram problem cannot break a production job."""
    token, chat, _ = _conf()
    if not token or not chat:
        return False
    try:
        return bool(_call(token, "sendMessage", {"chat_id": chat, "text": text[:4000],
                                                 "disable_web_page_preview": "true"}).get("ok"))
    except Exception as e:  # noqa: BLE001
        print("telegram: %s" % type(e).__name__, file=sys.stderr)
        return False


def setup():
    token, _, c = _conf()
    if not token:
        print("No token. Put it in %s as {\"token\": \"...\"} first." % CONF)
        return 1
    res = _call(token, "getUpdates", {})
    chats = {}
    for u in res.get("result", []):
        m = u.get("message") or u.get("channel_post") or {}
        ch = m.get("chat") or {}
        if ch.get("id"):
            chats[ch["id"]] = ch.get("username") or ch.get("title") or ch.get("first_name") or ""
    if not chats:
        print("No messages yet: open the bot in Telegram, send it any message (e.g. /start), then run --setup again.")
        return 1
    chat_id, name = list(chats.items())[-1]
    c.update(token=token, chat_id=chat_id)
    os.makedirs(os.path.dirname(CONF), exist_ok=True)
    with open(CONF, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=1)
    os.chmod(CONF, 0o600)
    print("Saved chat id for %s." % (name or chat_id))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--setup"]:
        sys.exit(setup())
    if a[:1] == ["--test"]:
        sys.exit(0 if send("Studio: Telegram notifications are working.") else 1)
    if a:
        sys.exit(0 if send(" ".join(a)) else 1)
    print(__doc__)
