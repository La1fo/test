import os
from dataclasses import dataclass

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api import add_location, map as map_api
from .api.auth import login_username, register_username_account
from .database import DB_READ_ONLY, get_connection, get_db_contract, validate_db_contract
from .migrations import ensure_add_location_schema, ensure_auth_schema
from .session_auth import SESSION_COOKIE_NAME, create_session_cookie, get_current_user_id

load_dotenv()

app = FastAPI(title="Frendly Map Website")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
frontend_path = os.path.join(project_root, "frontend")
media_path = os.getenv("MEDIA_ROOT", os.path.join(project_root, "media"))

app.mount("/static", StaticFiles(directory=frontend_path), name="static")
os.makedirs(media_path, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_path), name="media")
templates = Jinja2Templates(directory=frontend_path)
app.include_router(add_location.router, prefix="/api/add-location", tags=["add-location"])
app.include_router(map_api.router, prefix="/api/map", tags=["map"])

WRITER_RANK_NAMES = (
    "🟢 Исследователь 1",
    "🟢 Исследователь 2",
    "🟢 Исследователь 3",
    "🔵 Путешественник 1",
    "🔵 Путешественник 2",
    "🔵 Путешественник 3",
    "🟡 Первооткрыватель 1",
    "🟡 Первооткрыватель 2",
    "🟡 Первооткрыватель 3",
)
CARTOGRAPHER_RANK_NAME = "🟣 Картограф"
MASTER_CARTOGRAPHER_RANK_NAME = "⭐ Мастер-картограф"
KNOWN_RANK_NAMES = set(WRITER_RANK_NAMES) | {CARTOGRAPHER_RANK_NAME, MASTER_CARTOGRAPHER_RANK_NAME}


@dataclass
class LeaderboardRow:
    user_id: int
    username: str
    rank_level: int
    gp_in_rank: int
    total_gp: int
    rank_name: str
    position: int
    gp_display: str


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
    gp_display: str


def _site_rank_name(total_gp: int, position: int | None = None) -> str:
    if total_gp >= 1300 and position is not None and position <= 10:
        return MASTER_CARTOGRAPHER_RANK_NAME
    if total_gp >= 900:
        return CARTOGRAPHER_RANK_NAME

    tier_index = min(total_gp // 100, len(WRITER_RANK_NAMES) - 1)
    return WRITER_RANK_NAMES[tier_index]


def _display_rank_name(rank_name: str | None, total_gp: int, position: int | None = None) -> str:
    normalized = (rank_name or "").strip()
    if normalized in KNOWN_RANK_NAMES:
        return normalized
    return _site_rank_name(total_gp, position)


def _format_gp_display(total_gp: int, gp_in_rank: int, rank_name: str) -> str:
    _ = total_gp
    _ = rank_name
    return str(max(0, gp_in_rank))


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
    if not DB_READ_ONLY:
        ensure_add_location_schema()
        ensure_auth_schema()


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
            if rank_level is None or gp_in_rank is None:
                raise RuntimeError("Contract violation: rank fields must be provided by leaderboard view")

            position = int(position)
            display_rank_name = _display_rank_name(rank_name, total_gp, position)
            gp_display = _format_gp_display(total_gp, int(gp_in_rank), display_rank_name)
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
                    rank_name=display_rank_name,
                    position=position,
                    gp_display=gp_display,
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
        if rank_level is None or gp_in_rank is None:
            raise RuntimeError("Contract violation: rank fields must be provided by public users view")

        display_rank_name = _display_rank_name(rank_name, total_gp)
        gp_display = _format_gp_display(total_gp, int(gp_in_rank), display_rank_name)

        return (
            ProfileRow(
                user_id=int(user_id),
                username=(username or "Пользователь").lstrip("@"),
                total_gp=total_gp,
                rank_level=int(rank_level),
                gp_in_rank=int(gp_in_rank),
                rank_name=display_rank_name,
                approved_locations=int(approved_locations or 0),
                gp_display=gp_display,
            ),
            None,
        )
    except Exception as exc:
        return None, f"Не удалось загрузить профиль: {exc}"


def get_context(request: Request):
    current_user_id = get_current_user_id(request, required=False)
    current_path = getattr(getattr(request, "url", None), "path", "")
    return {
        "request": request,
                "current_user_id": current_user_id,
        "is_authenticated": current_user_id is not None,
        "current_path": current_path,
    }


def _normalize_next(next_url: str | None, default: str = "/") -> str:
    candidate = (next_url or "").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return default
    return candidate


def _set_session_cookie(response: RedirectResponse, user_id: int) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        create_session_cookie(user_id),
        httponly=True,
        samesite="lax",
        secure=os.getenv("SESSION_COOKIE_SECURE", "0") == "1",
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", get_context(request))


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", get_context(request))


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", get_context(request))


@app.post("/api/session/login")
async def login_username_page(request: Request, username: str = Body(...), password: str = Body(...), next: str = Body("/")):
    _ = request
    if not username.strip() or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    result = login_username(username=username, password=password)
    response = RedirectResponse(url=_normalize_next(next), status_code=303)
    _set_session_cookie(response, int(result["user_id"]))
    return response


@app.post("/api/session/register")
async def register_username_page(
    request: Request,
    username: str = Body(...),
    password: str = Body(...),
    confirm_password: str = Body(...),
    next: str = Body("/profile/me"),
):
    _ = request
    if DB_READ_ONLY:
        raise HTTPException(status_code=503, detail="Registration disabled in read-only DB mode")
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Password confirmation does not match")
    user_id = register_username_account(username=username, password=password)
    response = RedirectResponse(url=_normalize_next(next, default="/profile/me"), status_code=303)
    _set_session_cookie(response, int(user_id))
    return response



@app.get("/logout")
async def logout(next: str | None = None):
    response = RedirectResponse(url=_normalize_next(next), status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/api/session/me")
async def session_me(request: Request):
    user_id = get_current_user_id(request, required=False)
    if user_id is None:
        return JSONResponse({"authenticated": False, "user_id": None})
    return JSONResponse({"authenticated": True, "user_id": int(user_id)})


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


@app.get("/add-location", response_class=HTMLResponse)
async def add_location_page(request: Request):
    return templates.TemplateResponse("add-location.html", get_context(request))


@app.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    return templates.TemplateResponse("map.html", get_context(request))


@app.get("/profile/me", response_class=HTMLResponse)
async def my_profile_page(request: Request):
    user_id = get_current_user_id(request, required=True)
    return await profile_page(request, user_id)


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
