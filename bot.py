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
from pptx.util import Inches, Pt

# .env faylini yuklash
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Loglarni sozlash (xatolarni ko'rib turish uchun)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- AI BILAN ISHLASH ---

def get_ai_content(topic):
    """Mavzu bo'yicha matn olish. Formatni qat'iy so'raymiz."""
    prompt = (
        f"Create a 5-slide presentation outline about '{topic}' in Uzbek language. "
        "Format each slide exactly like this: "
        "Slide: Title of slide | Main content points | Image keyword "
        "Do not write any other text."
    )
    url = f"https://text.pollinations.ai/{prompt}"
    try:
        response = requests.get(url, timeout=30)
        return response.text
    except Exception as e:
        logging.error(f"Matn olishda xato: {e}")
        return None

def download_image(keyword):
    """AI orqali rasm yaratish va uni yuklab olish."""
    url = f"https://image.pollinations.ai/prompt/professional%20{keyword.replace(' ', '%20')}?width=1024&height=768&nologo=true"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except Exception as e:
        logging.error(f"Rasm yuklashda xato: {e}")
    return None

# --- PPTX YARATISH ---

def create_presentation(topic, ai_text, filename):
    prs = Presentation()
    
    # 1. Titul slayd
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = topic.upper()
    slide.placeholders[1].text = "Avtomatik yaratilgan taqdimot\nAI Assistant Bot"

    # AI javobini qatorlarga bo'lish
    lines = [l for l in ai_text.split('\n') if "|" in l]
    
    if not lines:
        # Agar AI noto'g'ri format bersa, oddiyroq bo'lishga harakat qilamiz
        lines = ai_text.split('\n')[:5]

    for line in lines:
        try:
            parts = line.split("|")
            # Indexerror dan himoya: agar qism yetishmasa, bo'sh qiymat beramiz
            title_text = parts[0].replace("Slide:", "").strip() if len(parts) > 0 else "Ma'lumot"
            content_text = parts[1].strip() if len(parts) > 1 else "Batafsil ma'lumot topilmadi."
            image_keyword = parts[2].strip() if len(parts) > 2 else title_text

            # Slayd yaratish (Sarlavha + Matn)
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = title_text
            
            # Matnni chapga joylash
            body_shape = slide.placeholders[1]
            tf = body_shape.text_frame
            tf.text = content_text
            
            # RASM QO'SHISH
            img_data = download_image(image_keyword)
            if img_data:
                # Slaydning o'ng tomoniga joylash
                slide.shapes.add_picture(img_data, Inches(5.5), Inches(1.5), width=Inches(4))
                
        except Exception as e:
            logging.error(f"Slayd yaratishda xato: {e}")
            continue

    prs.save(filename)

# --- BOT INTERFEYSI ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Salom {message.from_user.full_name}! 👋\n\nMen sizga har qanday mavzuda **rasmli taqdimot** tayyorlab beraman.\nMavzuni yozing:")

@dp.message(F.text)
async def handle_topic(message: types.Message):
    topic = message.text
    status = await message.answer("🔍 Mavzu o'rganilmoqda...")
    
    # AI dan matn olish
    ai_text = get_ai_content(topic)
    if not ai_text:
        await status.edit_text("❌ AI matn yarata olmadi. Qayta urinib ko'ring.")
        return

    await status.edit_text("🎨 Rasmlar chizilmoqda va slaydlar tayyorlanmoqda...")
    
    file_path = f"presentation_{message.from_user.id}.pptx"
    
    try:
        # PPTX faylni yaratish
        create_presentation(topic, ai_text, file_path)
        
        # Faylni yuborish
        await status.edit_text("📤 Fayl yuborilmoqda...")
        document = FSInputFile(file_path)
        await message.answer_document(document, caption=f"✅ {topic} mavzusidagi taqdimot tayyor!")
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        # Faylni o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)
        await status.delete()

async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
