# Telegram → Notion Task Bot

A small bot that turns a Telegram message into a task in Notion. Message the bot, it creates a row in a Notion database, and replies to confirm.

This is a personal learning project: first hands-on build with Python, APIs, and bots.

## How it works

1. You send a text message to the bot on Telegram.
2. The bot checks that the message is from you (and silently ignores anyone else).
3. The message is sent to an LLM (Cerebras, `gpt-oss-120b`), which classifies it and extracts structured fields:
   - **`new_task`** — something to do. Extracts a clean title and a date, if one was mentioned.
   - **`complete_task`** — something already done. Extracts a short reference phrase (e.g. "milk").
4. For a new task: creates a page in the Notion database.
   For completing a task: fetches open (unchecked) tasks from Notion, fuzzy-matches the reference phrase against their titles, and checks off the closest match — or replies that it couldn't find one, rather than guessing wrong.
5. Replies with `added: ...`, `marked done: ...`, `couldn't find...`, or `failed: ...`.

The bot uses **long polling** - it repeatedly asks Telegram's servers "anything new?" so it needs no public URL, webhook, or open port.

## Project status

- [x] Phase 0 — project folder, git, virtual environment
- [x] Phase 1 — Notion database + integration, verified with `curl`
- [x] Phase 2 — Telegram bot, echoes messages back, ignores non-allowed senders
- [x] Phase 3 — bot creates real Notion tasks, error handling tested
- [x] Phase 4 — deployed to a VPS, running in Docker, survives reboots
- [x] Phase 5 — LLM parsing (Cerebras): clean titles, dates, and completing existing tasks by natural language

## Setup

### 0. Machine setup (one-time)

Only needed once per laptop — skip if already done.

- Install **Xcode Command Line Tools** (gives you `git`):
  ```bash
  git --version
  ```
  If it's missing, macOS offers to install it. On Apple Silicon, if you hit a `libxcrun` architecture error, reinstall cleanly:
  ```bash
  sudo rm -rf /Library/Developer/CommandLineTools
  xcode-select --install
  ```
- Set your git identity (once per machine):
  ```bash
  git config --global user.name "Your Name"
  git config --global user.email "you@example.com"
  ```
