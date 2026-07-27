import logging
import random
import string
import requests
import os
import html
from io import BytesIO

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

# Translator Instance
translator = Translator()

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
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

# Morse Code Dictionary
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

# Fixed & Working Stylish Font Generator
def generate_stylish_text(text):
    normal_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    
    fonts = {
        "script": "𝒜ℬ𝒞𝒟ℰ𝐹𝒢ℋℐ𝒥𝒦ℒℳ𝒩𝒪𝒫𝒬ℛ𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵𝒶𝒷𝒸𝒹ℯ𝒻ℊ𝒽𝒾𝒿𝓀𝓁𝓂𝓃ℴ𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏0123456789",
        "italic": "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘙𝘠𝘘𝘙𝘈𝘛𝘜𝘝𝘞𝘌𝘎𝘞𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻0123456789",
        "gothic": "𝔄𝔅ℭ𝔇𝔈𝔉𝔤ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔑𝔛𝔜ℨ𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷0123456789",
        "bold": "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗",
        "double": "𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"
    }

    def convert(t, f_key):
        target = fonts[f_key]
        mapping = {normal_chars[i]: target[i] for i in range(len(normal_chars)) if i < len(target)}
        return "".join(mapping.get(c, c) for c in t)

    t_script = convert(text, "script")
    t_italic = convert(text, "italic")
    t_gothic = convert(text, "gothic")
    t_bold = convert(text, "bold")
    t_double = convert(text, "double")

    styles = [
        f"➊ 𝒞𝓊𝓇𝓈𝒾𝓋ℯ 𝒮𝓉𝓎𝓁ℯ:\n➺ {t_script}",
        f"➋ 𝘐𝘵𝘢𝘭𝘪𝘤 𝘍𝘰𝘯𝘵:\n➺ {t_italic}",
        f"➌ 𝔊𝔬𝔱𝔥𝔦𝔠 𝔖𝔱𝔶𝔩𝔢:\n➺ {t_gothic}",
        f"➍ 𝐁𝐨𝐥𝐝 𝐒𝐭𝐲𝐥𝐞:\n➺ {t_bold}",
        f"➎ 𝔻𝕠𝕦𝕓𝕝𝕖 𝕊𝕥𝕣𝕦𝕔𝕥𝕦𝕣𝕖:\n➺ {t_double}",
        f"➏ 𝒜𝓇𝓇ℴ𝓌 𝒟ℯ𝒸ℴ𝓇𝒶𝓉𝒾ℴ𝓃:\n➺ ➷➷ {t_italic} ➷➷",
        f"➐ 𝒮𝓉𝒶𝓇 𝒞𝓁𝒶𝓈𝓈𝒾𝒸:\n➺ ✦•┈๑ {text} ๑┈•✦",
        f"➑ 𝒞𝓇ℴ𝓌𝓃 𝒮𝓉𝓎𝓁ℯ:\n➺ 👑 『{t_bold}』 👑"
    ]
    return "\n\n".join(styles)

# UI Formatter using HTML
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

# Force Join Checker
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

# Main Keyboard
def get_main_keyboard(is_admin=False):
    keyboard = [
        [
            InlineKeyboardButton("🗣 Text to Voice", callback_data="btn_tts"),
            InlineKeyboardButton("🌐 Translator", callback_data="btn_translate")
        ],
        [
            InlineKeyboardButton("✨ Stylish Font", callback_data="btn_stylish"),
            InlineKeyboardButton("📡 Morse Code", callback_data="btn_morse")
        ],
        [
            InlineKeyboardButton("📥 Social Downloader", callback_data="btn_download")
        ],
        [
            InlineKeyboardButton("🎨 AI Image Gen", callback_data="btn_ai_image"),
            InlineKeyboardButton("🔐 Pass Generator", callback_data="btn_password")
        ],
        [
            InlineKeyboardButton("🤖 Our Other Bots", callback_data="btn_other_bots")
        ]
    ]
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="btn_admin")])
        
    return InlineKeyboardMarkup(keyboard)

# Back Button
def get_back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="btn_back")]])

