import hashlib
from html import escape
from urllib.parse import urlparse

from apscheduler.schedulers.blocking import BlockingScheduler

from config import (
    BOT_TOKEN,
    CHANNEL_TIMEZONE,
    CHAT_ID,
    DATABASE_PATH,
    MAX_ARTICLES_PER_CYCLE,
    SCHEDULE_INTERVAL_MINUTES,
)
from database import Database
from logger import setup_logging
from publisher import Publisher
from analyzer import Analyzer
from fetchers.rss_fetcher import RSSFetcher
from fetchers.html_fetcher import HTMLFetcher
from sources.sources import SOURCE_LIST
from utils.date_utils import now_channel_time


def make_article_id(item: dict) -> str:
    article_id = item.get("id") or item.get("link") or item.get("title")
    if article_id:
        return article_id

    raw = f"{item.get('title', '')}|{item.get('summary', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def source_domain(link: str) -> str:
    domain = urlparse(link).netloc
    return domain.removeprefix("www.")


def priority_marker(priority: str) -> str:
    markers = {
        "high": "🔴",
        "medium": "🟡",
        "low": "🔵",
    }
    return markers.get(priority, markers["medium"])


def priority_label(priority: str) -> str:
    labels = {
        "high": "высокий",
        "medium": "средний",
        "low": "низкий",
    }
    return labels.get(priority, labels["medium"])


def format_message(article: dict, link: str) -> str:
    domain = source_domain(link)
    source = link
    if domain:
        source = f"{link}\n\n{domain}"

    priority = article.get("priority", "medium")
    marker = priority_marker(priority)
    label = priority_label(priority)
    headline = escape(article.get("headline", "").strip())
    summary = escape(article.get("summary", "").strip())
    analysis = escape(article.get("analysis", "").strip())
    audience = escape(article.get("audience", "").strip())
    action = escape(article.get("action", "").strip())
    source = escape(source)

    return (
        f"{now_channel_time(CHANNEL_TIMEZONE)}\n\n"
        f"<b>{headline}</b>\n\n"
        f"Приоритет: {label} {marker}\n\n"
        f"📌 Кратко:\n{summary}\n\n"
        f"🤖 Анализ:\n{analysis}\n\n"
        f"👥 Кого касается:\n{audience}\n\n"
        f"✅ Что делать:\n{action}\n\n"
        f"🔗 Источник:\n{source}"
    ).strip()


def main() -> None:
    logger = setup_logging()
    logger.info("Starting SpainRadar Tax Telegram bot")

    db = Database(DATABASE_PATH)
    db.setup()

    publisher = Publisher(BOT_TOKEN, CHAT_ID, logger=logger)
    analyzer = Analyzer(logger=logger)
    rss_fetcher = RSSFetcher(logger=logger)
    html_fetcher = HTMLFetcher(logger=logger)

    def run_cycle() -> None:
        logger.info("Running fetch and publish cycle")
        seen_in_cycle = set()
        published_count = 0

        try:
            for source in SOURCE_LIST:
                if published_count >= MAX_ARTICLES_PER_CYCLE:
                    logger.info(
                        "Reached publish limit for cycle: %s",
                        MAX_ARTICLES_PER_CYCLE,
                    )
                    break

                source_name = source.get("name", source.get("url", "unknown source"))
                source_url = source.get("url", "")
                source_type = source.get("type", "rss")

                try:
                    if source_type == "rss":
                        items = rss_fetcher.fetch(source_url)
                    else:
                        items = html_fetcher.fetch(source_url)

                    logger.info(
                        "Source fetch completed: %s (%s entries)",
                        source_name,
                        len(items),
                    )
                except Exception:
                    logger.exception("Source fetch failed: %s", source_name)
                    continue

                for item in items:
                    try:
                        article_id = make_article_id(item)

                        if article_id in seen_in_cycle or db.has_article(article_id):
                            continue

                        seen_in_cycle.add(article_id)

                        title = item.get("title", "").strip()
                        link = item.get("link", "").strip()
                        summary_source = item.get("summary") or title
                        article = analyzer.analyze_item(
                            title=title,
                            link=link,
                            summary=summary_source,
                        )
                        message = format_message(article, link)

                        if publisher.publish(message):
                            db.save_article(article_id, title=title)
                            published_count += 1
                            logger.info("Published article: %s", title or article_id)
                            if published_count >= MAX_ARTICLES_PER_CYCLE:
                                logger.info(
                                    "Reached publish limit for cycle: %s",
                                    MAX_ARTICLES_PER_CYCLE,
                                )
                                break
                        else:
                            logger.error(
                                "Publish failed, article was not marked as sent: %s",
                                title or article_id,
                            )
                    except Exception:
                        logger.exception(
                            "Article processing failed for source: %s",
                            source_name,
                        )
                        continue
        except Exception:
            logger.exception("Fetch and publish cycle failed")
        finally:
            logger.info("Fetch and publish cycle finished")

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_cycle,
        "interval",
        minutes=SCHEDULE_INTERVAL_MINUTES,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )

    try:
        run_cycle()
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping SpainRadar Tax bot")
    finally:
        publisher.close()
        db.close()


if __name__ == "__main__":
    main()
