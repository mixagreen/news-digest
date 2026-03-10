"""
📰 Утренний дайджест новостей → Telegram
Версия для GitHub Actions — просто запускается и завершается.
"""

import feedparser
import requests
import os
from datetime import datetime, timezone, timedelta

# ─── НАСТРОЙКИ ────────────────────────────────────────────────
BOT_TOKEN  = os.environ["BOT_TOKEN"]   # берётся из GitHub Secrets
CHAT_ID    = os.environ["CHAT_ID"]     # берётся из GitHub Secrets

HOURS_FRESH  = 24   # считать новость свежей если не старше N часов
MAX_PER_FEED = 5    # максимум статей с одной ленты

# ─── RSS-ЛЕНТЫ ────────────────────────────────────────────────
RSS_FEEDS = [
    {"name": "Хабр",        "url": "https://habr.com/ru/rss/articles/top/?fl=ru"},
    {"name": "TechCrunch",  "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge",   "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Dev.to",      "url": "https://dev.to/feed"},
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage"},
    # Добавляй свои:
    # {"name": "Мой блог", "url": "https://example.com/rss"},
]

# ─── ПАРСИНГ ──────────────────────────────────────────────────

def parse_feed(feed_info: dict) -> list[dict]:
    cutoff   = datetime.now(timezone.utc) - timedelta(hours=HOURS_FRESH)
    articles = []

    try:
        feed = feedparser.parse(feed_info["url"])
        for entry in feed.entries[:20]:
            published = None
            for field in ("published_parsed", "updated_parsed"):
                val = getattr(entry, field, None)
                if val:
                    published = datetime(*val[:6], tzinfo=timezone.utc)
                    break

            if published is None or published >= cutoff:
                articles.append({
                    "source": feed_info["name"],
                    "title":  entry.get("title", "Без заголовка").strip(),
                    "link":   entry.get("link", ""),
                    "date":   published,
                })

            if len(articles) >= MAX_PER_FEED:
                break

        print(f"  ✓ {feed_info['name']}: {len(articles)} статей")

    except Exception as e:
        print(f"  ⚠ {feed_info['name']}: ошибка — {e}")

    return articles


def collect_news() -> list[dict]:
    all_articles = []
    for feed in RSS_FEEDS:
        all_articles.extend(parse_feed(feed))
    all_articles.sort(
        key=lambda x: x["date"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return all_articles


# ─── ФОРМАТИРОВАНИЕ ───────────────────────────────────────────

def format_digest(articles: list[dict]) -> str:
    today = datetime.now().strftime("%d.%m.%Y")

    if not articles:
        return f"📭 *Дайджест {today}*\n\nСвежих новостей нет."

    lines = [f"📰 *Утренний дайджест — {today}*\n"]

    by_source: dict[str, list] = {}
    for art in articles:
        by_source.setdefault(art["source"], []).append(art)

    for source, items in by_source.items():
        lines.append(f"\n*{source}*")
        for art in items:
            title = art["title"][:80] + ("…" if len(art["title"]) > 80 else "")
            lines.append(f"• [{title}]({art['link']})")

    lines.append(f"\n_Статей: {len(articles)} | Источников: {len(by_source)}_")
    return "\n".join(lines)


# ─── ОТПРАВКА ─────────────────────────────────────────────────

def send_telegram(text: str):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id":                  CHAT_ID,
        "text":                     text,
        "parse_mode":               "Markdown",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=data, timeout=15)
    resp.raise_for_status()
    print("✅ Дайджест отправлен!")


# ─── ЗАПУСК ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔄 Собираю новости...")
    articles = collect_news()
    print(f"📦 Итого: {len(articles)} статей")
    message = format_digest(articles)
    send_telegram(message)
