import os
from dataclasses import dataclass

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import get_connection, get_db_contract, validate_db_contract

load_dotenv()

app = FastAPI(title="Frendly Map Website")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
frontend_path = os.path.join(project_root, "frontend")

app.mount("/static", StaticFiles(directory=frontend_path), name="static")
templates = Jinja2Templates(directory=frontend_path)


@dataclass
class LeaderboardRow:
    username: str
    rank_name: str
    points: int


@dataclass
class AchievementRow:
    achievement_id: str
    name: str
    description: str | None
    reward_points: int
    is_seasonal: bool


def _contract_healthcheck() -> str | None:
    try:
        ok, errors = validate_db_contract()
    except Exception as exc:
        return f"DB contract check failed: {exc}"

    if not ok:
        return "DB contract mismatch: " + "; ".join(errors)
    return None


@app.on_event("startup")
def startup_contract_check() -> None:
    error = _contract_healthcheck()
    if error:
        raise RuntimeError(error)


def _load_leaderboard() -> tuple[list[LeaderboardRow], str | None]:
    try:
        contract = get_db_contract()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT username, rank_name, gp_points
                    FROM {contract.leaderboard_view}
                    ORDER BY gp_points DESC NULLS LAST
                    LIMIT 10
                    """
                )
                rows = cur.fetchall()

        result: list[LeaderboardRow] = []
        for username, rank_name, gp_points in rows:
            display_username = username or "Пользователь"
            if not str(display_username).startswith("@"):
                display_username = f"@{display_username}"

            result.append(
                LeaderboardRow(
                    username=display_username,
                    rank_name=rank_name or "—",
                    points=int(gp_points or 0),
                )
            )
        return result, None
    except Exception as exc:
        return [], f"Не удалось загрузить лидерборд: {exc}"


def _load_achievements() -> tuple[list[AchievementRow], list[AchievementRow], str | None]:
    try:
        contract = get_db_contract()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT achievement_id, name, description, reward_points, is_seasonal
                    FROM {contract.achievements_view}
                    ORDER BY name
                    """
                )
                rows = cur.fetchall()

        permanent: list[AchievementRow] = []
        seasonal: list[AchievementRow] = []
        for achievement_id, name, description, reward_points, is_seasonal in rows:
            item = AchievementRow(
                achievement_id=str(achievement_id),
                name=name or "Без названия",
                description=description,
                reward_points=int(reward_points or 0),
                is_seasonal=bool(is_seasonal),
            )
            if item.is_seasonal:
                seasonal.append(item)
            else:
                permanent.append(item)

        return permanent, seasonal, None
    except Exception as exc:
        return [], [], f"Не удалось загрузить достижения: {exc}"


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
    context = get_context(request)
    permanent, seasonal, warning = _load_achievements()
    context["permanent_achievements"] = permanent
    context["seasonal_achievements"] = seasonal
    context["db_warning"] = warning
    return templates.TemplateResponse("achievements.html", context)


@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    context = get_context(request)
    rows, warning = _load_leaderboard()
    context["leaderboard_rows"] = rows
    context["db_warning"] = warning
    return templates.TemplateResponse("leaderboard.html", context)


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
