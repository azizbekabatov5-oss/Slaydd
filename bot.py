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

# LOGGING - Xatolarni kuzatish uchun
logging.basicConfig(level=logging.INFO)

# --- DINAMIK KUTUBXONA TEKSHiruvi ---
HAS_GEMINI = False
try:
    import google.generativeai as genai
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
        # Eng yangi model nomi
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        HAS_GEMINI = True
        logging.info("Gemini kutubxonasi va API kaliti tayyor.")
except Exception as e:
    logging.error(f"Gemini yuklashda xato: {e}")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- AQLLI MATN OLISH (GEMINI -> LLAMA BACKUP) ---
async def get_presentation_content(topic):
    prompt = (
        f"Mavzu: '{topic}'. 5 ta slayidli taqdimot rejasi tuz. "
        "Format: 'Sarlavha | Matn | Rasm kalit so'zi'. "
        "Faqat o'zbek tilida yoz. Har bir slayd yangi qatorda bo'lsin."
    )
    
    # 1. Gemini orqali urinish (agar kalit va kutubxona bo'lsa)
    if HAS_GEMINI:
        try:
            response = gemini_model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            logging.error(f"Gemini 404 yoki API xatosi: {e}. Zaxira AI-ga o'tilmoqda...")

    # 2. ZAXIRA (Fallback) AI - Hech qanday kalit va kutubxona so'ramaydi
    try:
        url = f"https://text.pollinations.ai/{prompt}?model=llama"
        res = requests.get(url, timeout=30)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        logging.error(f"Zaxira AI xatosi: {e}")
        return None

# --- RASM YARATISH (AVTONOM) ---
def get_image(keyword):
    # Rasm topilmasa 404 bermasligi uchun tekshiruv bilan
    url = f"https://image.pollinations.ai/prompt/professional%20{keyword.replace(' ', '%20')}?width=1024&height=768&nologo=true"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code == 200:
            return io.BytesIO(res.content)
    except:
        return None

# --- PPTX YARATISH (XATOLIKDAN HIMOYALANGAN) ---
def create_pptx(topic, ai_content, filename):
    prs = Presentation()
    
    # Titul
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = topic.upper()
    slide.placeholders[1].text = "AI Smart Presentation\nRailway Adaptive Version"

    # AI javobini tahlil qilish (Har qanday formatga moslashadi)
    lines = [l.strip() for l in ai_content.split('\n') if "|" in l or ":" in l]
    if not lines: 
        lines = ai_content.split('\n')[:5] # Format buzilsa ham kamida 5 qatorni oladi

    for line in lines:
        try:
            # Bo'lish belgisi har xil bo'lishi mumkin (| yoki :)
            sep = "|" if "|" in line else ":"
            parts = line.split(sep)
            
            title = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else "Ma'lumotlar yuklanmoqda..."
            img_key = parts[2].strip() if len(parts) > 2 else title

            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = title[:50] # Sarlavha sig'ishi uchun
            slide.placeholders[1].text = content
            
            # Rasm yuklash va qo'shish
            img_data = get_image(img_key)
            if img_data:
                slide.shapes.add_picture(img_data, Inches(5.4), Inches(1.4), width=Inches(4.2))
        except:
            continue
            
    prs.save(filename)

# --- BOT INTERFEYSI ---
@dp.message(Command("start"))
async def start(m: types.Message):
    status = "✅ Gemini+Llama" if HAS_GEMINI else "⚠️ Llama Active (No Key)"
    await m.answer(f"Salom! Men tayyorman.\nRejim: {status}\n\nTaqdimot mavzusini yuboring:")

@dp.message(F.text)
async def handle_topic(message: types.Message):
    topic = message.text
    status_msg = await message.answer("💡 AI ma'lumot to'plamoqda...")
    
    # Aqlli qidiruv
    ai_text = await get_presentation_content(topic)
    
    if not ai_text:
        await status_msg.edit_text("❌ Xatolik: AI serverlari bilan bog'lanib bo'lmadi.")
        return

    await status_msg.edit_text("📂 Taqdimot fayli shakllantirilmoqda...")
    file_path = f"pres_{message.from_user.id}.pptx"
    
    try:
        create_pptx(topic, ai_text, file_path)
        
        doc = FSInputFile(file_path)
        await message.answer_document(doc, caption=f"✅ '{topic}' mavzusida tayyorlandi.")
    except Exception as e:
        await message.answer(f"⚠️ Kutilmagan xato: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        await status_msg.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
