## Plex Search Bot, but simple

Few years ago I made [PlexSearchBot](https://github.com/thomasasfk/PlexSearchBot), but it was over-engineered and bad, but worked.

This is a simpler version made to run easily without unnecessary overhead.

---

Setup:

- Install Python 3.9.2 (pyenv recommended)
- Copy `.env.example` to `.env`
```bash
cp .env.example .env
```
- Add telegram token ([docs](https://core.telegram.org/bots/api))
- Add other .env variables
- Setup venv & requirements
```bash
python -m venv .venv
. .venv/Scripts/activate
python -m pip install -r requirements.txt
```
- Run the bot
```bash
python main.py
```
