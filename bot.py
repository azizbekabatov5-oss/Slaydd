import instaloader
import re
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

L = instaloader.Instaloader()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Instagram profil URL yuboring.\n\nMisol: https://www.instagram.com/username/"
    )

def extract_username(url: str):
    url = url.strip().rstrip('/')
    match = re.search(r'instagram\.com/([^/?#]+)', url)
    if match:
        username = match.group(1)
        if username not in ['p', 'reel', 'reels', 'stories', 'explore']:
            return username
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    username = extract_username(text)
    if not username:
        await update.message.reply_text(
            "Noto'g'ri URL! Misol: https://www.instagram.com/username/"
        )
        return

    msg = await update.message.reply_text(f"Tekshirilmoqda @{username}...")

    try:
        profile = instaloader.Profile.from_username(L.context, username)
        has_pic = bool(profile.profile_pic_url)
        yoq = "Yoq"
        ism = profile.full_name if profile.full_name else yoq
        bio = profile.biography if profile.biography else yoq

        text_response = (
            f"Profil malumotlari:\n\n"
            f"Username: @{profile.username}\n"
            f"Ism: {ism}\n"
            f"Bio: {bio}\n\n"
            f"Obunachilar: {profile.followers:,}\n"
            f"Obunalar: {profile.followees:,}\n"
            f"Postlar: {profile.mediacount:,}\n\n"
            f"Profil: {'Ochiq' if not profile.is_private else 'Yopiq'}\n"
            f"Tasdiqlangan: {'Ha' if profile.is_verified else yoq}\n"
            f"Profil rasmi: {'Bor' if has_pic else yoq}"
        )

        await msg.delete()

        if has_pic:
            await update.message.reply_photo(
                photo=profile.profile_pic_url,
                caption=text_response
            )
        else:
            await update.message.reply_text(text_response)

    except instaloader.exceptions.ProfileNotExistsException:
        await msg.edit_text("Profil topilmadi.")
    except instaloader.exceptions.ConnectionException:
        await msg.edit_text("Instagram cheklov qoydi. Keyinroq urinib koring.")
    except Exception as e:
        await msg.edit_text(f"Xatolik: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == '__main__':
    main()
