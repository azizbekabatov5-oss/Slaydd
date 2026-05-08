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

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- MODELNI AVTOMATIK ANIQLASH ---
WORKING_MODEL = None

def initialize_gemini():
    global WORKING_MODEL
    if not GEMINI_KEY:
        logging.error("GEMINI_API_KEY topilmadi!")
        return

    try:
        genai.configure(api_key=GEMINI_KEY)
        # Mavjud modellarni tekshirish
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        logging.info(f"Mavjud modellar: {available_models}")

        # Ustuvorlik bo'yicha modellar ro'yxati
        priority_list = [
            'models/gemini-1.5-flash', 
            'models/gemini-1.5-pro', 
            'models/gemini-pro',
            'models/gemini-1.0-pro'
        ]

        for model_name in priority_list:
            if model_name in available_models:
                WORKING_MODEL = genai.GenerativeModel(model_name)
                logging.info(f"Tanlangan model: {model_name}")
                break
        
        if not WORKING_MODEL and available_models:
            WORKING_MODEL = genai.GenerativeModel(available_models[0])
            logging.info(f"Zaxira model tanlandi: {available_models[0]}")

    except Exception as e:
        logging.error(f"Gemini init xatosi: {e}")

# Bot ishga tushganda modelni aniqlaymiz
initialize_gemini()

# --- AI MATN FUNKSIYASI ---
async def get_ai_text(topic):
    prompt = (
        f"Mavzu: '{topic}'. 5 ta slayidli taqdimot rejasi tuz. "
        "Format: 'Sarlavha | Matn | Rasm kalit so'zi'. Faqat o'zbek tilida."
    )
    
    # 1. Gemini bilan urinish
    if WORKING_MODEL:
        try:
            response = WORKING_MODEL.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            logging.error(f"Gemini generatsiya xatosi: {e}")

    # 2. Zaxira AI (Agar Gemini modellari topilmasa yoki 404 bersa)
    try:
        url = f"https://text.pollinations.ai/{prompt}?model=llama"
        res = requests.get(url, timeout=20)
        return res.text if res.status_code == 200 else None
    except:
        return None

# --- RASM VA PPTX (O'ZGARISHSIZ QOLADI) ---
def get_image(keyword):
    url = f"https://image.pollinations.ai/prompt/professional%20{keyword.replace(' ', '%20')}?width=1024&height=768&nologo=true"
    try:
        res = requests.get(url, timeout=20)
        return io.BytesIO(res.content) if res.status_code == 200 else None
    except: return None

def create_pptx(topic, ai_content, filename):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = topic.upper()
    slide.placeholders[1].text = "AI Smart Auto-Model Version"

    lines = [l.strip() for l in ai_content.split('\n') if "|" in l]
    if not lines: lines = ai_content.split('\n')[:5]

    for line in lines:
        try:
            parts = line.split("|")
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = parts[0].strip()
            slide.placeholders[1].text = parts[1].strip() if len(parts) > 1 else ""
            
            img_key = parts[2].strip() if len(parts) > 2 else parts[0].strip()
            img_data = get_image(img_key)
            if img_data:
                slide.shapes.add_picture(img_data, Inches(5.5), Inches(1.5), width=Inches(4))
        except: continue
    prs.save(filename)

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start(m: types.Message):
    model_name = WORKING_MODEL.model_name if WORKING_MODEL else "Llama (Backup)"
    await m.answer(f"Salom! Bot ishlamoqda.\nTanlangan AI: {model_name}\nMavzuni yuboring:")

@dp.message(F.text)
async def handle(m: types.Message):
    topic = m.text
    status = await m.answer("⏳ AI tayyorlanmoqda...")
    ai_text = await get_ai_text(topic)
    
    if not ai_text:
        await status.edit_text("❌ Xatolik yuz berdi.")
        return

    fname = f"p_{m.from_user.id}.pptx"
    try:
        create_pptx(topic, ai_text, fname)
        await m.answer_document(FSInputFile(fname), caption=f"✅ {topic}")
    except Exception as e:
        await m.answer(f"⚠️ Xato: {e}")
    finally:
        if os.path.exists(fname): os.remove(fname)
        await status.delete()

async def main():
    # TelegramConflictError oldini olish uchun avvalgi webhook/update larni o'chiramiz
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