# /start Command Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    USER_LIST.add(user.id)
    
    is_joined, unjoined = await check_force_join(user.id, context)
    if not is_joined:
        buttons = []
        for ch in unjoined:
            ch_clean = ch.replace("@", "")
            buttons.append([InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch_clean}")])
        buttons.append([InlineKeyboardButton("🔄 Check Join", callback_data="btn_check_join")])
        
        text = format_card("FORCE JOIN REQUIRED", "⚠️ বটের সকল ফিচার ব্যবহার করতে নিচের চ্যানেলে জয়েন করুন:")
        if update.message:
            await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        return ConversationHandler.END

    is_admin = (user.id == ADMIN_ID)
    content = (
        f"👤 <b>NAME:</b> {html.escape(user.first_name)}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n\n"
        f"🚀 <b>SELECT A CATEGORY TO EXPLORE:</b>"
    )
    text = format_card("SH ToolBazar", content)
    
    if update.message:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=get_main_keyboard(is_admin))
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=get_main_keyboard(is_admin))
    
    return ConversationHandler.END

# Callback Query Router
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

    # Admin Panel Commands
    elif data == "btn_admin" and user.id == ADMIN_ID:
        admin_text = (
            f"📊 <b>Total Users:</b> <code>{len(USER_LIST)}</code>\n"
            f"📢 <b>Force Channels:</b> <code>{len(FORCE_CHANNELS)}</code>\n\n"
            f"নিচের বাটনগুলো ব্যবহার করে বোটে নিয়ন্ত্রণ করুন:"
        )
        admin_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Add Channel", callback_data="btn_add_ch"),
                InlineKeyboardButton("➖ Remove Channel", callback_data="btn_rem_ch")
            ],
            [
                InlineKeyboardButton("📋 View Channels", callback_data="btn_view_ch"),
                InlineKeyboardButton("✏️ Edit Extra Bots", callback_data="btn_edit_bots")
            ],
            [
                InlineKeyboardButton("📢 Broadcast Message", callback_data="btn_broadcast")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="btn_back")
            ]
        ])
        await query.edit_message_text(format_card("ADMIN CONTROL", admin_text), parse_mode='HTML', reply_markup=admin_keyboard)
        return ConversationHandler.END

    elif data == "btn_view_ch" and user.id == ADMIN_ID:
        ch_list = "\n".join([f"• <code>{c}</code>" for c in FORCE_CHANNELS]) if FORCE_CHANNELS else "কোনো চ্যানেল যুক্ত নেই।"
        text = format_card("ACTIVE CHANNELS", f"📢 <b>Force Join Channels:</b>\n\n{ch_list}")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return ConversationHandler.END

    elif data == "btn_rem_ch" and user.id == ADMIN_ID:
        if not FORCE_CHANNELS:
            text = format_card("REMOVE CHANNEL", "❌ রিমুভ করার মতো কোনো চ্যানেল পাওয়া যায়নি।")
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        else:
            buttons = []
            for ch in FORCE_CHANNELS:
                buttons.append([InlineKeyboardButton(f"❌ Remove {ch}", callback_data=f"del_ch_{ch}")])
            buttons.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="btn_back")])
            text = format_card("REMOVE CHANNEL", "যে চ্যানেলটি রিমুভ করতে চান তার উপর ক্লিক করুন:")
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        return ConversationHandler.END

    elif data.startswith("del_ch_") and user.id == ADMIN_ID:
        ch_to_del = data.replace("del_ch_", "")
        if ch_to_del in FORCE_CHANNELS:
            FORCE_CHANNELS.remove(ch_to_del)
            await query.answer(f"✅ {ch_to_del} রিমুভ করা হয়েছে!", show_alert=True)
        return await start(update, context)

    elif data == "btn_add_ch" and user.id == ADMIN_ID:
        text = format_card("ADD CHANNEL", "যেই চ্যানেলটি যুক্ত করতে চান সেটার ইউজারনেম পাঠান (e.g. <code>@MyChannel</code>):")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_ADD_CHANNEL

    elif data == "btn_edit_bots" and user.id == ADMIN_ID:
        text = format_card("EDIT EXTRA BOTS", "আপনার অন্যান্য বটের ইউজারনেম বা লিংক লিখে পাঠান (যেমন: @SH_BOMBING_bot):")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_EDIT_BOTS

    elif data == "btn_broadcast" and user.id == ADMIN_ID:
        text = format_card("BROADCAST", "সব ইউজারের কাছে যে মেসেজটি পাঠাতে চান তা লিখে পাঠান:")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_BROADCAST

    # User Features
    elif data == "btn_tts":
        text = format_card("TEXT TO VOICE", "আপনার কাঙ্ক্ষিত লেখাটি পাঠান, আমি ভয়েস মেসেজ বানিয়ে দিচ্ছি।")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_TTS

    elif data == "btn_translate":
        text = format_card("TRANSLATOR", "যেকোনো ভাষার টেক্সট পাঠান, এটি বাংলায় অনুবাদ হয়ে যাবে।")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_TRANSLATE

    elif data == "btn_stylish":
        text = format_card("STYLISH FONT", "আপনার নামটি বা লেখাটি ইংলিশে লিখুন (যেমন: Rimon)। বিভিন্ন স্টাইলে সাজিয়ে দেওয়া হবে।")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_STYLISH

    elif data == "btn_morse":
        text = format_card("MORSE CODE", "যেকোনো লেখা পাঠালে সেটা Morse Code-এ রূপান্তর করে দেওয়া হবে।")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_MORSE

    elif data == "btn_download":
        text = format_card("SOCIAL DOWNLOADER", "TikTok, Shorts, Instagram or Facebook ভিডিওর লিংক দিন।")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_DOWNLOAD

    elif data == "btn_ai_image":
        text = format_card("AI IMAGE GEN", "ছবি তৈরি করতে Prompt লিখুন অথবা ছবির ডাউনলোড লিংক দিন।")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_AI_IMAGE

    elif data == "btn_password":
        text = format_card("PASSWORD GENERATOR", "পাসওয়ার্ড তৈরির জন্য কিছু এলোমেলো শব্দ লিখে পাঠান।")
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
        return WAITING_FOR_PASSWORD

