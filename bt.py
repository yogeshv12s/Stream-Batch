import os
import json
import threading
import uuid
from urllib.parse import urlparse

from flask import Flask, render_template_string
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------- CONFIG ----------------
API_ID = 26421691
API_HASH = "a2ddc72ad8e40cd501790d36e7605d66"
BOT_TOKEN = "8395757838:AAEcQrm51c_QU8ydR6xQImznDsnRPmd--Us"

# Load domain from config
with open("config.json") as f:
    config = json.load(f)
DOMAIN = config["domain"]

app_bot = Client("batch_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- STORAGE ----------------
user_batches = {}  # temporary user batches before generating
BATCH_FOLDER = "batches"
if not os.path.exists(BATCH_FOLDER):
    os.makedirs(BATCH_FOLDER)

# ---------------- HTML TEMPLATE ----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Batch Files</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
/* Body & container */
body {
    margin: 0;
    padding: 0;
    background-color: #121212;
    font-family: 'Arial', sans-serif;
    color: #fff;
}
.container {
    max-width: 700px;
    margin: auto;
    padding: 20px;
}
/* Logo */
.logo {
    display: block;
    margin: 0 auto 30px auto;
    width: 180px;
}
/* Page Title */
h1 {
    text-align: center;
    color: #00ffcc;
    margin-bottom: 30px;
}
/* File Card */
.card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background-color: #1e1e1e;
    border-radius: 15px;
    padding: 15px 20px;
    margin-bottom: 15px;
    transition: transform 0.2s, box-shadow 0.2s;
}
.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 25px rgba(0,255,204,0.4);
}
/* Filename */
.filename {
    font-size: 18px;
    font-weight: 500;
    text-decoration: none;
    color: #fff;
    flex: 1;
}
.filename:hover {
    color: #00ffcc;
}
/* Play Icon */
.icon {
    color: #00ffcc;
    font-size: 26px;
    margin-left: 15px;
    transition: transform 0.2s, color 0.2s;
    text-decoration: none;
}
.icon:hover {
    transform: scale(1.2);
    color: #00ffaa;
}
/* Responsive */
@media (max-width: 600px) {
    .card {
        flex-direction: column;
        align-items: flex-start;
    }
    .icon {
        margin: 10px 0 0 0;
    }
}
</style>
</head>
<body>
<div class="container">
    <!-- Logo -->
    <img src="https://chadstreamz.sbs/assets/images/log2.png" alt="Logo" class="logo">
    <!-- Page Title -->
    <h1>Batch Files</h1>

    <!-- File Cards -->
    {% for link, filename in files.items() %}
    <div class="card">
        <a class="filename" href="{{ link }}">{{ filename }}</a>
        <a class="icon" href="{{ link }}"><i class="fa-solid fa-play"></i></a>
    </div>
    {% endfor %}
</div>
</body>
</html>

"""

# ---------------- FLASK APP ----------------
flask_app = Flask(__name__)

@flask_app.route("/batch/<batch_id>")
def batch_page(batch_id):
    batch_file = os.path.join(BATCH_FOLDER, f"{batch_id}.json")
    if not os.path.exists(batch_file):
        return "Batch not found", 404

    with open(batch_file, "r") as f:
        files = json.load(f)

    # Prepend domain
    full_links = {DOMAIN + path: name for path, name in files.items()}
    return render_template_string(HTML_TEMPLATE, files=full_links)

def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)

# ---------------- PYROGRAM BOT ----------------

# /start with inline buttons
@app_bot.on_message(filters.command("start") & filters.private)
def start(client, message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add File", callback_data="add")],
            [InlineKeyboardButton("🌐 Generate Batch", callback_data="batch")],
            [InlineKeyboardButton("🗑 Clear Batch", callback_data="clear")]
        ]
    )
    message.reply_text("Hello!👋 Use buttons below for actions.", reply_markup=keyboard)

# Handle inline buttons
@app_bot.on_callback_query()
def button_handler(client, callback_query):
    user_id = callback_query.from_user.id
    action = callback_query.data

    if action == "add":
        callback_query.message.reply_text("Send message as:\n/add <link> <filename>")
    elif action == "batch":
        files = user_batches.get(user_id)
        if not files:
            callback_query.message.reply_text("No files added yet. Use /add to add files.")
            return

        # Save batch as JSON (store only path + query)
        batch_id = str(uuid.uuid4())
        batch_file = os.path.join(BATCH_FOLDER, f"{batch_id}.json")
        json_data = {}
        for full_link, filename in files.items():
            parsed = urlparse(full_link)
            path_only = parsed.path
            if parsed.query:
                path_only += "?" + parsed.query
            json_data[path_only] = filename

        with open(batch_file, "w") as f:
            json.dump(json_data, f, indent=4)

        user_batches[user_id] = {}
        batch_url = f"http://effective-snake-test12s-2aeac175.koyeb.app/batch/{batch_id}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Open Batch", url=batch_url)]
        ])
        callback_query.message.reply_text(
            f"🌟 Your batch link:\n{batch_url}\n\nYou can click the button or copy the link.",
            reply_markup=keyboard
        )
    elif action == "clear":
        user_batches[user_id] = {}
        callback_query.message.reply_text("🗑️ Your batch cleared successfully.")

# /add <link> <filename>
@app_bot.on_message(filters.command("add") & filters.private)
def add_file(client, message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        message.reply_text("Usage: /add <link> <filename>")
        return

    full_link = parts[1].strip()
    filename = parts[2].strip()
    user_id = message.from_user.id

    if user_id not in user_batches:
        user_batches[user_id] = {}
    user_batches[user_id][full_link] = filename

    message.reply_text(f"✅ Added:\nFilename: {filename}\nPath stored: {urlparse(full_link).path}")

# ---------------- RUN BOTH ----------------
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app_bot.run()

