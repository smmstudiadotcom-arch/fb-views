import requests
import random
import time
import os
import re
from datetime import datetime

# ══════════════════════════════════════
#  JAP
# ══════════════════════════════════════
JAP_API_KEY = "ec2fb6c8f5a4ea7ba6cf532e87a09895"
JAP_API_URL = "https://justanotherpanel.com/api/v2"

# ══════════════════════════════════════
#  FACEBOOK REELS (cookies)
# ══════════════════════════════════════
FB_PAGE_ID     = "100081997113052"
FB_SERVICE     = 9604
FB_QTY_MIN     = 500
FB_QTY_MAX     = 1000
CHECK_INTERVAL = 3600  # каждый час

C_USER = os.environ.get("FB_C_USER", "61553351803414")
XS     = os.environ.get("FB_XS",     "8%3AeGYkn8717BMe-g%3A2%3A1774503965%3A-1%3A-1%3A%3AAcw0XpXFaM1nyL4JOlFdYs_Ud6Y079Nz9FGx2eBrLs8")
DATR   = os.environ.get("FB_DATR",   "gvGqaR00HB8BBQCtWvA_ZrBw")
FR     = os.environ.get("FB_FR",     "1fXp7RjNu6E4tlLeA.AWc5dZieQn71hppDlUvFZLqzKA5QYrGNQzKXlgvHvbeVm7zLhgs.Bp6coy..AAA.0.0.Bp6coy.AWeEM5yj4-p0pnZr32HrLye4l9I")
SB     = os.environ.get("FB_SB",     "hfGqaZIWmBX2PQV9iqh9Tr1V")

FB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Cookie": f"c_user={C_USER}; xs={XS}; datr={DATR}; fr={FR}; sb={SB}; ps_l=1; ps_n=1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
    "Referer": "https://m.facebook.com/",
}

# Хранение обработанных Reels
STATE_FILE = "processed_reels.txt"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [FB-Reels] {msg}", flush=True)

def load_processed():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed(data):
    with open(STATE_FILE, "w") as f:
        for item in data:
            f.write(f"{item}\n")

def check_balance():
    try:
        resp = requests.post(JAP_API_URL, data={"key": JAP_API_KEY, "action": "balance"}, timeout=10)
        if resp.text.strip():
            data = resp.json()
            if "balance" in data:
                log(f"💰 Баланс: ${data['balance']} {data.get('currency', '')}")
    except Exception as e:
        log(f"❌ Ошибка баланса: {e}")

def create_jap_order(link):
    quantity = random.randint(FB_QTY_MIN, FB_QTY_MAX)
    payload = {"key": JAP_API_KEY, "action": "add", "service": FB_SERVICE, "link": link, "quantity": quantity}
    try:
        log(f"📤 Заказ: service={FB_SERVICE}, qty={quantity}")
        resp = requests.post(JAP_API_URL, data=payload, timeout=15)
        log(f"📥 JAP: {resp.status_code} | {repr(resp.text[:150])}")
        if not resp.text.strip():
            log("❌ Пустой ответ JAP")
            return
        data = resp.json()
        if "order" in data:
            log(f"✅ Заказ! ID: {data['order']} | Кол-во: {quantity}")
        elif "error" in data:
            log(f"❌ JAP ошибка: {data['error']}")
    except Exception as e:
        log(f"❌ Ошибка заказа: {e}")

def fetch_reels():
    # Пробуем несколько URL для поиска Reels
    urls_to_try = [
        f"https://m.facebook.com/{FB_PAGE_ID}/reels",
        f"https://m.facebook.com/profile.php?id={FB_PAGE_ID}&sk=reels",
        f"https://m.facebook.com/profile.php?id={FB_PAGE_ID}",
    ]

    all_urls = set()

    for target_url in urls_to_try:
        log(f"🔄 Запрос: {target_url}")
        try:
            resp = requests.get(target_url, headers=FB_HEADERS, timeout=15)
            log(f"📥 Status: {resp.status_code} | HTML: {len(resp.content)} байт")

            if resp.status_code != 200:
                log(f"⚠️  Ответ: {resp.content[:200]}")
                continue

            html = resp.content.decode("utf-8", errors="ignore")

            # Паттерн 1: /reel/ID
            for match in re.finditer(r'/reel/(\d{10,})', html):
                all_urls.add(f"https://www.facebook.com/reel/{match.group(1)}")

            # Паттерн 2: video_id в JSON
            for match in re.finditer(r'"video_id":"(\d{10,})"', html):
                all_urls.add(f"https://www.facebook.com/reel/{match.group(1)}")

            # Паттерн 3: /videos/ID
            for match in re.finditer(r'/videos/(\d{10,})', html):
                all_urls.add(f"https://www.facebook.com/reel/{match.group(1)}")

            # Паттерн 4: watch/?v=ID
            for match in re.finditer(r'watch/\?v=(\d{10,})', html):
                all_urls.add(f"https://www.facebook.com/reel/{match.group(1)}")

            if all_urls:
                log(f"🎬 Найдено Reels: {len(all_urls)}")
                return list(all_urls)

        except Exception as e:
            log(f"❌ Ошибка: {e}")

    if not all_urls:
        log(f"⚠️  0 Reels найдено по всем URL")

    return list(all_urls)

def main():
    log("🚀 Facebook Reels бот запущен!")
    log(f"📘 Страница: {FB_PAGE_ID} | Услуга: {FB_SERVICE} | {FB_QTY_MIN}-{FB_QTY_MAX}")
    check_balance()

    processed = load_processed()

    # Первый запуск — запоминаем существующие Reels, не крутим
    if not processed:
        log("📌 Первый запуск — запоминаю существующие Reels...")
        reels = fetch_reels()
        if reels:
            processed.update(reels)
            save_processed(processed)
            log(f"📌 Запомнено {len(reels)} Reels. Жду новые...")

    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            reels = fetch_reels()
            new_reels = [url for url in reels if url not in processed]

            if new_reels:
                log(f"🆕 Новых Reels: {len(new_reels)}")
                for reel_url in new_reels:
                    log(f"🆕 {reel_url}")
                    create_jap_order(reel_url)
                    processed.add(reel_url)
                    time.sleep(2)
                save_processed(processed)
            else:
                log("🔍 Нет новых Reels")
        except Exception as e:
            log(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
