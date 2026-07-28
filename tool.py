import logging
import random
import string
import requests
import os
import html
from io import BytesIO
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from gtts import gTTS
from googletrans import Translator
import yt_dlp

# Logging Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Translator Instance
translator = Translator()

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8536829402:AAHMSVB7t1uZ91reDgvvzxXhkUGgJ9MmN9w")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 6535070545))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL") # Render নিজেই এই ইউআরএল প্রদান করবে
PORT = int(os.environ.get("PORT", 10000))
# =======================================================

# Database (In-Memory)
USER_LIST = set()
FORCE_CHANNELS = []
OTHER_BOTS_TEXT = "1. @BotOne_Bot\n2. @BotTwo_Bot"

# States for ConversationHandler
(
    WAITING_FOR_TTS,
    WAITING_FOR_TRANSLATE,
    WAITING_FOR_STYLISH,
    WAITING_FOR_MORSE,
    WAITING_FOR_DOWNLOAD,
    WAITING_FOR_AI_IMAGE,
    WAITING_FOR_PASSWORD,
    WAITING_FOR_BROADCAST,
    WAITING_FOR_ADD_CHANNEL,
    WAITING_FOR_EDIT_BOTS
) = range(10)

MORSE_CODE_DICT = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..', '1': '.----', '2': '..---', '3': '...--',
    '4': '....-', '5': '.....', '6': '-....', '7': '--...', '8': '---..',
    '9': '----.', '0': '-----', ' ': '/'
}

def text_to_morse(text):
    return ' '.join(MORSE_CODE_DICT.get(char.upper(), char) for char in text)

def generate_stylish_text(text):
    normal_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    fonts = {
        "script": "𝒜ℬ𝒞𝒟ℰ𝐹𝒢ℋℐ𝒥𝒦ℒℳ𝒩𝒪𝒫𝒬ℛ𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵𝒶𝒷𝒸𝒹ℯ𝒻𝒊𝒽𝒾𝒿𝓀𝓁𝓂𝓃ℴ𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝒵0123456789",
        "italic": "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘙𝘠𝘘𝘙𝘈𝘛𝘜𝘝𝘞𝘌𝘎𝘞𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻0123456789",
        "bold": "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗",
    }
    def convert(t, f_key):
        target = fonts.get(f_key, fonts["bold"])
        mapping = {normal_chars[i]: target[i] for i in range(len(normal_chars)) if i < len(target)}
        return "".join(mapping.get(c, c) for c in t)

    t_script = convert(text, "script")
    t_bold = convert(text, "bold")
    
    styles = [
        f"➊ 𝒞𝓊𝓇𝓈𝒾𝓋ℯ:\n➺ {t_script}",
        f"➋ 𝐁𝐨𝐥𝐝:\n➺ {t_bold}",
        f"➌ 𝒮𝓉𝒶𝓇:\n✦•┈๑ {text} ๑┈•✦"
    ]
    return "\n\n".join(styles)

def format_card(title, content):
    return (
        f"❖━━━━━━━━━━━━━━━━━━━━❖\n"
        f"   ✦  <b>{html.escape(title)}</b>  ✦\n"
        f"❖━━━━━━━━━━━━━━━━━━━━❖\n\n"
        f"{content}\n\n"
        f"❖━━━━━━━━━━━━━━━━━━━━❖\n"
        f"👨‍💻 Developed By: <b>@itsAdminRimon</b>\n"
        f"❖━━━━━━━━━━━━━━━━━━━━❖"
    )

