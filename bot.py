import os
import asyncio
import requests
import io
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from pptx import Presentation
from pptx.util import Inches

# .env faylini yuklash
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def download_image(prompt):
    image_url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=768&nologo=true"
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except Exception:
        return None

def get_ai_content(topic):
    prompt = f"Create a short outline for a 5-slide presentation about '{topic}'. Structure: Slide X | Title | 3 points. Language: Uzbek."
    url = f"https://text.pollinations.ai/{prompt}"
    try:
        response = requests.get(url)
        return response.text
    except:
        return None

def create_presentation(topic, ai_text, filename):
    prs = Presentation()
    
    # Titul slayd
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = topic
    slide.placeholders[1].text = "AI Presentation Creator Bot\nTayyorladi: @SizningBot"

    lines = [l for l in ai_text.split('\n') if "|" in l]
    
    for line in lines[:5]:
        parts = line.split("|")
        title_text = parts[1].strip()
        content_text = parts[2].strip()

        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = title_text
        slide.placeholders[1].text = content_text
        
        # Rasm qo'shish
        img_data = download_image(f"professional slide image for {title_text}")
        if img_data:
            slide.shapes.add_picture(img_data, Inches(5.5), Inches(1.5), width=Inches(4))

    prs.save(filename)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Taqdimot mavzusini yuboring (masalan: Quyosh tizimi)")

@dp.message(F.text)
async def handle_request(message: types.Message):
    topic = message.text
    wait_msg = await message.answer("🛠 Taqdimot tayyorlanmoqda (rasmlar bilan)...")
    
    file_path = f"pres_{message.from_user.id}.pptx"
    ai_text = get_ai_content(topic)
    
    if ai_text:
        create_presentation(topic, ai_text, file_path)
        doc = FSInputFile(file_path)
        await message.answer_document(doc, caption="✅ Marhamat, sizning taqdimotingiz!")
        if os.path.exists(file_path):
            os.remove(file_path)
    else:
        await message.answer("❌ Matn yaratishda xatolik bo'ldi.")
    
    await wait_msg.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
