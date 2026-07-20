#!/usr/bin/env python3
"""
Feishu API helper functions.
Wraps Feishu Open API for messaging, reactions, pins, etc.
"""

import json
import requests

from config import feishu_app_id, feishu_app_secret, feishu_dest, get_receive_id_type


def get_tenant_access_token():
    """Get Feishu tenant access token."""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {"app_id": feishu_app_id, "app_secret": feishu_app_secret}
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    data = r.json()
    if data.get('code') == 0:
        return data['tenant_access_token']
    raise Exception(f"Failed to get token: {data}")


def send_card(chat_id, content_parts, priority="urgent"):
    """Send an interactive card message. Returns (message_id, chat_id)."""
    receive_id_type = get_receive_id_type(chat_id)
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
    token = get_tenant_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

    content = {"elements": content_parts}
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(content),
        "priority": priority,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    data = r.json()
    if data.get('code') == 0:
        return data['data']['message_id'], data['data'].get('chat_id'), token
    raise Exception(f"Failed to send card: {data}")


def send_markdown(chat_id, text):
    """Send a simple markdown message. Returns (message_id, token)."""
    receive_id_type = get_receive_id_type(chat_id)
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
    token = get_tenant_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

    content = {"elements": [{"tag": "markdown", "content": text}]}
    payload = {"receive_id": chat_id, "msg_type": "interactive", "content": json.dumps(content)}
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    data = r.json()
    if data.get('code') == 0:
        return data['data']['message_id'], token
    raise Exception(f"Failed to send message: {data}")


def add_reaction(token, message_id, emoji_type):
    """Add a reaction emoji to a message."""
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reactions"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"reaction_type": {"emoji_type": emoji_type}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Error adding reaction: {e}")
        return None


def list_reactions(token, message_id):
    """List all reactions on a message."""
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reactions"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('code') == 0:
                return data.get('data', {}).get('items', [])
    except Exception as e:
        print(f"Error listing reactions: {e}")
    return []


def pin_message(token, message_id):
    """Pin a message."""
    url = "https://open.feishu.cn/open-apis/im/v1/pins"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    payload = {"message_id": message_id}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        data = r.json()
        if data.get('code') == 0:
            print(f"Message pinned: {message_id}")
            return True
        else:
            print(f"Failed to pin message: {data}")
            return False
    except Exception as e:
        print(f"Error pinning message: {e}")
        return False


def unpin_message(token, message_id):
    """Unpin a message."""
    url = f"https://open.feishu.cn/open-apis/im/v1/pins/{message_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    try:
        r = requests.delete(url, headers=headers, timeout=10)
        data = r.json()
        if data.get('code') == 0:
            print(f"Message unpinned: {message_id}")
            return True
        else:
            print(f"Failed to unpin message: {data}")
            return False
    except Exception as e:
        print(f"Error unpinning message: {e}")
        return False


def urgent_message(token, message_id, user_ids):
    """Send urgent notification for a message."""
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/urgent_app?user_id_type=open_id"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    payload = {"user_id_list": user_ids}
    try:
        r = requests.patch(url, headers=headers, json=payload, timeout=10)
        data = r.json()
        if data.get('code') == 0:
            print("Message sent with urgent notification")
            return True
        else:
            print(f"Failed to urgent message: {data}")
            return False
    except Exception as e:
        print(f"Error sending urgent notification: {e}")
        return False


# ── Unified backend interface ─────────────────────────────────────────────
# These functions provide a common interface that hook scripts use.
# Other backends (e.g. telegram_api) must implement the same signatures.

def send_rejection(repo_name, git_diff, llm_reason):
    """Send LLM rejection notification. Returns (msg_id, token)."""
    content_parts = [
        {"tag": "markdown", "content": f"**❌ LLM 审核拒绝**: {llm_reason}"},
        {"tag": "markdown", "content": f"**🔔 Push 审批请求 | {repo_name}**\n\n```\n{git_diff}\n```"},
    ]
    return send_card(feishu_dest, content_parts)


def send_approval_request(repo_name, git_diff):
    """Send approval request card. Returns (msg_id, chat_id, token)."""
    content_parts = [
        {"tag": "markdown", "content": f"**🔔 Push 审批请求 | {repo_name}**\n\n```\n{git_diff}\n```"},
    ]
    return send_card(feishu_dest, content_parts)


def urgent(token, message_id):
    """Send urgent notification for a message."""
    return urgent_message(token, message_id, [feishu_dest])


def send_notification(text):
    """Send a simple notification message. Returns (msg_id, token)."""
    return send_markdown(feishu_dest, text)
