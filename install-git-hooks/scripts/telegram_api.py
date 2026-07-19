#!/usr/bin/env python3
"""
Telegram Bot API helper functions using aiogram 3.x.
Implements the same unified backend interface as feishu_api.py.
Uses inline keyboard buttons for approval/rejection and aiogram's update listener
to capture callback queries in real time.
"""

import asyncio
import json
import threading
import time
import requests

from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.filters import Command
from config import (
    telegram_bot_token,
    telegram_chat_id,
    telegram_allow_from,
)


# ── Approval polling state ────────────────────────────────────────────────

_pending_approvals = {}  # message_id → Future(asyncio.Future)
_bot = None
_dp = None
_loop = None
_runner_thread = None


def _ensure_bot():
    """Create aiogram Bot and Dispatcher if not already created."""
    global _bot, _dp
    if _bot is None:
        _bot = Bot(token=telegram_bot_token)
        _dp = Dispatcher()
        _register_handlers()
    return _bot, _dp


def _allowed_user(user_id: int) -> bool:
    """Check if user is allowed to interact with the bot."""
    if not telegram_allow_from:
        return True
    return user_id in telegram_allow_from


def _register_handlers():
    """Register aiogram handlers."""
    bot, dp = _ensure_bot()

    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        if _allowed_user(message.from_user.id):
            await message.answer("🤖 install-git-hooks bot is running.")

    @dp.callback_query()
    async def handle_callback(callback: CallbackQuery):
        msg = callback.message
        if msg is None:
            return
        mid = msg.message_id
        if mid in _pending_approvals:
            future = _pending_approvals[mid]
            if not future.done():
                future.set_result({
                    "callback_id": callback.id,
                    "data": callback.data,
                    "from_user_id": callback.from_user.id,
                })


def _run_bot_loop():
    """Run aiogram polling in a dedicated thread."""
    global _loop, _bot
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    bot, dp = _ensure_bot()
    # Skip updates from before the bot started
    asyncio.run_coroutine_threadsafe(bot.delete_webhook(drop_pending_updates=True), _loop)
    polling = dp.start_polling(bot)
    _loop.run_until_complete(polling)


def _ensure_polling_thread():
    """Start the aiogram polling thread if not already running."""
    global _runner_thread
    if _runner_thread is None or not _runner_thread.is_alive():
        _runner_thread = threading.Thread(target=_run_bot_loop, daemon=True)
        _runner_thread.start()
        # Give the thread a moment to initialize
        time.sleep(1)


# ── Direct API calls (for non-async context) ──────────────────────────────

def _api(method, payload=None, timeout=10):
    """Call Telegram Bot API via requests (synchronous)."""
    url = f"https://api.telegram.org/bot{telegram_bot_token}/{method}"
    r = requests.post(url, json=payload or {}, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if not data.get('ok'):
        raise Exception(f"Telegram API error: {data}")
    return data


def _run_coro(coro):
    """Run an async coroutine from synchronous context."""
    global _loop
    _ensure_polling_thread()
    if _loop is None:
        # Fallback: create a temp event loop
        _loop = asyncio.new_event_loop()
    try:
        return asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout=10)
    except Exception as e:
        raise Exception(f"Failed to run async operation: {e}")


# ── Public API ────────────────────────────────────────────────────────────

def send_message(chat_id, text, parse_mode='Markdown', reply_markup=None):
    """Send a message. Returns (message_id)."""
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    data = _api('sendMessage', payload)
    return data['result']['message_id']


def edit_message_text(chat_id, message_id, text, parse_mode='Markdown', reply_markup=None):
    """Edit an existing message text."""
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode,
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    _api('editMessageText', payload)


def answer_callback_query_sync(callback_query_id, text=None, show_alert=False):
    """Answer a callback query (button click) via synchronous API."""
    payload = {
        'callback_query_id': callback_query_id,
        'show_alert': show_alert,
    }
    if text:
        payload['text'] = text
    _api('answerCallbackQuery', payload)


def pin_chat_message(chat_id, message_id):
    """Pin a message in the chat."""
    _api('pinChatMessage', {'chat_id': chat_id, 'message_id': message_id})


# ── Callback waiting via asyncio Future ────────────────────────────────────

