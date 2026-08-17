Telegram-Notion bot


A small bot that turns a Telegram message into a task in Notion. Message the bot and it creates a row in a Notion database, and replies to confirm.


This is a personal learning project: first hands-on build with Python, APIs, and bots.


How it works


1. You send a text message to the bot on Telegram.
2. The bot checks that the message is from you (and silently ignores anyone else).
3. It creates a new page in a Notion database via the Notion API.
4. It replies with “added to Notion”, or “failed: …” if something went wrong.


The bot uses **long polling*. It repeatedly asks Telegram's servers "anything new?" so it needs no public URL, webhook, or open port.


Project status


* [x] Phase 0: project folder, git, virtual environment
* [x] Phase 1: Notion database + integration, verified with "curl"
* [x] Phase 2: Telegram bot, echoes messages back, ignores non-allowed senders
* [x] Phase 3: bot creates real Notion tasks, error handling tested
* [x] Phase 4: deploy to a VPS so it runs without the laptop
* [ ] Phase 5: parse messages with an LLM (due dates, priority, etc.)


Setup
0. Machine setup (one-time)
Only needed once per laptop.
* Install Xcode Command Line Tools (gives you git):
bash
git --version
If it's missing, macOS offers to install it. On Apple Silicon, if you hit a libxcrun architecture error, reinstall cleanly:
bash
sudo rm -rf /Library/Developer/CommandLineTools
xcode-select --install
* Set your git identity (once per machine):
bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
* Install VS Code, then enable the code shell command: Cmd+Shift+P → "Shell Command: Install 'code' command in PATH". Add the Microsoft Python extension.
* Check Python is present (3.11+):
bash
python3 --version
* Create the project folder and initialize git:
bash
mkdir -p ~/Projects/telegram-notion
cd ~/Projects/telegram-notion
git init
* Create .gitignore before anything else, so secrets are never at risk of being committed:
bash
printf '.env\n.venv/\n__pycache__/\n' > .gitignore
* Create the project's virtual environment:
bash
python3 -m venv .venv
source .venv/bin/activate
You'll know it's active when (.venv) appears at the start of the terminal prompt. Run the source line again in every new terminal window/session — it doesn't persist.
* Open the project in VS Code from inside the folder:
bash
 code .
Then Cmd+Shift+P → "Python: Select Interpreter" → pick the one under .venv.


1. Notion
* Create a database with these properties: Name (title), Done (checkbox), Due (date), Raw (text)
* View: List, filtered to Done unchecked, sorted by Due ascending
* Create an internal integration (Access token) at notion.so/my-integrations → Developer tools → Connections
* Connect it to the database: ••• on the database → Connections → add your connection
* Look up the data source ID:
bash
curl -s https://api.notion.com/v1/databases/YOUR_DATABASE_ID \
    -H "Authorization: Bearer $NOTION_TOKEN" \
    -H "Notion-Version: 2025-09-03" \
    | python3 -m json.tool


Take the id from inside data_sources.


2. Telegram


- Message "@BotFather" → "/newbot" → save the token it gives you
- Message "@userinfobot" → note your numeric user ID




3. Environment - Install and run


Create a ".env" file in the project root (never committed — see ".gitignore"):


[
TELEGRAM_TOKEN=
TELEGRAM_ALLOWED_USER_ID=
NOTION_TOKEN=
NOTION_DATABASE_ID=
NOTION_DATA_SOURCE_ID=
]


bash
python3 -m venv .venv 
source .venv/bin/activate 
pip install -r requirements.txt 
python bot.py


You should see "Bot is running. Press Ctrl+C to stop". Message the bot from Telegram to test.


4. Deployment


* Host: UpCloud, Frankfurt
* Server: Ubuntu 26.04 LTS, 2 vCPU / 2 GB RAM / 30 GB NVMe (Starter plan)
* IP: <ip>
* Connect: ssh root@<ip> (SSH key only. See hardening below)
* Create user in server


Server hardening (SSH key only): 
* SSH key-only login (generated locally with ssh-keygen -t ed25519, public key added at server creation)
* Non-root sudo user created
adduser elena 
usermod -aG sudo elena 
rsync --archive --chown=elena:elena ~/.ssh /home/elena


* direct root login and password login were disabled in /etc/ssh/sshd_config (in a separate terminal session)
PermitRootLogin no
PasswordAuthentication no
* Firewall (ufw): allow SSH only, deny everything else by default
sudo ufw allow OpenSSH


* Automatic security updates (unattended-upgrades)
sudo apt update 
sudo apt install unattended-upgrades -y 
sudo dpkg-reconfigure --priority=low unattended-upgrades


* Docker + Docker Compose installed
* Bot running as a restart: unless-stopped container
* 

Files


File
	Purpose
	bot.py
	The bot itself
	requirements.txt
	Exact package versions, for reproducing the environment elsewhere
	.env
	Secrets and config — not committed
	.gitignore
	Keeps .env, .venv/, and __pycache__/ out of git
	





Notes / gotchas


* ".env" is only read at startup — restart the bot after changing it.
* Notion API version "2025-09-03" uses "data_source_id" for creating pages, not "database_id". Older tutorials get this wrong.
* The bot only replies to "TELEGRAM_ALLOWED_USER_ID". Anyone else's messages are silently ignored.
* When logged in in virtual server as user, most commands will require “sudo” at the beginning, to run a command with root’s power




Recurring actions when restarting laptop
When opening Terminal again type commands:


bash
cd ~/Projects/telegram-notion
source .venv/bin/activate