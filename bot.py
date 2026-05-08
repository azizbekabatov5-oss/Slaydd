import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ========== SOZLASH ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔑 TOKEN - Environment Variable dan olinadi
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN topilmadi! Environment Variable sozlang.")

DATA_FILE = "bot_data.json"

# Conversation holatlari
ADD_NAME, ADD_DAY, ADD_TIME, ADD_ROOM, ADD_TEACHER = range(5)
ADD_EXAM_NAME, ADD_EXAM_DATE, ADD_EXAM_TIME = range(5, 8)

DAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]


# ========== YORDAMCHI FUNKSIYALAR ==========
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_data(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"subjects": [], "exams": [], "reminders": True}
        save_data(data)
    return data[uid]


def update_user_data(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)


def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Bugungi darslar", callback_data="today")],
        [InlineKeyboardButton("📚 Haftalik jadval", callback_data="week")],
        [InlineKeyboardButton("➕ Dars qo'shish", callback_data="add_subject")],
        [InlineKeyboardButton("🗑️ Dars o'chirish", callback_data="del_subject")],
        [InlineKeyboardButton("📖 Imtihonlar", callback_data="exams")],
        [InlineKeyboardButton("🔔 Eslatmalar", callback_data="reminders")],
    ])


# ========== ASOSIY MENYU ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Salom, {user.first_name}!\n\n"
        f"📚 *Talaba yordamchi botiga* xush kelibsiz!\n\n"
        f"Bu bot yordamida:\n"
        f"• 📅 Dars jadvalingizni ko'rish\n"
        f"• ➕ Yangi darslar qo'shish\n"
        f"• 🔔 Dars eslatmalarini olish\n"
        f"• 📖 Imtihon sanalarini kuzatish\n\n"
        f"Quyidagi menyudan tanlang 👇"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


