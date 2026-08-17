import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID"))

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id 

    if sender_id != ALLOWED_USER_ID:
        return

    text = update.message.text
    await update.message.reply_text(text)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, echo))

print("Bot is running. Press Ctrl+C to stop")
app.run_polling()