- Install **[VS Code](https://code.visualstudio.com)**, then enable the `code` shell command: `Cmd+Shift+P` → "Shell Command: Install 'code' command in PATH". Add the Microsoft Python extension.
- Check **Python** is present (3.11+):
  ```bash
  python3 --version
  ```
- Create the project folder and initialize git:
  ```bash
  mkdir -p ~/Projects/telegram-notion
  cd ~/Projects/telegram-notion
  git init
  ```
- Create `.gitignore` **before** anything else, so secrets are never at risk of being committed:
  ```bash
  printf '.env\n.venv/\n__pycache__/\n' > .gitignore
  ```
- Create the project's virtual environment:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
  You'll know it's active when `(.venv)` appears at the start of the terminal prompt. Run the `source` line again in every new terminal window/session — it doesn't persist.
- Open the project in VS Code from inside the folder:
  ```bash
  code .
  ```
  Then `Cmd+Shift+P` → "Python: Select Interpreter" → pick the one under `.venv`.

### 1. Notion

- Create a database with these properties: `Name` (title), `Done` (checkbox), `Due` (date), `Raw` (text)
- View: List, filtered to `Done` unchecked, sorted by `Due` ascending
- Create an internal integration (Access token) at `notion.so/my-integrations` → `Developer tools` → `Connections`
- Connect it to the database: `•••` on the database → **Connections** → add your connection
- Look up the data source ID:
  ```
  curl -s https://api.notion.com/v1/databases/YOUR_DATABASE_ID \
    -H "Authorization: Bearer $NOTION_TOKEN" \
    -H "Notion-Version: 2025-09-03" \
    | python3 -m json.tool
  ```
  Take the `id` from inside `data_sources`.

### 2. Telegram

- Message `@BotFather` → `/newbot` → save the token it gives you
- Message `@userinfobot` → note your numeric user ID

### 3. Cerebras (LLM parsing)

- Sign up at [cloud.cerebras.ai](https://cloud.cerebras.ai) and add a payment method — required for any API access, but using the open-weight `gpt-oss-120b` model with the free trial credit costs effectively nothing at this project's message volume
- Create an API key from the console
- Model used: `gpt-oss-120b`, with `response_format: json_schema` + `strict: true` for reliable structured output — see `TASK_SCHEMA` in `bot.py`

### 4. Environment

Create a `.env` file in the project root (never committed — see `.gitignore`):

```
TELEGRAM_TOKEN=
TELEGRAM_ALLOWED_USER_ID=
NOTION_TOKEN=
NOTION_DATABASE_ID=
NOTION_DATA_SOURCE_ID=
CEREBRAS_API_KEY=
```

### 5. Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

You should see `Bot is running. Press Ctrl+C to stop`. Message the bot from Telegram to test.

## Deployment

- **Host:** UpCloud, Frankfurt
- **Server:** Ubuntu 26.04 LTS, 2 vCPU / 2 GB RAM / 30 GB NVMe (Starter plan)
- **IP:** `<your-server-ip>`
- **Connect:** `ssh elena@<your-server-ip>` (SSH key only — see hardening below)

### Server hardening

- [x] SSH key-only login (generated locally with `ssh-keygen -t ed25519`, public key added at server creation)
- [x] Non-root sudo user created, direct root login and password login both disabled
- [x] Firewall (`ufw`) — allow SSH only, deny everything else by default
- [x] Automatic security updates (`unattended-upgrades`)
- [x] Docker + Docker Compose installed
- [x] Bot running as a `restart: unless-stopped` container

**How the sudo user was created**, for reference if this server is ever rebuilt:

```bash
adduser elena
usermod -aG sudo elena
rsync --archive --chown=elena:elena ~/.ssh /home/elena
```

Then, only after confirming `ssh elena@<ip>` worked in a **separate** terminal session, root and password login were disabled in `/etc/ssh/sshd_config`:

```
PermitRootLogin no
PasswordAuthentication no
```

followed by `sudo systemctl restart ssh`.

> **Gotcha:** Ubuntu cloud images sometimes ship `/etc/ssh/sshd_config.d/50-cloud-init.conf`, which can override `PasswordAuthentication` set in the main config (that file's setting wins because `Include` loads it before the rest of the file, and OpenSSH uses the *first* value it sees). Worth checking that file's contents if password login won't disable.

**Firewall** — allow only SSH, deny everything else by default:

```bash
sudo ufw allow OpenSSH
sudo ufw enable
```

Allow *before* enable, or you can lock yourself out.

**Automatic security patches:**

```bash
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### Docker

The bot runs as a Docker container rather than a bare Python process — this is what makes `restart: unless-stopped` possible, and what makes redeploying a two-command affair instead of manually copying files around.

**One-time: install Docker + Compose** (see [Docker's official Ubuntu install docs](https://docs.docker.com/engine/install/ubuntu/) for the full apt-repository setup):

```bash
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
sudo usermod -aG docker elena   # log out and back in for this to take effect
```

**One-time: get the code and secrets onto the server:**

```bash
# on the server
cd ~
git clone https://github.com/YOUR_USERNAME/telegram-notion.git
cd telegram-notion
```

```bash
# from your Mac — .env is never in git, so it travels separately
scp ~/Projects/telegram-notion/.env elena@<your-server-ip>:~/telegram-notion/.env
```

**Build and start:**

```bash
docker compose up -d --build
docker compose logs -f    # confirm "Bot is running..." appears
```

**Redeploying after a code change**, from here on:

```bash
# on your Mac
git add . && git commit -m "..." && git push
```

```bash
# on the server
cd ~/telegram-notion
git pull
docker compose up -d --build
```

## Files

| File | Purpose |
|---|---|
| `bot.py` | The bot itself |
| `requirements.txt` | Exact package versions, for reproducing the environment elsewhere |
| `Dockerfile` | Recipe for building the bot's container image |
| `compose.yml` | How to run that image — env vars, restart policy |
| `.env` | Secrets and config — not committed, copied to the server by hand via `scp` |
| `.gitignore` | Keeps `.env`, `.venv/`, and `__pycache__/` out of git |

Scratch/throwaway test scripts (`parse_test.py`, `notion_test.py`) were used to test the Cerebras call and the Notion query/match/update logic in isolation before wiring them into `bot.py`. Safe to delete once confirmed working — same role `body.json` played back in Phase 1.

## Notes / gotchas

- `.env` is only read at startup — restart the bot (or `docker compose up -d --build`) after changing it.
- Notion API version `2025-09-03` uses `data_source_id` for creating pages, not `database_id`. Older tutorials get this wrong.
- The bot only replies to `TELEGRAM_ALLOWED_USER_ID` — anyone else's messages are silently ignored.
- **Only run one instance at a time.** If the container is running on the server, `bot.py` should not also be running on the laptop — two instances polling the same Telegram token will fight over messages.
- Python buffers `print()` output when it isn't attached to a real terminal, which is the case inside a container — so log lines can appear delayed or missing even though the code is running fine. Fixed with `ENV PYTHONUNBUFFERED=1` in the `Dockerfile`.
- GitHub Personal Access Tokens (used for `git push`/`clone` over HTTPS) and the Notion access token are unrelated, despite similar names — don't confuse the two, and don't store the GitHub one in `.env` (nothing in the bot's code reads it).
- **A Docker deploy needs both `bot.py` and `requirements.txt` pushed together.** Adding a new import without updating `requirements.txt` builds a container that crash-loops on `ModuleNotFoundError` — `restart: unless-stopped` will keep retrying forever, but it'll never succeed until the dependency list catches up.
- **Notion's data source query is `POST /v1/data_sources/{id}/query`** — despite "query" sounding read-only, and despite the URL living under `data_sources`. Updating a single page afterward is a *different* endpoint entirely: `PATCH /v1/pages/{page_id}` — easy to accidentally leave pointed at the query URL when adapting one function from the other.
- **`strict: true` on an LLM's structured output is not a hard guarantee.** The same schema and prompt returned `"new_task"` on one call and `"new task"` (with a space) on another. Normalize/validate values in code rather than trust the API's promise at face value.
- The completion flow only ever checks off a task when the fuzzy match clears a similarity threshold — an unmatched reference replies with "couldn't find" rather than guessing. Marking the *wrong* task done would be worse than doing nothing.