# --- Process Admin Actions ---
async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    ch_name = update.message.text.strip()
    if not ch_name.startswith("@"):
        ch_name = "@" + ch_name
    
    if ch_name not in FORCE_CHANNELS:
        FORCE_CHANNELS.append(ch_name)
        text = format_card("ADD CHANNEL", f"✅ চ্যানেল <code>{html.escape(ch_name)}</code> সফলভাবে এড হয়েছে!")
    else:
        text = format_card("ADD CHANNEL", "⚠️ এই চ্যানেলটি আগে থেকেই যুক্ত আছে।")
        
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
    return ConversationHandler.END

async def process_edit_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    global OTHER_BOTS_TEXT
    OTHER_BOTS_TEXT = html.escape(update.message.text.strip())
    text = format_card("EDIT EXTRA BOTS", "✅ Extra Bots তথ্য সফলভাবে সেভ হয়েছে! 'Our Other Bots' বাটন থেকে চেক করুন।")
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=get_back_keyboard())
    return ConversationHandler.END

async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
        
    broadcast_msg = html.escape(update.message.text)
    count = 0
    for uid in USER_LIST:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 <b>Announcement:</b>\n\n{broadcast_msg}", parse_mode='HTML')
            count += 1
        except Exception:
            pass
            
    await update.message.reply_text(format_card("BROADCAST DONE", f"✅ সফলভাবে <code>{count}</code> জন ইউজারের কাছে মেসেজ পাঠানো হয়েছে!"), parse_mode='HTML', reply_markup=get_back_keyboard())
    return ConversationHandler.END

# --- Process User Actions ---
async def process_tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_input = update.message.text
    tts = gTTS(text=text_input, lang='bn' if any(ord(c) > 127 for c in text_input) else 'en')
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    await update.message.reply_voice(voice=fp, caption="🔊 আপনার ভয়েস প্রস্তুত!")
    return ConversationHandler.END

