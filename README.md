# SpainRadar Tax MVP

Lightweight Python Telegram news bot for SpainRadar Tax. This MVP runs on a VPS, fetches news from RSS and HTML sources, translates and analyzes news with the OpenAI API, stores article metadata in SQLite, and publishes updates to Telegram.

## Structure

- `main.py`
- `config.py`
- `database.py`
- `logger.py`
- `analyzer.py`
- `publisher.py`
- `requirements.txt`
- `.env.example`
- `.gitignore`

- `fetchers/`
  - `__init__.py`
  - `rss_fetcher.py`
  - `html_fetcher.py`

- `sources/`
  - `__init__.py`
  - `sources.py`

- `utils/`
  - `__init__.py`
  - `text_utils.py`
  - `date_utils.py`

- `data/`
  - `.gitkeep`
- `logs/`
  - `.gitkeep`
- `systemd/`
  - `spainradar-tax.service.example`

## Requirements

- Python 3.11+
- SQLite
- `feedparser`
- `requests`
- `beautifulsoup4`
- `python-dotenv`
- `APScheduler`
- `python-telegram-bot`
- `openai`

## Configuration

Copy `.env.example` to `.env` and fill in:

- `BOT_TOKEN` - Telegram bot token from BotFather
- `CHAT_ID` - Telegram channel or chat ID
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_MODEL` - model used for translation and analysis, defaults to `gpt-5-mini`
- `DATABASE_PATH` - SQLite database path
- `SCHEDULE_INTERVAL_MINUTES` - fetch interval
- `LOG_PATH` - bot log path
- `CHANNEL_TIMEZONE` - timezone used in Telegram post timestamps, defaults to `Europe/Madrid`
- `MAX_ARTICLES_PER_CYCLE` - max number of articles published during one fetch cycle; `0` means unlimited
- `PUBLISH_DELAY_SECONDS` - delay between Telegram messages, defaults to `2`

If `OPENAI_API_KEY` is empty, the bot keeps running and publishes sanitized source text without AI translation.

## Local run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Server run with systemd

1. Clone the repository on the server.
2. Create `venv` and install dependencies.
3. Create `.env` from `.env.example`.
4. Copy `systemd/spainradar-tax.service.example` to `/etc/systemd/system/spainradar-tax.service`.
5. Update paths and the `User` value in the service file.
6. Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable spainradar-tax
sudo systemctl start spainradar-tax
sudo systemctl status spainradar-tax
```

Logs:

```bash
journalctl -u spainradar-tax -f
```
