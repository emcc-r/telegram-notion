import os
import json
import difflib
import requests
from datetime import date as date_cls
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from cerebras.cloud.sdk import Cerebras

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID"))
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATA_SOURCE_ID = os.getenv("NOTION_DATA_SOURCE_ID")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

cerebras_client = Cerebras(api_key=CEREBRAS_API_KEY)

TASK_SCHEMA = {
      "type": "object",
      "properties": {
            "intent": {
                  "type": "string",
                  "enum": ["new_task", "complete_task"],
                  "description": "'new_task' if the message describes something to do. 'complete_task' if it reports something already done.",
            },
            "title": {"type": "string", "description": "For new_task: a short, clear task title. For complete_task: empty string."},
            "date": {"type": "string", "description": "For new_task: ISO date YYYY-MM-DD if mentioned, otherwise empty string. For complete_task: empty string."},
            "reference": {"type": "string", "description": "For complete_task: a short phrase identifying which existing task this refers to, e.g. 'milk'. For new_task: empty string."},
        },
        "required": ["intent", "title", "date", "reference"],
        "additionalProperties": False,
}

def parse_task(raw_text):
      today = date_cls.today().isoformat()
      response = cerebras_client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[
                  {"role": "system", "content": f"Today's date is {today}. Classify the user's message and extract the relevant fields."},
                  {"role": "user", "content": raw_text},
            ],
            response_format={
                  "type": "json_schema",
                  "json_schema": {"name": "task", "strict": True, "schema": TASK_SCHEMA},
            },
      )
      ## print(response) ##debug line to print full API response to identify error
      result = json.loads(response.choices[0].message.content)
      return result

def add_to_notion(title, due_date, raw_text):
    properties = {
          "Title": {"title": [{"text": {"content": title}}]},
          "FullText": {"rich_text": [{"text": {"content": raw_text}}]},
          "Status": {"checkbox": False},
    }
    if due_date:
          properties["Date"] = {"date": {"start": due_date}}

    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2025-09-03",
            "Content-Type": "application/json",
        },
        json={
            "parent": {"data_source_id": NOTION_DATA_SOURCE_ID},
            "properties": properties,
        },
    )
    response.raise_for_status()
    return response.json()

def get_open_tasks():
      response = requests.post(
            f"https://api.notion.com/v1/data_sources/{NOTION_DATA_SOURCE_ID}/query",
            headers={
                  "Authorization": f"Bearer {NOTION_TOKEN}",
                  "Notion-Version": "2025-09-03",
                  "Content-Type": "application/json",
            },
            json={"filter": {"property": "Status", "checkbox": {"equals": False}}},
      )
      response.raise_for_status()
      results = response.json()["results"]
      return[
            {
                  "id": page["id"],
                  "title": page["properties"]["Title"]["title"][0]["text"]["content"],
            }
            for page in results
      ]

def find_best_match(reference, open_tasks):
      titles = [t["title"] for t in open_tasks]
      matches = difflib.get_close_matches(reference, titles, n=1, cutoff=0.3)
      if not matches:
            return None
      matched_title = matches[0]
      return next(t for t in open_tasks if t["title"] == matched_title)

def mark_task_done(page_id):
      response = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers={
                  "Authorization": f"Bearer {NOTION_TOKEN}",
                  "Notion-Version": "2025-09-03",
                  "Content-Type": "application/json",
            },
            json={"properties": {"Status": {"checkbox": True}}},
      )
      response.raise_for_status()
      return response.json()

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id 

    if sender_id != ALLOWED_USER_ID:
        return

    text = update.message.text

    try:
            parsed = parse_task(text)

            if parsed["intent"] == "new_task":
                  add_to_notion(parsed["title"], parsed["date"], text)
                  await update.message.reply_text(f"added: {parsed['title']}")

            elif parsed["intent"] == "complete_task":
                  open_tasks = get_open_tasks()
                  match = find_best_match(parsed["reference"], open_tasks)
                  if match:
                        mark_task_done(match["id"])
                        await update.message.reply_text(f"marked done: {match['title']}")
                  else:
                        await update.message.reply_text(f"couldn't find an open task matching '{parsed['reference']}'")

            else:
                  add_to_notion(text[:100], "", text)
                  await update.message.reply_text("added (fallback)")
    except Exception as e:
            await update.message.reply_text(f"failed: {e}")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, echo))

print("Bot is running. Press Ctrl+C to stop")
app.run_polling()