def wait_for_callback(message_id, chat_id, timeout=120):
    """
    Wait for a callback query matching the given message_id.
    Uses an asyncio Future that gets resolved by the callback handler.
    Returns (callback_id, callback_data, from_user_id) or (None, None, None) on timeout.
    """
    _ensure_polling_thread()

    loop = _loop
    if loop is None:
        return None, None, None

    future = asyncio.run_coroutine_threadsafe(
        _create_future_for_message(message_id),
        loop
    ).result(timeout=5)

    try:
        result = asyncio.run_coroutine_threadsafe(
            _wait_for_future(future, timeout),
            loop
        ).result(timeout=timeout + 5)
        return result["callback_id"], result["data"], result["from_user_id"]
    except asyncio.TimeoutError:
        # Clean up the future
        asyncio.run_coroutine_threadsafe(
            _remove_future(message_id),
            loop
        )
        return None, None, None


async def _create_future_for_message(message_id):
    """Create a Future for a pending approval message."""
    future = asyncio.get_event_loop().create_future()
    _pending_approvals[message_id] = future
    return future


async def _wait_for_future(future, timeout):
    """Wait for a Future to resolve with a timeout."""
    return await asyncio.wait_for(future, timeout=timeout)


async def _remove_future(message_id):
    """Remove a Future from pending approvals."""
    _pending_approvals.pop(message_id, None)


# ── Unified backend interface ──────────────────────────────────────────────

def send_rejection(repo_name, git_diff, llm_reason):
    """Send LLM rejection notification. Returns (msg_id, chat_id, token)."""
    text = (
        f"❌ **LLM 审核拒绝**: {llm_reason}\n\n"
        f"🔔 **Push 审批请求 | {repo_name}**\n\n"
        f"```\n{git_diff}\n```"
    )
    msg_id = send_message(telegram_chat_id, text)
    return msg_id, telegram_chat_id, telegram_bot_token


def send_approval_request(repo_name, git_diff):
    """
    Send approval request with inline keyboard buttons.
    Returns (msg_id, chat_id, token).
    """
    text = (
        f"✅ **LLM 审核通过**\n\n"
        f"🔔 **Push 审批请求 | {repo_name}**\n\n"
        f"```\n{git_diff}\n```"
    )

    reply_markup = {
        'inline_keyboard': [
            [
                {'text': '✅ Approve', 'callback_data': 'approve'},
                {'text': '❌ Reject', 'callback_data': 'reject'},
            ]
        ]
    }

    msg_id = send_message(telegram_chat_id, text, reply_markup=reply_markup)
    return msg_id, telegram_chat_id, telegram_bot_token


def urgent(token, message_id):
    """Send urgent notification — for Telegram, pin the message."""
    try:
        pin_chat_message(telegram_chat_id, message_id)
        print("Message pinned (urgent notification)")
        return True
    except Exception as e:
        print(f"Failed to pin message: {e}")
        return False


def send_notification(text):
    """Send a notification message. Returns (msg_id, token)."""
    msg_id = send_message(telegram_chat_id, text)
    return msg_id, telegram_bot_token


def add_reaction(token, message_id, emoji_type):
    """
    Telegram doesn't have emoji reactions via bot API in the same way as Feishu.
    Try to add emoji reaction (Telegram 6.8+).
    """
    emoji = _emoji_map(emoji_type)
    try:
        _api('setMessageReaction', {
            'chat_id': telegram_chat_id,
            'message_id': message_id,
            'reaction': json.dumps([{'type': 'emoji', 'emoji': emoji}]),
        })
        return {'ok': True}
    except Exception:
        print(f"[Telegram] Cannot add reaction '{emoji_type}' to message {message_id}")
        return {'ok': False}


def list_reactions(token, message_id):
    """
    Telegram doesn't expose reactions via the same mechanism as Feishu.
    Return empty list — approval is handled via callback queries, not reactions.
    """
    return []


def poll_callback(message_id, chat_id, timeout=120, poll_interval=3):
    """
    Wait for a callback query using aiogram's async event system.
    Returns (callback_id, callback_data, from_user_id).
    After receiving the callback, answer it and return.
    """
    cb_id, callback_data, from_user_id = wait_for_callback(message_id, chat_id, timeout=timeout)

    if cb_id is not None:
        # Answer the callback query so Telegram stops the "loading" spinner
        answer_callback_query_sync(cb_id)

    return cb_id, callback_data, from_user_id


def _emoji_map(emoji_type):
    """Map Feishu emoji names to Unicode emoji for Telegram."""
    mapping = {
        'CheckMark': '✅',
        'OK': '👌',
        'ThumbsUp': '👍',
        'Yes': '👍',
        'CrossMark': '❌',
        'NO': '👎',
        'ThumbsDown': '👎',
        'No': '👎',
        'Alarm': '🚨',
    }
    return mapping.get(emoji_type, '❓')
