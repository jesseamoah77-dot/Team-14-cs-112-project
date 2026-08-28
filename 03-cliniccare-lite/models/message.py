"""
Non-urgent messaging between a patient and their clinician, plus system notifications.

Privacy property that the routes and tests both lean on: a conversation is only ever
readable by its two participants. conversation() takes the *requesting* user and the
other party and returns only messages strictly between those two ids - there is no
"all messages" accessor for patients at all.

kind: "message" (human wrote it) or "notification" (system event for the inbox -
submission confirmations, review outcomes, appointment reminders).
"""

from datetime import datetime

from models import store
from utils.validators import ValidationError, require


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def send(sender_id, recipient_id, content, kind="message"):
    content = require(content, "Message")
    if sender_id == recipient_id:
        raise ValidationError("You cannot message yourself.")

    def _apply(data):
        message_id = store.next_id("messages", "M")
        data[message_id] = {
            "sender_id": sender_id, "recipient_id": recipient_id,
            "content": content, "timestamp": _now(), "read": False, "kind": kind,
        }
        return message_id
    return store.update("messages", _apply)


def notify(recipient_id, content):
    """System notification into the in-app inbox (sender 'SYSTEM')."""
    def _apply(data):
        message_id = store.next_id("messages", "M")
        data[message_id] = {
            "sender_id": "SYSTEM", "recipient_id": recipient_id,
            "content": content, "timestamp": _now(), "read": False, "kind": "notification",
        }
        return message_id
    return store.update("messages", _apply)


def conversation(user_id, other_id):
    """Messages strictly between these two users, oldest first."""
    out = []
    for message_id, m in store.load("messages").items():
        pair = {m["sender_id"], m["recipient_id"]}
        if pair == {user_id, other_id}:
            out.append({"id": message_id, **m})
    return sorted(out, key=lambda m: m["timestamp"])


def inbox(user_id):
    """Everything addressed to this user (messages and notifications), newest first."""
    out = [{"id": mid, **m} for mid, m in store.load("messages").items()
           if m["recipient_id"] == user_id]
    return sorted(out, key=lambda m: m["timestamp"], reverse=True)


def unread_count(user_id):
    return sum(1 for m in store.load("messages").values()
               if m["recipient_id"] == user_id and not m["read"])


def mark_read(user_id, message_id):
    """Only the recipient can mark their mail read - silently ignore anything else."""
    def _apply(data):
        m = data.get(message_id)
        if m and m["recipient_id"] == user_id:
            m["read"] = True
    store.update("messages", _apply)
