import signal
import os
from dotenv import load_dotenv
from telebot import TeleBot, types
from handlers import handle_start, handle_stats, handle_broadcast, check_membership
from downloader import PinterestDownloader

# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # Make sure this is in your .env file

# Initialize bot
bot = TeleBot(BOT_TOKEN)
bot.downloader = PinterestDownloader(bot)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    handle_start(bot, message)

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    handle_stats(bot, message)

@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(message):
    handle_broadcast(bot, message)

@bot.message_handler(content_types=['text'])
def text_handler(message):
    user_id = message.from_user.id

    # Channel check
    if not check_membership(bot, user_id):
        join_btn = types.InlineKeyboardMarkup()
        join_btn.add(types.InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(user_id, "Please join our channel to use this bot.", reply_markup=join_btn)
        return

    url = message.text.strip()
    if "pinterest.com" in url or "pin.it" in url:
        bot.downloader.handle_message(message)
    else:
        bot.send_message(user_id, "Please send a valid Pinterest link.")

# Shutdown handler
def shutdown_handler(sig, frame):
    print("Stopping bot...")
    bot.stop_polling()
    exit(0)

signal.signal(signal.SIGINT, shutdown_handler)

# Start polling
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
