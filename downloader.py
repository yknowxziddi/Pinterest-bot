import os as WOLF_OS
import re as WOLF_RE
import requests as WOLF_REQ
import threading as WOLF_THR
import signal as WOLF_SIG
from pathlib import Path as WOLF_PTH
from typing import List as WOLF_LST
import yt_dlp as WOLF_YTD
import logging as WOLF_LOG
from fake_useragent import UserAgent as WOLF_UA
import datetime as WOLF_DTM
from telebot import types as WOLF_TYP

class PinterestDownloader:
    def __init__(self, wolf_bot):
        self.wolf_bot = wolf_bot
        self.wolf_ua = WOLF_UA()
        self.wolf_p_dr = WOLF_PTH('Pin')
        self.wolf_p_dr.mkdir(exist_ok=True)
        self.wolf_u_dwn = {}

    def wolf_res(self, wolf_url: str) -> str:
        try:
            wolf_rsp = WOLF_REQ.get(wolf_url, headers={'User-Agent': self.wolf_ua.random}, allow_redirects=True, timeout=10)
            wolf_rsp.raise_for_status()
            return wolf_rsp.url
        except Exception:
            return wolf_url

    def wolf_epi(self, wolf_url: str) -> str:
        wolf_ptr = [
            r"pinterest\.com/pin/(\d+)",
            r"pin\.it/(\w+)"
        ]
        for wolf_pt in wolf_ptr:
            wolf_mtc = WOLF_RE.search(wolf_pt, wolf_url)
            if wolf_mtc:
                return wolf_mtc.group(1)
        return None

    def wolf_fpm(self, wolf_p_id: str) -> dict:
        wolf_a_ur = "https://www.pinterest.com/resource/PinResource/get/"
        wolf_hdr = {
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": self.wolf_ua.random,
            "X-Pinterest-PWS-Handler": f"www/pin/{wolf_p_id}/feedback.js"
        }
        wolf_prm = {
            "source_url": f"/pin/{wolf_p_id}",
            "data": f'{{"options":{{"id":"{wolf_p_id}","field_set_key":"auth_web_main_pin"}}}}'
        }
        wolf_rsp = WOLF_REQ.get(wolf_a_ur, headers=wolf_hdr, params=wolf_prm, timeout=10)
        wolf_rsp.raise_for_status()
        wolf_dat = wolf_rsp.json()
        return wolf_dat.get('resource_response', {}).get('data', {})

    def wolf_exm(self, wolf_p_dat: dict) -> dict:
        wolf_m_inf = {'type': None, 'resources': [], 'signature': wolf_p_dat.get('id') or str(hash(str(wolf_p_dat)))}
        if wolf_p_dat.get('videos'):
            wolf_v_vs = wolf_p_dat['videos'].get('video_list', {})
            for wolf_q in ['V_EXP7', 'V_720P', 'V_480P']:
                if wolf_v_vs.get(wolf_q):
                    wolf_m_inf.update({'type': 'video', 'resources': [wolf_v_vs[wolf_q]['url']]})
                    return wolf_m_inf
        if wolf_p_dat.get('carousel_data'):
            wolf_slts = wolf_p_dat['carousel_data'].get('carousel_slots', [])
            wolf_urls = []
            for wolf_itm in wolf_slts:
                wolf_img = wolf_itm.get('images', {}).get('orig', {}).get('url')
                if wolf_img:
                    wolf_urls.append(wolf_img)
            if wolf_urls:
                wolf_m_inf.update({'type': 'carousel', 'resources': wolf_urls})
                return wolf_m_inf
        wolf_img = wolf_p_dat.get('images', {}).get('orig', {}).get('url')
        if wolf_img:
            wolf_m_inf.update({'type': 'image', 'resources': [wolf_img]})
            return wolf_m_inf
        raise ValueError("Unsupported pin content type")

    def wolf_d_rs(self, wolf_url: str, wolf_f_pth: WOLF_PTH):
        wolf_f_pth.parent.mkdir(parents=True, exist_ok=True)
        if wolf_url.endswith('.m3u8'):
            wolf_opt = {'outtmpl': str(wolf_f_pth)}
            with WOLF_YTD.YoutubeDL(wolf_opt) as wolf_ydl:
                wolf_ydl.download([wolf_url])
        else:
            wolf_r = WOLF_REQ.get(wolf_url, stream=True, timeout=10)
            wolf_r.raise_for_status()
            with open(wolf_f_pth, 'wb') as wolf_f:
                for wolf_chnk in wolf_r.iter_content(1024):
                    wolf_f.write(wolf_chnk)

    def wolf_snd(self, wolf_c_id: int, wolf_fls: WOLF_LST[WOLF_PTH], wolf_m_typ: str, wolf_o_url: str):
        wolf_b_inf = self.wolf_bot.get_me()
        wolf_u_nm = wolf_b_inf.username
        wolf_cap = f"Downloaded ☑️ | By @{wolf_u_nm}"

        if wolf_c_id not in self.wolf_u_dwn:
            self.wolf_u_dwn[wolf_c_id] = []
        self.wolf_u_dwn[wolf_c_id].append({
            'url': wolf_o_url,
            'type': wolf_m_type
            timestamp := WOLF_DTM.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        })

        for wolf_fpt in wolf_fls:
            with open(wolf_fpt, 'rb') as wolf_f:
                if wolf_m_typ == 'video':
                    self.wolf_bot.send_video(wolf_c_id, wolf_f, caption=wolf_cap)
                else:
                    self.wolf_bot.send_photo(wolf_c_id, wolf_f, caption=wolf_cap)
            try:
                wolf_fpt.unlink()
            except Exception:
                pass

    def wolf_prp(self, wolf_url: str, wolf_c_id: int):
        wolf_rsv = self.wolf_res(wolf_url)
        wolf_p_id = self.wolf_epi(wolf_rsv)
        if not wolf_p_id:
            self.wolf_bot.send_message(wolf_c_id, "The link is incorrect, dear!")
            return

        try:
            wolf_msg = self.wolf_bot.send_message(wolf_c_id, "Checking the link... ⏳")
            wolf_p_dat = self.wolf_fpm(wolf_p_id)
            wolf_m_inf = self.wolf_exm(wolf_p_dat)
            self.wolf_bot.edit_message_text("Fetching content... 📥", wolf_c_id, wolf_msg.message_id)
            wolf_d_dir = self.wolf_p_dr / wolf_m_inf['signature']
            wolf_d_dir.mkdir(exist_ok=True)
            wolf_fls = []
            for wolf_idx, wolf_res in enumerate(wolf_m_inf['resources']):
                wolf_ext = 'mp4' if wolf_m_inf['type'] == 'video' else 'jpg'
                wolf_nme = f"{wolf_idx}.{wolf_ext}" if wolf_m_inf['type'] == 'carousel' else f"content.{wolf_ext}"
                wolf_pth = wolf_d_dir / wolf_nme
                self.wolf_d_rs(wolf_res, wolf_pth)
                wolf_fls.append(wolf_pth)
            self.wolf_snd(wolf_c_id, wolf_fls, wolf_m_inf['type'], wolf_o_url=wolf_url)
            self.wolf_bot.delete_message(wolf_c_id, wolf_msg.message_id)
        except Exception as wolf_e:
            self.wolf_bot.send_message(wolf_c_id, f"Oops, an error occurred:\n`{wolf_e}`")

    # This method used in main.py
    def handle_message(self, wolf_msg):
        wolf_url = wolf_msg.text.strip()
        if WOLF_RE.search(r"pinterest\.com|pin\.it", wolf_url):
            WOLF_THR.Thread(target=self.wolf_prp, args=(wolf_url, wolf_msg.chat.id)).start()
