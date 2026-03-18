import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api.achievements import router as achievements_router
from .api.auth import router as auth_router
from .api.users import router as users_router
from .database import engine
from .models import Base

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Friendly Map Website", lifespan=lifespan)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
    return response


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
frontend_path = os.path.join(project_root, "frontend")

app.mount("/static", StaticFiles(directory=frontend_path), name="static")
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(achievements_router)

templates = Jinja2Templates(directory=frontend_path)


def get_context(request: Request):
    return {
        "request": request,
        "bot_username": os.getenv("TELEGRAM_BOT_USERNAME", "FrendlyMapBot"),
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

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)