async def check_force_join(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    if user_id == ADMIN_ID or not FORCE_CHANNELS:
        return True, []
    unjoined = []
    for ch in FORCE_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ['left', 'kicked']:
                unjoined.append(ch)
        except Exception:
            continue
    return len(unjoined) == 0, unjoined

def get_main_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("🗣 Text to Voice", callback_data="btn_tts"), InlineKeyboardButton("🌐 Translator", callback_data="btn_translate")],
        [InlineKeyboardButton("✨ Stylish Font", callback_data="btn_stylish"), InlineKeyboardButton("📡 Morse Code", callback_data="btn_morse")],
        [InlineKeyboardButton("📥 Social Downloader", callback_data="btn_download")],
        [InlineKeyboardButton("🎨 AI Image Gen", callback_data="btn_ai_image"), InlineKeyboardButton("🔐 Pass Generator", callback_data="btn_password")],
        [InlineKeyboardButton("🤖 Our Other Bots", callback_data="btn_other_bots")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="btn_admin")])
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="btn_back")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    USER_LIST.add(user.id)
    is_joined, unjoined = await check_force_join(user.id, context)
    if not is_joined:
        buttons = [[InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@', '')}")] for ch in unjoined]
        buttons.append([InlineKeyboardButton("🔄 Check Join", callback_data="btn_check_join")])
        text = format_card("FORCE JOIN REQUIRED", "⚠️ বটের সকল ফিচার ব্যবহার করতে নিচের চ্যানেলে জয়েন করুন:")
        if update.message:
            await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        return ConversationHandler.END

    is_admin = (user.id == ADMIN_ID)
    content = f"👤 <b>NAME:</b> {html.escape(user.first_name)}\n🆔 <b>ID:</b> <code>{user.id}</code>\n\n🚀 <b>SELECT A CATEGORY:</b>"
    text = format_card("SH ToolBazar", content)
    if update.message:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=get_main_keyboard(is_admin))
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=get_main_keyboard(is_admin))
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()
    data = query.data

    if data == "btn_check_join":
        is_joined, _ = await check_force_join(user.id, context)
        if is_joined:
            return await start(update, context)
        else:
            await query.answer("❌ আপনি এখনও সব চ্যানেলে জয়েন করেননি!", show_alert=True)
            return ConversationHandler.END

    if data == "btn_back":
        return await start(update, context)
    elif data == "btn_other_bots":
        text = format_card("OUR OTHER BOTS", f"✨ <b>Our Other Utility Bots:</b>\n\n{OTHER_BOTS_TEXT}")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return ConversationHandler.END
    elif data == "btn_tts":
        await query.edit_message_text(format_card("TEXT TO VOICE", "আপনার কাঙ্ক্ষিত লেখাটি পাঠান:"), parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_TTS
    elif data == "btn_translate":
        await query.edit_message_text(format_card("TRANSLATOR", "যেকোনো ভাষার টেক্সট পাঠান:"), parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_TRANSLATE
    elif data == "btn_stylish":
        await query.edit_message_text(format_card("STYLISH FONT", "আপনার নামটি বা লেখাটি ইংলিশে লিখুন:"), parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_STYLISH
    elif data == "btn_download":
        await query.edit_message_text(format_card("SOCIAL DOWNLOADER", "ভিডিওর লিংক দিন:"), parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_DOWNLOAD
    elif data == "btn_ai_image":
        await query.edit_message_text(format_card("AI IMAGE GEN", "প্রম্পট লিখুন:"), parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_AI_IMAGE
    elif data == "btn_password":
        await query.edit_message_text(format_card("PASSWORD GENERATOR", "কিছু শব্দ লিখে পাঠান:"), parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_PASSWORD

async def process_tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tts = gTTS(text=update.message.text, lang='bn')
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    await update.message.reply_voice(voice=fp, caption="🔊 আপনার ভয়েস প্রস্তুত!")
    return ConversationHandler.END

async def process_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    translated = translator.translate(update.message.text, dest='bn')
    res = f"<b>মূল:</b> {html.escape(update.message.text)}\n\n<b>অনুবাদ:</b>\n{html.escape(translated.text)}"
    await update.message.reply_text(format_card("TRANSLATION", res), parse_mode='HTML', reply_markup=get_back_keyboard())
    return ConversationHandler.END

async def process_stylish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    styled = generate_stylish_text(update.message.text)
    await update.message.reply_text(format_card("STYLISH FONTS", styled), parse_mode='HTML', reply_markup=get_back_keyboard())
    return ConversationHandler.END

async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    msg = await update.message.reply_text("🔄 Processing video...")
    try:
        ydl_opts = {'format': 'best[ext=mp4]/best', 'outtmpl': 'downloads/%(id)s.%(ext)s', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        with open(file_path, 'rb') as f:
            await update.message.reply_video(video=f, caption="✅ Success!")
        os.remove(file_path)
        await msg.delete()
    except Exception:
        await msg.edit_text("❌ ডাউনলোড ব্যর্থ হয়েছে।", reply_markup=get_back_keyboard())
    return ConversationHandler.END

async def process_ai_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = requests.utils.quote(update.message.text)
    img_url = f"https://image.pollinations.ai/prompt/{prompt}"
    await update.message.reply_photo(photo=img_url, caption="🎨 AI Generated Image")
    return ConversationHandler.END

async def process_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chars = update.message.text + string.digits + string.ascii_letters
    p1 = ''.join(random.sample(chars, min(len(chars), 14)))
    await update.message.reply_text(format_card("PASSWORD", f"<code>{p1}</code>"), parse_mode='HTML', reply_markup=get_back_keyboard())
    return ConversationHandler.END

# --- Telegram Bot Application & Flask Setup ---
app = Flask(__name__)
telegram_app = None

async def setup_bot():
    global telegram_app
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CallbackQueryHandler(button_handler)],
        states={
            WAITING_FOR_TTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_tts)],
            WAITING_FOR_TRANSLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_translate)],
            WAITING_FOR_STYLISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_stylish)],
            WAITING_FOR_DOWNLOAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_download)],
            WAITING_FOR_AI_IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_ai_image)],
            WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_password)],
        },
        fallbacks=[CommandHandler("start", start), CallbackQueryHandler(button_handler)],
        per_message=False
    )
    telegram_app.add_handler(conv_handler)
    await telegram_app.initialize()
    
    # Webhook সেটআপ করা
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{BOT_TOKEN}"
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = Update.de_json(json_string, telegram_app.bot)
        
        # Async প্রসেস হ্যান্ডেল করার জন্য লুপ চালানো
        import asyncio
        asyncio.run(telegram_app.process_update(update))
        return "OK", 200
    return "Invalid Request", 403

@app.route("/")
def index():
    return "Bot is running on Render Webhook!", 200

if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_bot())
    app.run(host="0.0.0.0", port=PORT)
