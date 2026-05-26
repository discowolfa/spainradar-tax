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
- `STATUS_CHAT_ID` - optional test/admin chat for technical status notifications
- `ENABLE_STATUS_COMMANDS` - enable `/status` and `/health` commands in `STATUS_CHAT_ID`
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_MODEL` - model used for translation and analysis, defaults to `gpt-5-mini`
- `DATABASE_PATH` - SQLite database path
- `SCHEDULE_INTERVAL_MINUTES` - fetch interval
- `LOG_PATH` - bot log path
- `LOG_MAX_BYTES` - max size of one log file before rotation
- `LOG_BACKUP_COUNT` - number of rotated log files to keep
- `CHANNEL_TIMEZONE` - timezone used in Telegram post timestamps, defaults to `Europe/Madrid`
- `MAX_ARTICLES_PER_CYCLE` - max number of articles published during one fetch cycle; `0` means unlimited
- `PUBLISH_DELAY_SECONDS` - delay between Telegram messages, defaults to `0.5`
- `OPENAI_ANALYSIS_WORKERS` - number of parallel OpenAI analysis workers, defaults to `5`

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

## Production Deploy

Recommended production path:

```bash
/opt/spainradar-tax
```

Connect to the server:

```bash
ssh root@49.12.229.205
```

Install system packages:

```bash
apt update
apt install -y git python3 python3-venv python3-pip sqlite3
```

Clone the project:

```bash
cd /opt
git clone https://github.com/discowolfa/spainradar-tax.git
cd /opt/spainradar-tax
```

If the project already exists:

```bash
cd /opt/spainradar-tax
git pull origin main
```

Create the virtual environment:

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Create server config:

```bash
cp .env.example .env
nano .env
```

Production `.env` example:

```env
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=@spainradar_tax
STATUS_CHAT_ID=your_test_or_admin_chat_id
ENABLE_STATUS_COMMANDS=true
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-mini
DATABASE_PATH=data/spainradar_tax.db
SCHEDULE_INTERVAL_MINUTES=10
LOG_PATH=logs/spainradar_tax.log
LOG_MAX_BYTES=5242880
LOG_BACKUP_COUNT=5
CHANNEL_TIMEZONE=Europe/Madrid
MAX_ARTICLES_PER_CYCLE=0
PUBLISH_DELAY_SECONDS=0.5
OPENAI_ANALYSIS_WORKERS=5
```

Manual smoke test:

```bash
./venv/bin/python -m compileall -q .
timeout 60 ./venv/bin/python main.py
```

The bot should send technical status messages to `STATUS_CHAT_ID`. News posts go only to `CHAT_ID`.

## systemd

Create the service:

```bash
cp systemd/spainradar-tax.service.example /etc/systemd/system/spainradar-tax.service
nano /etc/systemd/system/spainradar-tax.service
```

Use these production values:

```ini
WorkingDirectory=/opt/spainradar-tax
ExecStart=/opt/spainradar-tax/venv/bin/python /opt/spainradar-tax/main.py
User=root
EnvironmentFile=/opt/spainradar-tax/.env
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable spainradar-tax
systemctl start spainradar-tax
systemctl status spainradar-tax
```

Logs:

```bash
journalctl -u spainradar-tax -f
```

## Monitoring

You do not need to watch the server all the time.

The bot sends operational status messages to `STATUS_CHAT_ID`, which should be a test/admin channel. Regular news posts go only to `CHAT_ID`.

The bot does not send a "cycle finished" message for empty healthy cycles. This keeps the test/admin channel quiet.

Automatic status messages are sent when:

- the bot starts;
- a cycle publishes at least one news post;
- a cycle has errors;
- a source or processing error occurs.

Manual status check in the test/admin channel:

```text
/status
```

or:

```text
/health
```

The bot replies with the latest known status:

```text
SpainRadar Tax: статус

Последний цикл: 26.05.2026, 14:40
Получено из RSS: 65
Новых найдено: 0
Опубликовано: 0
Ошибок: 0
База: 65 записей, 32 KB
```

Normal status message:

```text
SpainRadar Tax: цикл завершен

Получено из RSS: 65
Новых найдено: 0
Опубликовано: 0
Ошибок: 0
База: 65 записей, 32 KB
```

If `Ошибок: 0`, the bot is healthy.

Check the server manually only when:

- status messages stop arriving in the test/admin channel;
- `Ошибок` is greater than `0`;
- news stops appearing in the main channel;
- you changed tokens, `.env`, code, or dependencies.

Useful manual checks:

```bash
systemctl status spainradar-tax --no-pager
```

This shows whether the service is alive. Healthy state:

```text
Active: active (running)
```

```bash
journalctl -u spainradar-tax -f
```

This shows the live bot log. Use it only for debugging.

```bash
sqlite3 /opt/spainradar-tax/data/spainradar_tax.db "select count(*) from articles;"
```

This shows how many articles are already marked as published.

Restart after code updates:

```bash
cd /opt/spainradar-tax
git pull origin main
./venv/bin/pip install -r requirements.txt
systemctl restart spainradar-tax
systemctl status spainradar-tax
```

Stop:

```bash
systemctl stop spainradar-tax
```

Local bot logs are rotated automatically:

```bash
ls -lh /opt/spainradar-tax/logs
```

SQLite database:

```bash
sqlite3 /opt/spainradar-tax/data/spainradar_tax.db "select count(*) from articles;"
```
