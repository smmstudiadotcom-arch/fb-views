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
#  SCRAPERAPI
# ══════════════════════════════════════
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "9d538a4836e83b0ff52157ccfe3aca8b")

# ══════════════════════════════════════
#  FACEBOOK REELS
# ══════════════════════════════════════
FB_PAGE_ID     = "100081997113052"
FB_SERVICE     = 9604
FB_QTY_MIN     = 500
FB_QTY_MAX     = 1000
CHECK_INTERVAL = 3600  # каждый час

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
    # Пробуем несколько вариантов URL
    urls_to_try = [
        f"https://m.facebook.com/{FB_PAGE_ID}/reels",
        f"https://www.facebook.com/{FB_PAGE_ID}/reels",
        f"https://m.facebook.com/profile.php?id={FB_PAGE_ID}&sk=reels",
    ]

    for target_url in urls_to_try:
        scraper_url = (
            f"http://api.scraperapi.com/"
            f"?api_key={SCRAPER_API_KEY}"
            f"&url={requests.utils.quote(target_url)}"
            f"&render=true"
            f"&country_code=us"
            f"&premium=true"
            f"&device_type=mobile"
        )
        log(f"🔄 ScraperAPI запрос: {target_url}")
        try:
            resp = requests.get(scraper_url, timeout=90)
            log(f"📥 Status: {resp.status_code} | HTML: {len(resp.text)} символов")

            if resp.status_code != 200:
                log(f"⚠️  Ответ: {resp.text[:300]}")
                continue

            html = resp.text

            urls = set()

            # Паттерн 1: прямые ссылки на Reels
            for match in re.finditer(r'https://www\.facebook\.com/reel/(\d+)', html):
                urls.add(f"https://www.facebook.com/reel/{match.group(1)}")

            # Паттерн 2: мобильные ссылки на Reels
            for match in re.finditer(r'https://m\.facebook\.com/reel/(\d+)', html):
                urls.add(f"https://www.facebook.com/reel/{match.group(1)}")

            # Паттерн 3: video_id в JSON
            for match in re.finditer(r'"video_id":"(\d{10,})"', html):
                urls.add(f"https://www.facebook.com/watch/?v={match.group(1)}")

            # Паттерн 4: /videos/ ссылки
            for match in re.finditer(r'href="(/[^"]+/videos/(\d+)[^"]*)"', html):
                urls.add(f"https://www.facebook.com{match.group(1)}")

            # Паттерн 5: reel в href
            for match in re.finditer(r'href="[^"]*(/reel/(\d+))[^"]*"', html):
                urls.add(f"https://www.facebook.com/reel/{match.group(2)}")

            log(f"🎬 Найдено Reels: {len(urls)}")

            if len(urls) > 0:
                return list(urls)

            # Если 0 — логируем HTML для диагностики
            log(f"⚠️  0 Reels. HTML начало: {html[:500]}")

        except Exception as e:
            log(f"❌ Ошибка ScraperAPI: {e}")

    return []

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
