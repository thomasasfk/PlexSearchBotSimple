# Plex Search Search Bot Simple [![Tests](https://github.com/thomasasfk/PlexSearchBotSimple/actions/workflows/pytest.yml/badge.svg)](https://github.com/thomasasfk/PlexSearchBotSimple/actions/workflows/pytest.yml)

A Telegram bot that searches Jackett indexers and uploads to rTorrent. Despite the repository name, this has no Plex integration.

## Commands

| Command | Description | Example | Access Level |
|---------|-------------|---------|--------------|
| `/auth [password]` | Authenticate with the bot | `/auth mypassword` | Anyone |
| `/search [term]` | Search for content | `/search arcane` | Authenticated Users |
| `/get[id]` | Download from a search result | `/get14492` | Authenticated Users |
| `/download [magnet]` | Download using magnet link | `/download magnet:?xt=...` | Authenticated Users |
| `/space` | Check home directory size | `/space` | Authenticated Users |
| `/spaceforce` | Force refresh space calculation | `/spaceforce` | Authenticated Users |
| `/sh [command]` | Execute shell commands | `/sh ls -la` | Admins |

## Setup

1. **Install Python 3.9.2** (pyenv recommended)

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Install Requirements**
   ```bash
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

4. **Run**
   ```bash
   python main.py
   ```

## Environment Configuration

Create a `.env` file with the following variables:

```bash
# Bot configuration
PASSWORD=your_password_here
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456
ADMINS=123456789

# Jackett configuration
JACKETT_API_KEY=abcdef1234567890abcdef1234567890
JACKETT_URL=http://your.jackett.host:port
JACKETT_URL_SEARCH=/your/jackett/api/v2.0/indexers/all/results

# ruTorrent configuration
RU_TORRENT_URL=https://your.rutorrent.host/user/rutorrent/php/addtorrent.php
RU_TORRENT_TOKEN=base64_encoded_credentials
```

| Variable | Description |
|----------|-------------|
| `PASSWORD` | Bot authentication password |
| `TELEGRAM_TOKEN` | Get from [@BotFather](https://t.me/botfather) |
| `ADMINS` | Your Telegram user ID for admin access |
| `JACKETT_API_KEY` | Found in Jackett dashboard |
| `JACKETT_URL` | Your Jackett instance URL with port |
| `JACKETT_URL_SEARCH` | Jackett API endpoint path |
| `RU_TORRENT_URL` | Full path to ruTorrent addtorrent.php |
| `RU_TORRENT_TOKEN` | Base64 encoded username:password |` | `user:password_base64` | Base64 encoded auth |