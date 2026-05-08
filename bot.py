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

# .env faylidan kalitlarni yuklash
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Gemini-ni sozlash
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- GEMINI MATN YARATISH ---
async def get_gemini_text(topic):
    prompt = (
        f"Mavzu: '{topic}'. Professional 5 slayidli taqdimot rejasi tuz. "
        "Har bir slayd uchun quyidagi formatda javob ber:\n"
        "Slayd sarlavhasi | Slayd matni (3 ta asosiy nuqta) | Rasm uchun inglizcha qisqa kalit so'z\n"
        "Faqat shu formatda bo'lsin, ortiqcha gap yozma."
    )
    try:
        # Generatsiya qilish
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini xatosi: {e}")
        return None

# --- AI RASM YARATISH ---
def get_ai_image(keyword):
    url = f"https://image.pollinations.ai/prompt/professional%20presentation%20slide%20{keyword.replace(' ', '%20')}?width=1024&height=768&nologo=true"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code == 200:
            return io.BytesIO(res.content)
    except:
        return None

# --- TAQDIMOTNI YIG'ISH (PPTX) ---
def create_pptx(topic, ai_content, filename):
    prs = Presentation()
    
    # 1. Titul slaydi
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = topic.upper()
    slide.placeholders[1].text = "Gemini AI tomonidan tayyorlandi\nTelegram Bot: @SizningBot"

    # Gemini matnini qatorlarga bo'lish
    lines = [l for l in ai_content.split('\n') if "|" in l]
    
    for line in lines[:5]:
        try:
            parts = line.split("|")
            # Indexerror dan himoya
            title = parts[0].strip() if len(parts) > 0 else "Ma'lumot"
            text = parts[1].strip() if len(parts) > 1 else ""
            img_key = parts[2].strip() if len(parts) > 2 else title

            # Yangi slayd
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = title
            slide.placeholders[1].text = text
            
            # Rasmni slayidga qo'shish
            img_data = get_ai_image(img_key)
            if img_data:
                # O'ng tomonga joylashtirish
                slide.shapes.add_picture(img_data, Inches(5.5), Inches(1.5), width=Inches(4))
        except Exception as e:
            logging.error(f"Slayd xatosi: {e}")
            continue
            
    prs.save(filename)

# --- BOT FUNKSIYALARI ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(f"Salom {message.from_user.first_name}! 👋\nMen **Gemini AI** yordamida professional taqdimotlar yarataman.\n\nMavzuni yuboring:")

@dp.message(F.text)
async def topic_handler(message: types.Message):
    topic = message.text
    msg = await message.answer("🧠 Gemini o'ylamoqda...")
    
    # Gemini-dan matn olish
    ai_text = await get_gemini_text(topic)
    
    if not ai_text:
        await msg.edit_text("❌ Gemini xatosi yoki API kalitda muammo bor.")
        return

    await msg.edit_text("🖼 Rasmlar chizilmoqda...")
    file_name = f"pres_{message.from_user.id}.pptx"
    
    try:
        create_pptx(topic, ai_text, file_name)
        
        # Faylni yuborish
        document = FSInputFile(file_name)
        await message.answer_document(document, caption=f"✅ '{topic}' mavzusida taqdimot tayyor!")
    except Exception as e:
        await message.answer(f"⚠️ Xatolik: {e}")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)
        await msg.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
