import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import get_connection, resolve_column, resolve_table_mapping

load_dotenv()

app = FastAPI(title="Frendly Map Website")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
frontend_path = os.path.join(project_root, "frontend")

app.mount("/static", StaticFiles(directory=frontend_path), name="static")
templates = Jinja2Templates(directory=frontend_path)


def _rank_name(points: int) -> str:
    if points >= 2500:
        return "Мастер-картограф"
    if points >= 2000:
        return "Картограф"
    if points >= 1500:
        return "Первооткрыватель"
    if points >= 1000:
        return "Путешественник"
    if points >= 600:
        return "Исследователь 1"
    if points >= 300:
        return "Исследователь 2"
    return "Исследователь 3"


def _is_truthy_seasonal(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "seasonal", "temporary", "event"}


def _load_leaderboard() -> tuple[list[dict[str, Any]], str | None]:
    try:
        table_map = resolve_table_mapping()
        users_table = table_map["users"]

        gp_override = os.getenv("FM_GP_COLUMN", "").strip()
        gp_candidates = [
            gp_override,
            "gp",
            "gp_points",
            "rank_points",
            "rating_points",
            "total_gp",
            "total_points",
            "score",
            "rating",
            "points",
            "coins",
        ]
        points_col = resolve_column(users_table, [c for c in gp_candidates if c])
        username_col = resolve_column(users_table, ["username", "user_name", "telegram_username", "name"])

        if not points_col or not username_col:
            return [], (
                f"В таблице {users_table} нет нужных колонок для лидерборда GP "
                f"(gp={points_col}, username={username_col}). "
                "Если GP хранится в отдельной колонке, укажите FM_GP_COLUMN в .env."
            )

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {username_col}, {points_col}
                    FROM {users_table}
                    ORDER BY {points_col} DESC NULLS LAST
                    LIMIT 10
                    """
                )
                rows = cur.fetchall()

        result = []
        for username, points in rows:
            points_value = int(points or 0)
            display_username = username or "Пользователь"
            if not str(display_username).startswith("@"):
                display_username = f"@{display_username}"
            result.append(
                {
                    "username": display_username,
                    "points": points_value,
                    "rank_name": _rank_name(points_value),
                }
            )
        return result, None
    except Exception as exc:
        return [], f"Не удалось загрузить лидерборд: {exc}"


def _load_achievements() -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    try:
        table_map = resolve_table_mapping()
        achievements_table = table_map["achievements"]

        id_col = resolve_column(achievements_table, ["id", "achievement_id"])
        name_col = resolve_column(achievements_table, ["name", "title", "achievement_name"])
        desc_col = resolve_column(achievements_table, ["description", "desc", "text"])
        reward_col = resolve_column(achievements_table, ["reward_points", "points", "reward"])
        seasonal_col = resolve_column(
            achievements_table,
            ["is_seasonal", "seasonal", "is_temporary", "is_event", "season_type", "type"],
        )

        if not id_col or not name_col:
            return [], [], f"В таблице {achievements_table} нет обязательных колонок id/name."

        select_parts = [id_col, name_col]
        select_parts.append(desc_col if desc_col else "NULL")
        select_parts.append(reward_col if reward_col else "0")
        select_parts.append(seasonal_col if seasonal_col else "NULL")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {', '.join(select_parts)} FROM {achievements_table} ORDER BY {name_col}"
                )
                rows = cur.fetchall()

        permanent, seasonal = [], []
        for ach_id, name, description, reward_points, seasonal_raw in rows:
            item = {
                "id": ach_id,
                "name": name,
                "description": description,
                "reward_points": int(reward_points or 0),
            }
            if _is_truthy_seasonal(seasonal_raw):
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
