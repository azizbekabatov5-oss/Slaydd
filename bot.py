import os
import asyncio
import requests
import io
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from pptx import Presentation
from pptx.util import Inches

# .env yuklash
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Dinamik import (Agar kutubxona bo'lmasa, xato bermasligi uchun)
HAS_GEMINI = False
try:
    import google.generativeai as genai
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        HAS_GEMINI = True
except Exception as e:
    logging.error(f"Gemini kutubxonasi yoki sozlamasida xato: {e}")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- MOSLASHUVCHAN AI FUNKSIYASI ---
async def get_ai_text(topic):
    prompt = (
        f"Mavzu: '{topic}'. 5 slayidli taqdimot rejasi tuz. "
        "Format: 'Sarlavha | Matn | Rasm kalit so'zi'. Faqat o'zbek tilida."
    )
    
    # 1-yo'l: Gemini (agar kutubxona va key bo'lsa)
    if HAS_GEMINI:
        try:
            response = gemini_model.generate_content(prompt)
            if response and response.text:
                logging.info("Gemini AI orqali matn olindi.")
                return response.text
        except Exception as e:
            logging.error(f"Gemini ishlamadi, zaxiraga o'tilmoqda: {e}")

    # 2-yo'l: Zaxira AI (Hech qanday kutubxona va kalit talab qilmaydi)
    try:
        url = f"https://text.pollinations.ai/{prompt}?model=llama"
        res = requests.get(url, timeout=30)
        if res.status_code == 200:
            logging.info("Fallback (Llama) AI orqali matn olindi.")
            return res.text
    except Exception as e:
        logging.error(f"Zaxira AI ham ishlamadi: {e}")
        return None

# --- RASM FUNKSIYASI ---
def get_ai_image(keyword):
    url = f"https://image.pollinations.ai/prompt/professional%20{keyword.replace(' ', '%20')}?width=1024&height=768&nologo=true"
    try:
        res = requests.get(url, timeout=20)
        return io.BytesIO(res.content) if res.status_code == 200 else None
    except:
        return None

# --- PPTX YARATISH (BARQAROR) ---
def create_pptx(topic, ai_content, filename):
    prs = Presentation()
    # Titul
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = topic.upper()
    slide.placeholders[1].text = "AI Presentation Bot\nRailway Serverda tayyorlandi"

    # Matnni qayta ishlash (har qanday formatga moslashuvchan)
    lines = [l.strip() for l in ai_content.split('\n') if "|" in l or ":" in l]
    if not lines: lines = ai_content.split('\n')[:5]

    for line in lines:
        try:
            # Bo'lish usuli: | yoki : yoki -
            sep = "|" if "|" in line else (":" if ":" in line else "-")
            parts = line.split(sep)
            
            title = parts[0].strip()[:50] # Sarlavha juda uzun bo'lmasligi uchun
            text = parts[1].strip() if len(parts) > 1 else "Batafsil ma'lumot kiritilmagan."
            img_key = parts[2].strip() if len(parts) > 2 else title

            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = title
            slide.placeholders[1].text = text
            
            img_data = get_ai_image(img_key)
            if img_data:
                slide.shapes.add_picture(img_data, Inches(5.4), Inches(1.4), width=Inches(4.2))
        except:
            continue
    prs.save(filename)

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start(m: types.Message):
    mode = "Gemini + Llama" if HAS_GEMINI else "Llama (Universal)"
    await m.answer(f"Salom! Men tayyorman. \nIshlash tartibi: {mode}\nMavzuni yuboring:")

@dp.message(F.text)
async def handle(m: types.Message):
    topic = m.text
    status = await m.answer("⏳ AI ma'lumot to'plamoqda...")
    
    ai_text = await get_ai_text(topic)
    if not ai_text:
        await status.edit_text("❌ AI ulanishda xato. Keyinroq urinib ko'ring.")
        return

    await status.edit_text("🖼 Slaydlar yig'ilmoqda...")
    fname = f"file_{m.from_user.id}.pptx"
    
    try:
        # Loop ichida ishlash uchun create_pptx ni executorga beramiz (ixtiyoriy)
        create_pptx(topic, ai_text, fname)
        await m.answer_document(FSInputFile(fname), caption=f"✅ {topic}")
    except Exception as e:
        await m.answer(f"⚠️ Xatolik: {e}")
    finally:
        if os.path.exists(fname): os.remove(fname)
        await status.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
