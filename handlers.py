import json
import os
from telebot import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_ID"))
DEVELOPER_LINK = os.getenv("DEVELOPER_LINK")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

USERS_FILE = 'users.json'

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def check_membership(bot, user_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ['member', 'creator', 'administrator']
    except:
        return False

def handle_start(bot, message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if not check_membership(bot, user_id):
        join_btn = types.InlineKeyboardMarkup()
        join_btn.add(types.InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(user_id, "Please join our channel to use this bot.", reply_markup=join_btn)
        return

    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)

        bot.send_message(
            ADMIN_ID,
            f"📢 New User Alert!\n"
            f"Username: @{message.from_user.username}\n"
            f"Name: {user_name}\n"
            f"User ID: {user_id}\n"
            f"Total Users: {len(users)}"
        )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Developer", url=DEVELOPER_LINK))
    bot.send_photo(
        chat_id=user_id,
        photo="https://i.ibb.co/4RkNdPdT/image.png",
        caption=f"Hello {user_name}! 👋\n\nWelcome to Pinterest Downloader Bot.\n\nRights reserved © {DEVELOPER_LINK}",
        reply_markup=keyboard
    )

def handle_stats(bot, message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "You are not authorized to use this command.")
        return
    users = load_users()
    bot.send_message(message.chat.id, f"📊 Total Users: {len(users)}")

def handle_broadcast(bot, message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "You are not authorized to use this command.")
        return

    msg_parts = message.text.split(maxsplit=1)
    if len(msg_parts) < 2:
        bot.send_message(message.chat.id, "Usage: /broadcast your message")
        return

    broadcast_message = msg_parts[1]
    users = load_users()
    count = 0

    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 Broadcast:\n\n{broadcast_message}")
            count += 1
        except:
            pass

    bot.send_message(message.chat.id, f"✅ Broadcast sent to {count} users.")
