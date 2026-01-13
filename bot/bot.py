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

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("8397711166:AAHXK4FWiU8xD9e62F5gUEWhXGjm32Tis9Y")  # Render ENV
ADMIN_ID = int(os.environ.get("6428107644"))
CHANNEL_USERNAME = os.environ.get("@joooffy")
DATA_FILE = "data.json"
WORK_DIR = "files"

os.makedirs(WORK_DIR, exist_ok=True)

# ===== DATA =====
def load():
    if not os.path.exists(DATA_FILE):
        return {"authorized": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

# ===== CHANNEL CHECK =====
async def is_joined(bot, uid):
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ("member", "administrator", "creator")
    except:
        return False

# ===== KEYBOARDS =====
JOIN_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton(
        "👉 Join Channel",
        url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
    )],
    [InlineKeyboardButton("✅ I Have Joined", callback_data="check_join")]
])

ADMIN_MENU = ReplyKeyboardMarkup(
    [["✅ Authorize User"], ["❌ Remove User"], ["📋 Authorized List"]],
    resize_keyboard=True
)

USER_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("🖼 Photo ➜ PDF", callback_data="photo_pdf")],
    [InlineKeyboardButton("📄 PDF ➜ ZIP", callback_data="pdf_zip")]
])

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load()

    if not await is_joined(context.bot, user.id):
        await update.message.reply_text(
            "⚠️ Join channel first",
            reply_markup=JOIN_KB
        )
        return

    username = f"@{user.username}" if user.username else "No Username"
    box = (
        "┌── USER INFO ──┐\n"
        f"│ Username: {username}\n"
        f"│ UID: {user.id}\n"
        "└──────────────┘"
    )

    if user.id == ADMIN_ID:
        await update.message.reply_text(box)
        await update.message.reply_text("👑 ADMIN PANEL", reply_markup=ADMIN_MENU)
        return

    if user.id in data["authorized"]:
        await update.message.reply_text(
            "✅ Authorized\n\n" + box,
            reply_markup=USER_KB
        )
    else:
        await update.message.reply_text(
            "❌ Not authorized\nWait for admin\n\n" + box
        )

# ===== JOIN CHECK =====
async def join_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_joined(context.bot, q.from_user.id):
        await q.message.reply_text("✅ Joined, send /start")
    else:
        await q.message.reply_text("❌ Still not joined")

# ===== USER BUTTON =====
async def user_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = q.data
    if q.data == "photo_pdf":
        await q.message.reply_text("🖼 Send photo")
    else:
        await q.message.reply_text("📄 Send PDF")

# ===== PHOTO ➜ PDF =====
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "photo_pdf":
        return
    photo = update.message.photo[-1]
    file = await photo.get_file()
    img = Image.open(BytesIO(await file.download_as_bytearray())).convert("RGB")
    path = os.path.join(WORK_DIR, "photo.pdf")
    img.save(path, "PDF")
    await update.message.reply_document(open(path, "rb"))
    context.user_data["mode"] = None

# ===== PDF ➜ ZIP =====
async def doc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "pdf_zip":
        return
    doc = update.message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("Send PDF only")
        return
    file = await doc.get_file()
    pdf_path = os.path.join(WORK_DIR, doc.file_name)
    await file.download_to_drive(pdf_path)
    zip_path = pdf_path.replace(".pdf", ".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pdf_path, arcname=doc.file_name)
    await update.message.reply_document(open(zip_path, "rb"))
    context.user_data["mode"] = None

# ===== ADMIN PANEL =====
async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    data = load()
    txt = update.message.text

    if txt == "✅ Authorize User":
        context.user_data["auth"] = True
        await update.message.reply_text("Send UID")
    elif context.user_data.get("auth"):
        uid = int(txt)
        if uid not in data["authorized"]:
            data["authorized"].append(uid)
            save(data)
            await context.bot.send_message(uid, "🎉 You are authorized")
        context.user_data["auth"] = False
        await update.message.reply_text("Done")

# ===== RUN =====
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(join_check, pattern="check_join"))
app.add_handler(CallbackQueryHandler(user_button))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app.add_handler(MessageHandler(filters.Document.ALL, doc_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))

app.run_polling()
