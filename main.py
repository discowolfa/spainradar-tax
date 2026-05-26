from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import time
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from apscheduler.schedulers.blocking import BlockingScheduler

from config import (
    BOT_TOKEN,
    CHANNEL_TIMEZONE,
    CHAT_ID,
    DATABASE_PATH,
    ENABLE_STATUS_COMMANDS,
    MAX_ARTICLES_PER_CYCLE,
    OPENAI_ANALYSIS_WORKERS,
    PUBLISH_DELAY_SECONDS,
    SCHEDULE_INTERVAL_MINUTES,
    STATUS_CHAT_ID,
)
from database import Database
from logger import setup_logging
from publisher import Publisher
from analyzer import Analyzer
from fetchers.rss_fetcher import RSSFetcher
from fetchers.html_fetcher import HTMLFetcher
from sources.sources import SOURCE_LIST
from status_bot import StatusCommandBot, StatusState, format_status_text
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


def publish_limit_reached(published_count: int) -> bool:
    return MAX_ARTICLES_PER_CYCLE > 0 and published_count >= MAX_ARTICLES_PER_CYCLE


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


def build_message(analyzer: Analyzer, item: dict) -> str:
    title = item.get("title", "").strip()
    link = item.get("link", "").strip()
    summary_source = item.get("summary") or title
    article = analyzer.analyze_item(
        title=title,
        link=link,
        summary=summary_source,
    )
    return format_message(article, link)


def status_message(title: str, lines: list[str]) -> str:
    body = "\n".join(escape(line) for line in lines if line)
    return f"<b>{escape(title)}</b>\n\n{body}".strip()


def main() -> None:
    logger = setup_logging()
    logger.info("Starting SpainRadar Tax Telegram bot")

    db = Database(DATABASE_PATH)
    db.setup()

    publisher = Publisher(BOT_TOKEN, CHAT_ID, logger=logger)
    status_publisher = (
        Publisher(BOT_TOKEN, STATUS_CHAT_ID, logger=logger) if STATUS_CHAT_ID else None
    )
    status_state = StatusState()
    status_bot = (
        StatusCommandBot(
            BOT_TOKEN,
            STATUS_CHAT_ID,
            lambda: format_status_text(status_state.snapshot()),
            logger=logger,
        )
        if STATUS_CHAT_ID and ENABLE_STATUS_COMMANDS
        else None
    )
    analyzer = Analyzer(logger=logger)
    rss_fetcher = RSSFetcher(logger=logger)
    html_fetcher = HTMLFetcher(logger=logger)

    def notify_status(title: str, lines: list[str]) -> None:
        if not status_publisher:
            return

        try:
            status_publisher.publish(status_message(title, lines))
        except Exception:
            logger.exception("Status notification failed")

    if status_bot:
        status_bot.start()

    notify_status(
        "SpainRadar Tax: бот запущен",
        [
            f"Основной канал: {CHAT_ID}",
            f"Интервал: {SCHEDULE_INTERVAL_MINUTES} мин.",
            "Команды: /status",
            f"База: {db.count_articles()} записей",
        ],
    )

    def run_cycle() -> None:
        logger.info("Running fetch and publish cycle")
        seen_in_cycle = set()
        published_count = 0
        fetched_count = 0
        new_count = 0
        error_count = 0

        try:
            for source in SOURCE_LIST:
                if publish_limit_reached(published_count):
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
                    fetched_count += len(items)
                except Exception:
                    error_count += 1
                    logger.exception("Source fetch failed: %s", source_name)
                    notify_status(
                        "SpainRadar Tax: ошибка источника",
                        [f"Источник: {source_name}", f"URL: {source_url}"],
                    )
                    continue

                pending_items = []

                for item in items:
                    try:
                        article_id = make_article_id(item)

                        if article_id in seen_in_cycle or db.has_article(article_id):
                            continue

                        seen_in_cycle.add(article_id)
                        title = item.get("title", "").strip()
                        pending_items.append((article_id, title, item))
                        new_count += 1

                        if (
                            MAX_ARTICLES_PER_CYCLE > 0
                            and published_count + len(pending_items)
                            >= MAX_ARTICLES_PER_CYCLE
                        ):
                            break
                    except Exception:
                        error_count += 1
                        logger.exception(
                            "Article deduplication failed for source: %s",
                            source_name,
                        )
                        continue

                if not pending_items:
                    continue

                logger.info(
                    "Analyzing %s new articles from source: %s",
                    len(pending_items),
                    source_name,
                )

                with ThreadPoolExecutor(
                    max_workers=max(1, OPENAI_ANALYSIS_WORKERS)
                ) as executor:
                    futures = {
                        executor.submit(build_message, analyzer, item): (
                            article_id,
                            title,
                        )
                        for article_id, title, item in pending_items
                    }

                    for future in as_completed(futures):
                        article_id, title = futures[future]

                        try:
                            message = future.result()

                            if publisher.publish(message):
                                db.save_article(article_id, title=title)
                                published_count += 1
                                logger.info(
                                    "Published article: %s",
                                    title or article_id,
                                )
                                if PUBLISH_DELAY_SECONDS > 0:
                                    time.sleep(PUBLISH_DELAY_SECONDS)
                                if publish_limit_reached(published_count):
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
                            error_count += 1
                            logger.exception(
                                "Article processing failed for source: %s",
                                source_name,
                            )

                if publish_limit_reached(published_count):
                    break
        except Exception:
            error_count += 1
            logger.exception("Fetch and publish cycle failed")
            notify_status(
                "SpainRadar Tax: ошибка цикла",
                ["Проверьте journalctl/log-файл на сервере."],
            )
        finally:
            db_size = Path(DATABASE_PATH).stat().st_size if Path(DATABASE_PATH).exists() else 0
            db_count = db.count_articles()
            status_state.update(
                last_cycle_at=now_channel_time(CHANNEL_TIMEZONE),
                fetched=fetched_count,
                new=new_count,
                published=published_count,
                errors=error_count,
                db_count=db_count,
                db_size_kb=db_size // 1024,
            )
            if published_count > 0 or error_count > 0:
                notify_status(
                    "SpainRadar Tax: цикл завершен",
                    [
                        f"Получено из RSS: {fetched_count}",
                        f"Новых найдено: {new_count}",
                        f"Опубликовано: {published_count}",
                        f"Ошибок: {error_count}",
                        f"База: {db_count} записей, {db_size // 1024} KB",
                    ],
                )
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
        notify_status("SpainRadar Tax: бот остановлен", ["Получен сигнал остановки."])
    finally:
        publisher.close()
        if status_bot:
            status_bot.stop()
        if status_publisher:
            status_publisher.close()
        db.close()


if __name__ == "__main__":
    main()
