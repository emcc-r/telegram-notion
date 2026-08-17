import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID"))
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATA_SOURCE_ID = os.getenv("NOTION_DATA_SOURCE_ID")

def add_to_notion(task_text):
    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2025-09-03",
            "Content-Type": "application/json",
        },
        json={
            "parent": {"data_source_id": NOTION_DATA_SOURCE_ID},
            "properties": {
                "Title": {"title": [{"text": {"content": task_text}}]}
            },
        },
    )
    response.raise_for_status()
    return response.json()

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id 

    if sender_id != ALLOWED_USER_ID:
        return

    text = update.message.text

    try:
            add_to_notion(text)
            await update.message.reply_text("added to Notion")
    except Exception as e:
            await update.message.reply_text(f"failed: {e}")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, echo))

print("Bot is running. Press Ctrl+C to stop")
app.run_polling()