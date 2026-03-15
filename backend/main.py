# backend/main.py
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles  # ← ДОБАВИЛИ ЭТУ СТРОКУ
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

# Загружаем .env (должен быть в корне проекта)
load_dotenv()

app = FastAPI(title="Frendly Map Website")

# === ДОБАВИЛИ ОБСЛУЖИВАНИЕ СТАТИКИ ===
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
frontend_path = os.path.join(project_root, "frontend")

# Подключаем папку frontend как статику по пути /static
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# === ОСТАЛЬНОЙ КОД ===
print(f"📁 Ищем шаблоны в: {frontend_path}")
if not os.path.exists(frontend_path):
    print("❌ Папка frontend не найдена!")
else:
    print("✅ Папка frontend найдена")

templates = Jinja2Templates(directory=frontend_path)

def get_context(request: Request):
    return {
        "request": request,
        "bot_username": os.getenv("TELEGRAM_BOT_USERNAME", "FrendlyMapBot")
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", get_context(request))

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", get_context(request))

@app.get("/achievements", response_class=HTMLResponse)
async def achievements_page(request: Request):
    return templates.TemplateResponse("achievements.html", get_context(request))

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    return templates.TemplateResponse("leaderboard.html", get_context(request))

@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request):
    return templates.TemplateResponse("faq.html", get_context(request))

@app.get("/profile/{user_id}", response_class=HTMLResponse)
async def profile_page(request: Request, user_id: int):
    context = get_context(request)
    context["user_id"] = user_id
    return templates.TemplateResponse("profile.html", context)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)