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
    user_id: int
    username: str
    rank_level: int
    gp_in_rank: int
    total_gp: int
    rank_name: str
    position: int


@dataclass
class AchievementRow:
    achievement_id: str
    code: str
    name: str
    description: str | None
    completed_count: int
    is_seasonal: bool


@dataclass
class ProfileRow:
    user_id: int
    username: str
    total_gp: int
    rank_level: int
    gp_in_rank: int
    rank_name: str
    approved_locations: int


def _derive_rank(total_gp: int) -> tuple[int, int, str]:
    rank_level = (total_gp // 100) + 1
    gp_in_rank = total_gp % 100
    return rank_level, gp_in_rank, f"Ранг {rank_level}"


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
                    SELECT user_id, username, total_gp, rank_level, gp_in_rank, rank_name, position
                    FROM {contract.leaderboard_view}
                    ORDER BY position ASC
                    LIMIT 10
                    """
                )
                rows = cur.fetchall()

        result: list[LeaderboardRow] = []
        for user_id, username, total_gp, rank_level, gp_in_rank, rank_name, position in rows:
            total_gp = int(total_gp or 0)
            if rank_level is None or gp_in_rank is None or not rank_name:
                rank_level, gp_in_rank, rank_name = _derive_rank(total_gp)

            display_username = username or "Пользователь"
            if not str(display_username).startswith("@"):
                display_username = f"@{display_username}"

            result.append(
                LeaderboardRow(
                    user_id=int(user_id),
                    username=display_username,
                    rank_level=int(rank_level),
                    gp_in_rank=int(gp_in_rank),
                    total_gp=total_gp,
                    rank_name=str(rank_name),
                    position=int(position),
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
                    SELECT achievement_id, code, name, description, completed_count, is_seasonal
                    FROM {contract.achievements_view}
                    ORDER BY name
                    """
                )
                rows = cur.fetchall()

        permanent: list[AchievementRow] = []
        seasonal: list[AchievementRow] = []
        for achievement_id, code, name, description, completed_count, is_seasonal in rows:
            item = AchievementRow(
                achievement_id=str(achievement_id),
                code=str(code),
                name=name or "Без названия",
                description=description,
                completed_count=int(completed_count or 0),
                is_seasonal=bool(is_seasonal),
            )
            if item.is_seasonal:
                seasonal.append(item)
            else:
                permanent.append(item)

        return permanent, seasonal, None
    except Exception as exc:
        return [], [], f"Не удалось загрузить достижения: {exc}"


def _load_profile(user_id: int) -> tuple[ProfileRow | None, str | None]:
    try:
        contract = get_db_contract()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT user_id, username, total_gp, rank_level, gp_in_rank, rank_name, approved_locations
                    FROM {contract.public_users_view}
                    WHERE user_id = %s
                    LIMIT 1
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

        if row is None:
            return None, None

        user_id, username, total_gp, rank_level, gp_in_rank, rank_name, approved_locations = row
        total_gp = int(total_gp or 0)
        if rank_level is None or gp_in_rank is None or not rank_name:
            rank_level, gp_in_rank, rank_name = _derive_rank(total_gp)

        return (
            ProfileRow(
                user_id=int(user_id),
                username=(username or "Пользователь").lstrip("@"),
                total_gp=total_gp,
                rank_level=int(rank_level),
                gp_in_rank=int(gp_in_rank),
                rank_name=str(rank_name),
                approved_locations=int(approved_locations or 0),
            ),
            None,
        )
    except Exception as exc:
        return None, f"Не удалось загрузить профиль: {exc}"


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
    profile, warning = _load_profile(user_id)
    context["profile"] = profile
    context["db_warning"] = warning
    return templates.TemplateResponse("profile.html", context)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
