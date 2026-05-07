import os
import asyncio
import requests
import io
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from pptx import Presentation
from pptx.util import Inches

# .env faylini yuklash
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Gemini-ni sozlash
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- GEMINI ORQALI MATN YARATISH ---
async def get_gemini_content(topic):
    prompt = (
        f"Mavzu: '{topic}'. Ushbu mavzuda 5 ta slayddan iborat taqdimot rejasi tuzing. "
        "Har bir slayd uchun quyidagi formatda javob bering:\n"
        "Slayd nomi | Slayd matni (3 ta nuqta bilan) | Rasm uchun inglizcha qisqa kalit so'z\n"
        "Faqat shu formatda bo'lsin, ortiqcha gap yozmang."
    )
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini xatosi: {e}")
        return None

# --- RASM YUKLASH (Pollinations hali ham rasmlar uchun eng yaxshisi) ---
def download_image(keyword):
    url = f"https://image.pollinations.ai/prompt/professional%20presentation%20slide%20{keyword.replace(' ', '%20')}?width=1024&height=768&nologo=true"
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except:
        return None

# --- PPTX YARATISH ---
def create_presentation(topic, ai_text, filename):
    prs = Presentation()
    
    # 1. Titul slayd
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = topic.upper()
    slide.placeholders[1].text = "Gemini AI tomonidan tayyorlandi"

    # Gemini javobini tahlil qilish
    lines = [l for l in ai_text.split('\n') if "|" in l]
    
    for line in lines[:5]: # Maksimal 5 slayd
        try:
            parts = line.split("|")
            title_text = parts[0].strip()
            content_text = parts[1].strip()
            img_keyword = parts[2].strip() if len(parts) > 2 else title_text

            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = title_text
            slide.placeholders[1].text = content_text
            
            # Rasm qo'shish
            img_data = download_image(img_keyword)
            if img_data:
                slide.shapes.add_picture(img_data, Inches(5.5), Inches(1.5), width=Inches(4))
        except:
            continue

    prs.save(filename)

# --- BOT HANDLERLARI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Salom {message.from_user.first_name}! 👋\nMen **Gemini AI** yordamida rasmli taqdimotlar yarataman.\nMavzuni yuboring:")

@dp.message(F.text)
async def handle_topic(message: types.Message):
    topic = message.text
    status = await message.answer("🧠 Gemini o'ylamoqda...")
    
    # Gemini dan matn olish
    ai_text = await get_gemini_content(topic)
    if not ai_text:
        await status.edit_text("❌ Gemini bilan bog'lanishda xato bo'ldi.")
        return

    await status.edit_text("🖼 Rasmlar joylanmoqda...")
    file_path = f"pres_{message.from_user.id}.pptx"
    
    try:
        create_presentation(topic, ai_text, file_path)
        document = FSInputFile(file_path)
        await message.answer_document(document, caption=f"✅ '{topic}' mavzusida Gemini tomonidan yaratildi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        await status.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