async def process_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    translated = translator.translate(update.message.text, dest='bn')
    res = f"<b>মূল লেখা:</b> {html.escape(update.message.text)}\n\n<b>বাংলা অনুবাদ:</b>\n{html.escape(translated.text)}"
    await update.message.reply_text(format_card("TRANSLATION RESULT", res), parse_mode='HTML', reply_markup=get_back_keyboard())
    return ConversationHandler.END

async def process_stylish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    styled = generate_stylish_text(update.message.text)
    await update.message.reply_text(format_card("STYLISH FONTS", styled), parse_mode='HTML', reply_markup=get_back_keyboard())
    return ConversationHandler.END

async def process_morse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    morse = text_to_morse(update.message.text)
    res = f"<code>{morse}</code>"
    await update.message.reply_text(format_card("MORSE CODE RESULT", res), parse_mode='HTML', reply_markup=get_back_keyboard())
    return ConversationHandler.END

# Auto Auto-Cleaning Downloader
async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    msg = await update.message.reply_text("🔄 Processing video URL...")
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    
    file_path = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
        await msg.edit_text("📤 Uploading video to Telegram...")
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption="✅ Video Downloaded Successfully!")
        await msg.delete()

    except Exception:
        try:
            dl_api = f"https://api.vkrdown.com/v2/download?url={url}"
            res = requests.get(dl_api, timeout=10).json()
            video_url = res.get("data", {}).get("url") or res.get("data", {}).get("video")
            if video_url:
                await msg.delete()
                await update.message.reply_video(video=video_url, caption="✅ Video Downloaded Successfully!")
                return ConversationHandler.END
        except Exception:
            pass

        await msg.edit_text(format_card("DOWNLOAD FAILED", "❌ ভিডিওটি ডাউনলোড করতে ব্যর্থ হয়েছে। লিংকটি সঠিক ও পাবলিক কিনা তা নিশ্চিত করুন।"), parse_mode='HTML', reply_markup=get_back_keyboard())

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

    return ConversationHandler.END

async def process_ai_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    if user_input.startswith("http://") or user_input.startswith("https://"):
        await update.message.reply_photo(photo=user_input, caption="🖼 ছবির লিংক থেকে ছবি ডাউনলোড সফল!")
    else:
        prompt = requests.utils.quote(user_input)
        img_url = f"https://image.pollinations.ai/prompt/{prompt}"
        await update.message.reply_photo(photo=img_url, caption=f"🎨 AI Generated Image for:\n<b>{html.escape(user_input)}</b>", parse_mode='HTML')
    return ConversationHandler.END

async def process_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    specials = "!@#$%^&*()_+-=[]{}"
    chars = user_input + specials + string.digits + string.ascii_letters
    
    p1 = ''.join(random.sample(chars, min(len(chars), 14)))
    p2 = ''.join(random.sample(chars, min(len(chars), 16)))
    p3 = ''.join(random.sample(chars, min(len(chars), 18)))
    
    res = (
        f"🔑 <b>Option 1:</b> <code>{p1}</code>\n"
        f"🔑 <b>Option 2:</b> <code>{p2}</code>\n"
        f"🔑 <b>Option 3:</b> <code>{p3}</code>"
    )
    await update.message.reply_text(format_card("STRONG PASSWORDS", res), parse_mode='HTML', reply_markup=get_back_keyboard())
    return ConversationHandler.END

# Main Function
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(button_handler)
        ],
        states={
            WAITING_FOR_TTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_tts)],
            WAITING_FOR_TRANSLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_translate)],
            WAITING_FOR_STYLISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_stylish)],
            WAITING_FOR_MORSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_morse)],
            WAITING_FOR_DOWNLOAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_download)],
            WAITING_FOR_AI_IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_ai_image)],
            WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_password)],
            WAITING_FOR_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_broadcast)],
            WAITING_FOR_ADD_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_channel)],
            WAITING_FOR_EDIT_BOTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_bots)],
        },
        fallbacks=[CommandHandler("start", start), CallbackQueryHandler(button_handler)],
        per_message=False
    )

    app.add_handler(conv_handler)

    print("SH ToolBazar Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