# ========== TUGMALAR HANDLERI (CONVERSATION TASHQARIDA) ==========
async def today_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    today = DAYS[datetime.now().weekday()]
    subjects = [s for s in user_data["subjects"] if s["day"] == today]
    subjects.sort(key=lambda x: x["time"])

    if not subjects:
        text = f"📅 *{today}*\n\n❌ Bugun dars yo'q! 🎉"
    else:
        text = f"📅 *{today}*\n{'═' * 20}\n\n"
        for i, s in enumerate(subjects, 1):
            text += f"🔹 *{i}. {s['name']}*\n🕐 {s['time']} | 🏫 {s['room']} | 👤 {s['teacher']}\n\n"

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def week_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    subjects = user_data["subjects"]

    if not subjects:
        await query.edit_message_text("❌ Hali dars qo'shilmagan!", reply_markup=get_main_keyboard())
        return

    text = "📚 *HAFTALIK JADVAL*\n{'═' * 25}\n\n"
    schedule = {day: [] for day in DAYS}
    for s in subjects:
        schedule[s["day"]].append(s)

    for day in DAYS:
        if schedule[day]:
            schedule[day].sort(key=lambda x: x["time"])
            text += f"*{day}:*\n"
            for s in schedule[day]:
                text += f"  • {s['name']} ({s['time']}, {s['room']})\n"
            text += "\n"

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def del_subject_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)

    if not user_data["subjects"]:
        await query.edit_message_text("❌ O'chirish uchun dars yo'q!", reply_markup=get_main_keyboard())
        return

    keyboard = []
    for i, s in enumerate(user_data["subjects"]):
        text = f"{s['name']} ({s['day']} {s['time']})"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"del_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back")])

    await query.edit_message_text(
        "🗑️ *O'chirish uchun darsni tanlang:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def delete_subject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    idx = int(query.data.split("_")[1])
    user_data = get_user_data(user_id)

    if 0 <= idx < len(user_data["subjects"]):
        deleted = user_data["subjects"].pop(idx)
        update_user_data(user_id, user_data)
        await query.edit_message_text(
            f"✅ *{deleted['name']}* o'chirildi!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(),
        )


async def exams_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    exams = user_data.get("exams", [])

    keyboard = [[InlineKeyboardButton("➕ Imtihon qo'shish", callback_data="add_exam")]]
    if exams:
        keyboard.append([InlineKeyboardButton("🗑️ O'chirish", callback_data="del_exam")])
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back")])

    if not exams:
        text = "📖 *IMTIHONLAR*\n\n❌ Hali imtihon yo'q"
    else:
        text = "📖 *IMTIHONLAR*\n{'═' * 20}\n\n"
        exams.sort(key=lambda x: x["date"])
        for i, e in enumerate(exams, 1):
            exam_date = datetime.strptime(e["date"], "%Y-%m-%d")
            days = (exam_date - datetime.now()).days
            status = "🔴 BUGUN!" if days == 0 else f"{'🟡' if days <= 3 else '🟢'} {days} kun"
            text += f"*{i}. {e['name']}*\n📅 {e['date']} {e.get('time', '')}\n{status}\n\n"

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def reminders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    user_data["reminders"] = not user_data.get("reminders", True)
    update_user_data(user_id, user_data)
    status = "✅ YOQILDI" if user_data["reminders"] else "❌ O'CHIRILDI"
    await query.edit_message_text(
        f"🔔 Eslatmalar {status}",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(),
    )


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Quyidagi menyudan tanlang 👇", reply_markup=get_main_keyboard())


# ========== CONVERSATION: DARS QO'SHISH ==========
async def add_subject_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✏️ *Dars nomini kiriting:*\n(Masalan: Matematika analizi)",
        parse_mode="Markdown",
    )
    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    keyboard = [[InlineKeyboardButton(day, callback_data=f"day_{i}")] for i, day in enumerate(DAYS)]
    await update.message.reply_text(
        "📅 *Hafta kunini tanlang:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADD_DAY


async def add_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    day_idx = int(query.data.split("_")[1])
    context.user_data["day"] = DAYS[day_idx]
    await query.edit_message_text(
        "🕐 *Dars vaqtini kiriting:*\nFormat: `HH:MM` (Masalan: 09:00)",
        parse_mode="Markdown",
    )
    return ADD_TIME


async def add_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_str = update.message.text
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format! Qayta: `HH:MM`", parse_mode="Markdown")
        return ADD_TIME

    context.user_data["time"] = time_str
    await update.message.reply_text("🏫 *Xona raqamini kiriting:*", parse_mode="Markdown")
    return ADD_ROOM


async def add_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["room"] = update.message.text
    await update.message.reply_text("👤 *O'qituvchi F.I.Sh:*", parse_mode="Markdown")
    return ADD_TEACHER


async def add_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)

    new_subject = {
        "name": context.user_data["name"],
        "day": context.user_data["day"],
        "time": context.user_data["time"],
        "room": context.user_data["room"],
        "teacher": update.message.text,
    }

    user_data["subjects"].append(new_subject)
    update_user_data(user_id, user_data)

    await update.message.reply_text(
        f"✅ *Dars qo'shildi!*\n\n📖 {new_subject['name']}\n📅 {new_subject['day']} {new_subject['time']}\n🏫 {new_subject['room']}\n👤 {new_subject['teacher']}",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(),
    )
    return ConversationHandler.END


# ========== CONVERSATION: IMTIHON QO'SHISH ==========
async def add_exam_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📝 *Imtihon nomini kiriting:*",
        parse_mode="Markdown",
    )
    return ADD_EXAM_NAME


async def add_exam_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["exam_name"] = update.message.text
    await update.message.reply_text(
        "📅 *Sana:* `YYYY-MM-DD` formatida\n(Masalan: 2026-06-15)",
        parse_mode="Markdown",
    )
    return ADD_EXAM_DATE


