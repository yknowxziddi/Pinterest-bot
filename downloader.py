import os
import re
import requests
import threading
import signal
from pathlib import Path
from typing import List
from telebot import TeleBot
from telebot.types import Message
from telebot import types
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
import logging
from fake_useragent import UserAgent
import datetime

BOT_TOKEN = '7267049251:AAHDMWIy0CcmvYgfZ5Iwrp_8xt7oAwXCWVE'
logging.getLogger('xgv').setLevel(logging.CRITICAL)

DEVELOPER_LINK = "https://t.me/nobi_shops"
ADMIN_ID = 6706134967

BOT_NAME = "PISCARTBOT"
BOT_DESCRIPTION = "PISCART bot that downloads images, videos from Pinterest and more."
BOT_RIGHTS = f"Bot rights reserved to: {DEVELOPER_LINK} ©"

class PinterestDownloader:
    def __init__(self, bot: TeleBot):
        self.bot = bot
        self.ua = UserAgent()
        self.download_dir = Path('Pin')
        self.download_dir.mkdir(exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.user_downloads = {}

    def resolve_url(self, url: str) -> str:
        try:
            response = requests.get(url, headers={'User-Agent': self.ua.random}, allow_redirects=True, timeout=10)
            response.raise_for_status()
            return response.url
        except Exception:
            return url

    def extract_pin_id(self, url: str) -> str:
        patterns = [
            r"pinterest\.com/pin/(\d+)",
            r"pin\.it/(\w+)"
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def fetch_pin_metadata(self, pin_id: str) -> dict:
        api_url = "https://www.pinterest.com/resource/PinResource/get/"
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": self.ua.random,
            "X-Pinterest-PWS-Handler": f"www/pin/{pin_id}/feedback.js"
        }
        params = {
            "source_url": f"/pin/{pin_id}",
            "data": f'{{"options":{{"id":"{pin_id}","field_set_key":"auth_web_main_pin"}}}}'
        }
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('resource_response', {}).get('data', {})

    def extract_media_info(self, pin_data: dict) -> dict:
        media_info = {'type': None, 'resources': [], 'signature': pin_data.get('id') or str(hash(str(pin_data)))}
        if pin_data.get('videos'):
            video_variants = pin_data['videos'].get('video_list', {})
            for quality in ['V_EXP7', 'V_720P', 'V_480P']:
                if video_variants.get(quality):
                    media_info.update({'type': 'video', 'resources': [video_variants[quality]['url']]})
                    return media_info
        if pin_data.get('carousel_data'):
            slots = pin_data['carousel_data'].get('carousel_slots', [])
            urls = []
            for item in slots:
                image_url = item.get('images', {}).get('orig', {}).get('url')
                if image_url:
                    urls.append(image_url)
            if urls:
                media_info.update({'type': 'carousel', 'resources': urls})
                return media_info
        image_url = pin_data.get('images', {}).get('orig', {}).get('url')
        if image_url:
            media_info.update({'type': 'image', 'resources': [image_url]})
            return media_info
        raise ValueError("Unsupported pin content type")

    def download_resource(self, url: str, file_path: Path):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith('.m3u8'):
            options = {'outtmpl': str(file_path)}
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])
        else:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

    def send_files(self, chat_id: int, files: List[Path], media_type: str, original_url: str):
        bot_info = self.bot.get_me()
        username = bot_info.username
        caption = f"Downloaded ☑️ | By @{username}"

        if chat_id not in self.user_downloads:
            self.user_downloads[chat_id] = []
        self.user_downloads[chat_id].append({
            'url': original_url,
            'type': media_type,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        for file_path in files:
            with open(file_path, 'rb') as f:
                if media_type == 'video':
                    self.bot.send_video(chat_id, f, caption=caption)
                else:
                    self.bot.send_photo(chat_id, f, caption=caption)
            try:
                file_path.unlink()
            except Exception:
                pass

    def process_pin(self, url: str, chat_id: int):
        resolved_url = self.resolve_url(url)
        pin_id = self.extract_pin_id(resolved_url)
        if not pin_id:
            self.bot.send_message(chat_id, "Invalid link!")
            return

        try:
            msg = self.bot.send_message(chat_id, "Checking the link... ⏳")
            pin_data = self.fetch_pin_metadata(pin_id)
            media_info = self.extract_media_info(pin_data)
            self.bot.edit_message_text("Downloading... 📥", chat_id, msg.message_id)
            download_dir = self.download_dir / media_info['signature']
            download_dir.mkdir(exist_ok=True)
            files = []
            for idx, res_url in enumerate(media_info['resources']):
                ext = 'mp4' if media_info['type'] == 'video' else 'jpg'
                name = f"{idx}.{ext}" if media_info['type'] == 'carousel' else f"content.{ext}"
                file_path = download_dir / name
                self.download_resource(res_url, file_path)
                files.append(file_path)
            self.send_files(chat_id, files, media_info['type'], original_url=url)
            self.bot.delete_message(chat_id, msg.message_id)
        except Exception as e:
            self.bot.send_message(chat_id, f"Oops, an error occurred:\n`{e}`")

    def handle_message(self, msg: Message):
        url = msg.text.strip()
        if re.search(r"pinterest\.com|pin\.it", url):
            threading.Thread(target=self.process_pin, args=(url, msg.chat.id)).start()

    def shutdown(self):
        self.executor.shutdown(wait=True)

def create_bot(token: str) -> TeleBot:
    bot = TeleBot(token)
    bot.pinterest_downloader = PinterestDownloader(bot)

    def start_command(msg: Message):
        user_name = msg.from_user.first_name
        response_text = f"Hello {user_name}! 👋\n\nI am {BOT_NAME}, {BOT_DESCRIPTION}\n\n{BOT_RIGHTS}"

        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("DEVELOPER", url=DEVELOPER_LINK)
        button2 = types.InlineKeyboardButton("RUN to start using", callback_data="run_bot")
        keyboard.add(button1, button2)

        bot.send_photo(
            chat_id=msg.chat.id,
            photo="https://i.ibb.co/0yzZHrjc/image.jpg",
            caption=response_text,
            parse_mode="HTML",
            has_spoiler=True,
            reply_markup=keyboard
        )

    def callback_handler(call: types.CallbackQuery):
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

        if call.data == "run_bot":
            bot.send_message(
                chat_id=call.message.chat.id,
                text="Done, you can now use the bot. Send a Pinterest image/video link and I will download it for you 😁"
            )

    def admin_command(msg: Message):
        if msg.from_user.id == ADMIN_ID:
            bot.send_message(msg.chat.id, "Admin panel (mock feature).")
        else:
            bot.send_message(msg.chat.id, "Sorry, you are not an admin of this bot.")

    bot.message_handler(commands=['start'])(start_command)
    bot.message_handler(commands=['admin'])(admin_command)
    bot.callback_query_handler(func=lambda call: True)(callback_handler)
    bot.message_handler(content_types=['text'])(bot.pinterest_downloader.handle_message)

    return bot

if __name__ == '__main__':
    bot_instance = create_bot(BOT_TOKEN)

    def shutdown_handler(sig, frame):
        bot_instance.stop_polling()
        if os.path.exists('Pin'):
            for root, dirs, files in os.walk('Pin', topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir('Pin')

        if hasattr(bot_instance, 'pinterest_downloader') and bot_instance.pinterest_downloader:
            bot_instance.pinterest_downloader.shutdown()
        exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)

    try:
        bot_instance.infinity_polling()
    except Exception as e:
        print(f"Error running bot: {e}")
        bot_instance.stop_polling()
        if hasattr(bot_instance, 'pinterest_downloader') and bot_instance.pinterest_downloader:
            bot_instance.pinterest_downloader.shutdown()
