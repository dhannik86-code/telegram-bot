import json, os, zipfile
from io import BytesIO
from PIL import Image
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ========= CONFIG =========
BOT_TOKEN = "8397711166:AAHXK4FWiU8xD9e62F5gUEWhXGjm32Tis9Y"
ADMIN_ID = 6428107644    # admin telegram UID
CHANNEL_USERNAME = "@joooffy"
DATA_FILE = "data.json"
WORK_DIR = "files"

os.makedirs(WORK_DIR, exist_ok=True)

# ========= DATA =========
def load():
    if not os.path.exists(DATA_FILE):
        return {"authorized": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

# ========= CHANNEL CHECK =========
async def is_joined(bot, uid):
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ("member", "administrator", "creator")
    except:
        return False

# ========= KEYBOARDS =========
JOIN_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton(
        "👉 Join Channel (1 Click)",
        url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
    )],
    [InlineKeyboardButton("✅ I Have Joined", callback_data="check_join")]
])

ADMIN_MENU = ReplyKeyboardMarkup(
    [
        ["✅ Authorize User"],
        ["❌ Remove User"],
        ["📋 Authorized List"]
    ],
    resize_keyboard=True
)

USER_INLINE_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("🖼 Photo ➜ PDF", callback_data="photo_pdf")],
    [InlineKeyboardButton("📄 PDF ➜ ZIP", callback_data="pdf_zip")]
])

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load()

    # Channel join check
    if not await is_joined(context.bot, user.id):
        await update.message.reply_text(
            "⚠️ ACCESS DENIED\nPlease join channel first 👇",
            reply_markup=JOIN_KB
        )
        return

    username = f"@{user.username}" if user.username else "No Username"

    # USER INFO BOX
    box = (
        "┌──────── USER INFO ────────┐\n"
        f"│ Username : {username}\n"
        f"│ UID      : {user.id}\n"
        "└──────────────────────────┘"
    )

    # ADMIN
    if user.id == ADMIN_ID:
        await update.message.reply_text(box)
        await update.message.reply_text(
            "👑 ADMIN PANEL",
            reply_markup=ADMIN_MENU
        )
        return

    # NORMAL USER
    if user.id in data["authorized"]:
        await update.message.reply_text(
            "✅ You are AUTHORIZED\n\n" + box,
            reply_markup=USER_INLINE_KB
        )
    else:
        await update.message.reply_text(
            "❌ You are NOT Authorized\nWait for admin approval\n\n" + box
        )

# ========= JOIN CHECK =========
async def join_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_joined(context.bot, q.from_user.id):
        await q.message.reply_text("✅ Joined successfully\nSend /start")
    else:
        await q.message.reply_text("❌ Still not joined")

# ========= INLINE BUTTON =========
async def user_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = q.data

    if q.data == "photo_pdf":
        await q.message.reply_text("🖼 Send photo")
    elif q.data == "pdf_zip":
        await q.message.reply_text("📄 Send PDF file")

# ========= PHOTO ➜ PDF =========
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "photo_pdf":
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    img_bytes = await file.download_as_bytearray()

    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    pdf_path = os.path.join(WORK_DIR, "photo.pdf")
    img.save(pdf_path, "PDF")

    await update.message.reply_document(
        document=open(pdf_path, "rb"),
        filename="photo.pdf"
    )

    context.user_data["mode"] = None

# ========= PDF ➜ ZIP =========
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "pdf_zip":
        return

    doc = update.message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❌ Please send a PDF file")
        return

    file = await doc.get_file()
    pdf_path = os.path.join(WORK_DIR, doc.file_name)
    await file.download_to_drive(pdf_path)

    zip_name = doc.file_name.replace(".pdf", ".zip")
    zip_path = os.path.join(WORK_DIR, zip_name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pdf_path, arcname=doc.file_name)

    await update.message.reply_document(
        document=open(zip_path, "rb"),
        filename=zip_name
    )

    context.user_data["mode"] = None

# ========= ADMIN PANEL =========
async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    data = load()
    text = update.message.text

    if text == "✅ Authorize User":
        context.user_data["auth"] = True
        await update.message.reply_text("Send USER UID to authorize")

    elif text == "❌ Remove User":
        context.user_data["remove"] = True
        await update.message.reply_text("Send USER UID to remove")

    elif text == "📋 Authorized List":
        if not data["authorized"]:
            await update.message.reply_text("No authorized users")
        else:
            await update.message.reply_text(
                "Authorized UIDs:\n" + "\n".join(map(str, data["authorized"]))
            )

    elif context.user_data.get("auth"):
        uid = int(text)
        if uid not in data["authorized"]:
            data["authorized"].append(uid)
            save(data)
            await context.bot.send_message(
                uid,
                "🎉 You are AUTHORIZED\nSend /start"
            )
        await update.message.reply_text("✅ User Authorized")
        context.user_data["auth"] = False

    elif context.user_data.get("remove"):
        uid = int(text)
        if uid in data["authorized"]:
            data["authorized"].remove(uid)
            save(data)
            await context.bot.send_message(
                uid,
                "❌ Authorization Removed"
            )
        await update.message.reply_text("❌ User Removed")
        context.user_data["remove"] = False

# ========= RUN =========
app = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .connect_timeout(60)
    .read_timeout(60)
    .write_timeout(60)
    .build()
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(join_check, pattern="check_join"))
app.add_handler(CallbackQueryHandler(user_button))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))

print("🤖 FINAL ADMIN + USER BOT RUNNING")
app.run_polling(drop_pending_updates=True)