async def add_exam_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = update.message.text
    try:
        exam_date = datetime.strptime(date_str, "%Y-%m-%d")
        if exam_date < datetime.now():
            await update.message.reply_text("❌ O'tgan sana! Qayta kiriting:")
            return ADD_EXAM_DATE
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format! `YYYY-MM-DD`")
        return ADD_EXAM_DATE

    context.user_data["exam_date"] = date_str
    await update.message.reply_text(
        "🕐 *Vaqt:* `HH:MM` yoki `/skip`",
        parse_mode="Markdown",
    )
    return ADD_EXAM_TIME


async def add_exam_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_str = update.message.text
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)

    if time_str != "/skip":
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri! `HH:MM` yoki `/skip`")
            return ADD_EXAM_TIME

    user_data.setdefault("exams", []).append({
        "name": context.user_data["exam_name"],
        "date": context.user_data["exam_date"],
        "time": time_str if time_str != "/skip" else "",
        "room": "",
    })
    update_user_data(user_id, user_data)

    await update.message.reply_text(
        "✅ *Imtihon qo'shildi!*",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(),
    )
    return ConversationHandler.END


# ========== ESLATMALAR ==========
async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    current_day = DAYS[now.weekday()]

    data = load_data()
    for uid, udata in data.items():
        if not udata.get("reminders", True):
            continue
        for subject in udata.get("subjects", []):
            if subject["day"] != current_day:
                continue
            subj_time = datetime.strptime(subject["time"], "%H:%M")
            reminder = (subj_time - timedelta(minutes=15)).strftime("%H:%M")
            if current_time == reminder:
                try:
                    await context.bot.send_message(
                        chat_id=int(uid),
                        text=(
                            f"⏰ *DARS ESIGIZDA!*\n\n"
                            f"📖 {subject['name']}\n"
                            f"🕐 {subject['time']} | 🏫 {subject['room']}\n"
                            f"👤 {subject['teacher']}\n\n"
                            f"Omad! 💪"
                        ),
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.error(f"Eslatma xatosi: {e}")


# ========== ASOSIY ==========
def main():
    application = Application.builder().token(TOKEN).build()

    # 1. Oddiy tugmalar (CONVERSION TASHQARIDA)
    application.add_handler(CallbackQueryHandler(today_callback, pattern="^today$"))
    application.add_handler(CallbackQueryHandler(week_callback, pattern="^week$"))
    application.add_handler(CallbackQueryHandler(del_subject_menu, pattern="^del_subject$"))
    application.add_handler(CallbackQueryHandler(delete_subject_callback, pattern="^del_\\d+$"))
    application.add_handler(CallbackQueryHandler(exams_callback, pattern="^exams$"))
    application.add_handler(CallbackQueryHandler(reminders_callback, pattern="^reminders$"))
    application.add_handler(CallbackQueryHandler(back_callback, pattern="^back$"))

    # 2. Conversation handlerlar (oddiy handlerlardan KEYIN)
    add_subject_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_subject_start, pattern="^add_subject$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_DAY: [CallbackQueryHandler(add_day, pattern="^day_")],
            ADD_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_time)],
            ADD_ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_room)],
            ADD_TEACHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_teacher)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Bekor qilindi!", reply_markup=get_main_keyboard()))],
    )

    add_exam_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_exam_start, pattern="^add_exam$")],
        states={
            ADD_EXAM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_exam_name)],
            ADD_EXAM_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_exam_date)],
            ADD_EXAM_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_exam_time)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Bekor qilindi!", reply_markup=get_main_keyboard()))],
    )

    application.add_handler(add_subject_conv)
    application.add_handler(add_exam_conv)

    # 3. Start komandasi (ENG OXIRIDA)
    application.add_handler(CommandHandler("start", start))

    # 4. Eslatma
    application.job_queue.run_repeating(check_reminders, interval=60, first=10)

    application.run_polling()


if __name__ == "__main__":
    main()
