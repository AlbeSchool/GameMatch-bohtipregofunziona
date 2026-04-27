"""
GameMatch — FastAPI Application Entry Point
Endpoint di salute, esempi e documentazione interattiva
"""

from datetime import datetime
from typing import Optional
import json
import secrets
from pathlib import Path
from fastapi import FastAPI, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.routing import APIRoute
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.database import engine, init_db, get_db
from app.schemas import (
    GameRead,
    MatchRead,
    TeamRead,
    UserRead,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    AdminUserUpdateRequest,
    AdminUserRenameRequest,
    ActionResponse,
)
from app.auth import authenticate_user, create_user, get_all_users, get_user_by_username, verify_password
from app.models import (
    User,
    PlayerProfile,
    TeamRequest,
    TeamCreatorRequest,
    Team,
    TeamRecruitment,
    TryoutSession,
)


app = FastAPI(
    title="GameMatch",
    version="1.0.0",
    docs_url=None,
    description=(
        "API FastAPI per GameMatch con autenticazione, dashboard, richieste matchmaking "
        "e strumenti tecnici per ispezionare database ed esempi schema."
    ),
    openapi_tags=[
        {"name": "utility", "description": "Endpoint tecnici e di supporto."},
        {"name": "auth", "description": "Login, registrazione e logout."},
        {"name": "matchmaking", "description": "Richieste utente e matchmaking."},
        {"name": "creator", "description": "Funzioni per team creator."},
        {"name": "admin", "description": "Pannello amministrativo."},
    ],
    generate_unique_id_function=lambda route: _generate_unique_operation_id(route),
)
ACTIVE_SESSIONS: dict[str, int] = {}

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _generate_unique_operation_id(route: APIRoute) -> str:
    methods = "_".join(sorted(method.lower() for method in route.methods or []))
    line_number = getattr(getattr(route.endpoint, "__code__", None), "co_firstlineno", 0)
    normalized_path = route.path_format.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    return f"{route.name}_{methods}_{normalized_path}_{line_number}"


def _form_example_payload(example: dict[str, object]) -> dict[str, object]:
    properties: dict[str, dict[str, str]] = {}
    required = []
    for key, value in example.items():
        required.append(key)
        if isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, int):
            value_type = "integer"
        else:
            value_type = "string"
        properties[key] = {"type": value_type}

    return {
        "requestBody": {
            "required": True,
            "content": {
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                    "example": example,
                }
            },
        }
    }


def _json_response_example(example: object, description: str = "Successful Response") -> dict[str, object]:
    return {
        "responses": {
            "200": {
                "description": description,
                "content": {
                    "application/json": {
                        "example": example,
                    }
                },
            }
        }
    }


def _json_request_payload(example: dict[str, object]) -> dict[str, object]:
    properties: dict[str, dict[str, str]] = {}
    required = []
    for key, value in example.items():
        required.append(key)
        if isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, int):
            value_type = "integer"
        else:
            value_type = "string"
        properties[key] = {"type": value_type}

    return {
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                    "example": example,
                }
            },
        }
    }


def _redirect_response_example(location: str = "/dashboard") -> dict[str, object]:
    return {
        "responses": {
            "302": {
                "description": f"Redirect to {location}",
                "content": {
                    "text/plain": {
                        "example": f"Redirect to {location}",
                    }
                },
            }
        }
    }


def _merge_openapi_metadata(operation: dict[str, object], extra: dict[str, object]) -> None:
    if "requestBody" in extra:
        operation["requestBody"] = extra["requestBody"]

    if "responses" in extra:
        responses = operation.setdefault("responses", {})
        for status_code, response_spec in extra["responses"].items():
            existing_response = responses.setdefault(status_code, {"description": "Successful Response"})
            if "content" in response_spec:
                existing_content = existing_response.setdefault("content", {})
                for content_type, content_spec in response_spec["content"].items():
                    existing_content[content_type] = content_spec


def _build_swagger_examples() -> dict[tuple[str, str], dict[str, object]]:
    return {
        ("/login/submit", "post"): {
            **_form_example_payload({"username": "Russo", "password": "1234"}),
            **_redirect_response_example("/dashboard"),
        },
        ("/register/submit", "post"): {
            **_form_example_payload(
                {
                    "username": "newPlayer",
                    "email": "newplayer@email.com",
                    "password": "StrongPass123!",
                    "confirm": "StrongPass123!",
                }
            ),
            "responses": {
                "200": {
                    "description": "Registration confirmation page",
                    "content": {"text/plain": {"example": "Registrazione completata con successo"}},
                }
            },
        },
        ("/creator/request", "post"): {
            **_form_example_payload({"message": "Vorrei gestire un team competitivo."}),
            **_redirect_response_example("/dashboard"),
        },
        ("/creator/teams/create", "post"): {
            **_form_example_payload(
                {"team_name": "NightRaiders", "game": "Valorant", "looking_for": "Duelist"}
            ),
            **_redirect_response_example("/dashboard"),
        },
        ("/creator/teams/{team_id}/recruitment", "post"): {
            **_form_example_payload({"game": "Rocket League", "looking_for": "Defender"}),
            **_redirect_response_example("/dashboard"),
        },
        ("/creator/teams/{team_id}/tryouts/create", "post"): {
            **_form_example_payload(
                {"scheduled_at": "2026-06-01T18:00:00", "slots": 4, "notes": "Provino aperto ai player ranked."}
            ),
            **_redirect_response_example("/dashboard"),
        },
        ("/creator/teams/{team_id}/delete", "post"): _redirect_response_example("/dashboard"),
        ("/creator/tryouts/{tryout_id}/delete", "post"): _redirect_response_example("/dashboard"),
        ("/request/submit", "post"): {
            **_form_example_payload(
                {
                    "game": "Valorant",
                    "rank": "Gold",
                    "role": "Duelist",
                    "attack_main": "",
                    "defense_main": "",
                    "preferred_mode": "",
                    "notes": "Gioco in fascia serale e cerco team competitivo.",
                }
            ),
            **_redirect_response_example("/dashboard"),
        },
        ("/admin/users/{target_user_id}/update", "post"): {
            **_form_example_payload({"username": "MarcoPro", "email": "marcopro@email.com"}),
            **_redirect_response_example("/dashboard"),
        },
        ("/api/admin/users/{target_user_id}", "put"): {
            **_json_request_payload({"username": "MarcoPro", "email": "marcopro@email.com"}),
            **_json_response_example({"status": "ok", "message": "Utente aggiornato"}),
        },
        ("/api/admin/users/{target_user_id}/rename", "patch"): {
            **_json_request_payload({"new_username": "MarcoLegend"}),
            **_json_response_example({"status": "ok", "message": "Username aggiornato"}),
        },
        ("/api/admin/users/{target_user_id}", "delete"): _json_response_example(
            {"status": "ok", "message": "Utente eliminato"}
        ),
        ("/admin/users/{target_user_id}/delete", "post"): _redirect_response_example("/dashboard"),
        ("/admin/users/{target_user_id}/set-creator", "post"): _redirect_response_example("/dashboard"),
        ("/admin/users/{target_user_id}/unset-creator", "post"): _redirect_response_example("/dashboard"),
        ("/admin/creator-requests/{request_id}/approve", "post"): _redirect_response_example("/dashboard"),
        ("/admin/creator-requests/{request_id}/reject", "post"): _redirect_response_example("/dashboard"),
        ("/creator/request/{request_id}/ack", "post"): _redirect_response_example("/dashboard"),
        ("/health/json", "get"): _json_response_example({"status": "ok"}),
        (
            "/tables",
            "get",
        ): _json_response_example(
            {
                "database": ["user", "team", "match"],
                "tables": [
                    {
                        "table": "user",
                        "columns": [
                            {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                            {"name": "username", "type": "VARCHAR(50)", "nullable": False, "primary_key": False},
                        ],
                    }
                ],
            }
        ),
        (
            "/examples",
            "get",
        ): _json_response_example(
            {
                "user": {"id": 1, "username": "proGamer", "email": "pro@email.com"},
                "team": {"id": 10, "name": "NightRaiders", "creator_id": 1, "members": []},
                "game": {"id": 2, "name": "Valorant", "genre": "FPS"},
                "match": {
                    "id": 100,
                    "scheduled_at": "2026-06-01T18:00:00",
                    "game_id": 2,
                    "team1_id": 10,
                    "team2_id": 11,
                },
            }
        ),
    }


def custom_openapi() -> dict[str, object]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    examples = _build_swagger_examples()
    for path, methods in examples.items():
        operation = schema.get("paths", {}).get(path[0] if isinstance(path, tuple) else path, {})
        method_name = path[1] if isinstance(path, tuple) else ""
        if method_name and method_name in operation:
            _merge_openapi_metadata(operation[method_name], methods)

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui() -> HTMLResponse:
    """Swagger UI con colori personalizzati per i metodi HTTP."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_css_url="/static/swagger-custom.css",
    )


GAME_OPTIONS = ["Valorant", "Rainbow Six Siege", "Fortnite", "Rocket League"]

GAME_RANK_OPTIONS = {
    "Valorant": [
        "Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ascendant", "Immortal", "Radiant"
    ],
    "Rainbow Six Siege": [
        "Copper", "Bronze", "Silver", "Gold", "Platinum", "Emerald", "Diamond", "Champion"
    ],
    "Fortnite": [
        "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Elite", "Champion", "Unreal"
    ],
    "Rocket League": [
        "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Champion", "Grand Champion", "Supersonic Legend"
    ],
}

GAME_CONFIG = {
    "Valorant": {
        "roles": ["Duelist", "Initiator", "Controller", "Sentinel"],
        "teams": [
            {"name": "Vortex Elite", "role": "Duelist", "target_rank": "Diamond"},
            {"name": "Night Ravens", "role": "Controller", "target_rank": "Platinum"},
            {"name": "Pulse Alpha", "role": "Initiator", "target_rank": "Ascendant"},
        ],
    },
    "Fortnite": {
        "roles": ["IGL", "Fragger", "Support", "Flex"],
        "teams": [
            {"name": "Storm Breakers", "role": "IGL", "target_rank": "Diamond"},
            {"name": "Build Masters", "role": "Fragger", "target_rank": "Platinum"},
            {"name": "Zero Ping", "role": "Flex", "target_rank": "Ascendant"},
        ],
    },
    "Rocket League": {
        "roles": ["Striker", "Playmaker", "Defender", "Flex"],
        "teams": [
            {"name": "Blue Strikers", "role": "Striker", "target_rank": "Diamond"},
            {"name": "Goal Keepers", "role": "Defender", "target_rank": "Platinum"},
            {"name": "Supersonic Trio", "role": "Flex", "target_rank": "Ascendant"},
        ],
    },
    "Rainbow Six Siege": {
        "attack_mains": [
            "Sledge", "Thatcher", "Ash", "Thermite", "Twitch", "Montagne", "Glaz", "Fuze", "Blitz", "IQ",
            "Buck", "Blackbeard", "Capitão", "Hibana", "Jackal", "Ying", "Zofia", "Dokkaebi", "Finka", "Lion",
            "Maverick", "Nomad", "Gridlock", "Nøkk", "Amaru", "Kali", "Iana", "Ace", "Zero", "Flores",
            "Osa", "Sens", "Grim", "Brava", "Ram", "Deimos"
        ],
        "defense_mains": [
            "Smoke", "Mute", "Castle", "Pulse", "Doc", "Rook", "Kapkan", "Tachanka", "Jäger", "Bandit",
            "Frost", "Valkyrie", "Caveira", "Echo", "Mira", "Lesion", "Ela", "Vigil", "Maestro", "Alibi",
            "Clash", "Kaid", "Mozzie", "Warden", "Goyo", "Wamai", "Oryx", "Melusi", "Aruni", "Thunderbird",
            "Thorn", "Azami", "Solis", "Fenrir", "Tubarão", "Sentry (Recluta)", "Skopós", "Rauora", "Denari"
        ],
        "modes": ["Entry", "Support", "Flex", "Anchor", "Roamer"],
        "teams": [
            {"name": "Breach Protocol", "mode": "Entry", "target_rank": "Diamond"},
            {"name": "Site Holders", "mode": "Anchor", "target_rank": "Platinum"},
            {"name": "Silent Drones", "mode": "Flex", "target_rank": "Emerald"},
        ],
    },
}

def _rank_score(game: str, rank: str) -> int:
    ranks = GAME_RANK_OPTIONS.get(game, [])
    normalized = rank.strip().lower()
    for idx, value in enumerate(ranks, start=1):
        if value.lower() == normalized:
            return idx
    return 1


def _match_team(
    game: str,
    rank: str,
    role: str,
    preferred_mode: str,
) -> Optional[dict[str, str]]:
    config = GAME_CONFIG.get(game)
    if not config:
        return None

    user_rank = _rank_score(game, rank)
    teams = config.get("teams", [])
    if not teams:
        return None

    def distance(team: dict[str, str]) -> int:
        team_rank = _rank_score(game, team.get("target_rank", "Gold"))
        rank_gap = abs(team_rank - user_rank)
        role_gap = 0
        if game == "Rainbow Six Siege":
            role_gap = 0 if team.get("mode", "").lower() == preferred_mode.lower() else 2
        else:
            role_gap = 0 if team.get("role", "").lower() == role.lower() else 2
        return rank_gap * 3 + role_gap

    return min(teams, key=distance)


def _looking_for_options_for_game(game: str) -> list[str]:
    if game == "Rainbow Six Siege":
        return GAME_CONFIG[game].get("modes", [])
    return GAME_CONFIG.get(game, {}).get("roles", [])


def _get_user_from_session(request: Request, db: Session) -> Optional[User]:
    token = request.cookies.get("session_token")
    if not token:
        return None
    user_id = ACTIVE_SESSIONS.get(token)
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


@app.on_event("startup")
def startup() -> None:
    """Inizializza il database all'avvio"""
    init_db()


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.get("/login")
def login_page() -> HTMLResponse:
    """Pagina di login"""
    html = """
    <!doctype html>
    <html lang="it">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>GameMatch - Login</title>
            <style>
                :root {
                    color-scheme: dark;
                    --bg: #0b1020;
                    --panel: #121a33;
                    --text: #eef2ff;
                    --muted: #aab4d6;
                    --accent: #67e8f9;
                    --accent-2: #a78bfa;
                }
                * { box-sizing: border-box; }
                body {
                    margin: 0;
                    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    background:
                        radial-gradient(circle at top left, rgba(103, 232, 249, 0.18), transparent 35%),
                        radial-gradient(circle at top right, rgba(167, 139, 250, 0.18), transparent 30%),
                        linear-gradient(180deg, #0b1020 0%, #060912 100%);
                    color: var(--text);
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    padding: 32px;
                }
                .card {
                    width: min(400px, 100%);
                    background: rgba(18, 26, 51, 0.88);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 24px;
                    padding: 36px;
                    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
                    backdrop-filter: blur(16px);
                }
                h1 {
                    margin: 0 0 12px;
                    font-size: 2.2rem;
                    line-height: 1;
                }
                p {
                    margin: 0 0 24px;
                    color: var(--muted);
                    font-size: 0.95rem;
                }
                .form-group {
                    margin-bottom: 16px;
                }
                label {
                    display: block;
                    margin-bottom: 6px;
                    font-size: 0.9rem;
                    color: var(--text);
                }
                input {
                    width: 100%;
                    padding: 10px 12px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    background: rgba(255, 255, 255, 0.04);
                    color: var(--text);
                    font-size: 1rem;
                }
                input:focus {
                    border-color: var(--accent);
                    outline: none;
                }
                button {
                    width: 100%;
                    padding: 11px;
                    background: linear-gradient(90deg, rgba(103, 232, 249, 0.3), rgba(167, 139, 250, 0.3));
                    border: 1px solid rgba(103, 232, 249, 0.4);
                    color: var(--text);
                    border-radius: 10px;
                    cursor: pointer;
                    font-size: 1rem;
                    margin-top: 8px;
                }
                button:hover {
                    border-color: var(--accent);
                    background: linear-gradient(90deg, rgba(103, 232, 249, 0.5), rgba(167, 139, 250, 0.5));
                }
                .link {
                    text-align: center;
                    margin-top: 16px;
                }
                a {
                    color: var(--accent);
                    text-decoration: none;
                }
                a:hover {
                    text-decoration: underline;
                }
                .error {
                    color: #ff6b6b;
                    padding: 10px;
                    border-radius: 8px;
                    background: rgba(255, 107, 107, 0.1);
                    margin-bottom: 16px;
                    font-size: 0.9rem;
                }
                .test-users {
                    background: rgba(103, 232, 249, 0.1);
                    border: 1px solid rgba(103, 232, 249, 0.2);
                    border-radius: 12px;
                    padding: 12px;
                    margin-top: 24px;
                    font-size: 0.85rem;
                }
                .test-users strong {
                    color: var(--accent);
                }
            </style>
        </head>
        <body>
            <main class="card">
                <h1>🎮 GameMatch</h1>
                <p>Accedi per gestire i tuoi team e le partite</p>
                
                <form method="POST" action="/login/submit">
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit">Accedi</button>
                </form>

                <div class="link">
                    Non hai un account? <a href="/register">Registrati</a>
                </div>

                <div class="test-users">
                    <strong>Utenti di prova:</strong><br>
                    <strong>Admin:</strong> Russo / 1234<br>
                    <br>
                    <strong>Utenti normali:</strong><br>
                    Marco, Sofia, Luca, Emma, Alex<br>
                    <strong>Password:</strong> password123
                </div>
            </main>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post(
    "/login/submit",
    tags=["auth"],
    summary="Autentica un utente",
    description="Riceve username e password dal form HTML e crea la sessione nel cookie.",
)
def login_submit(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Gestisce il submit del form di login"""
    user = authenticate_user(db, username, password)
    if not user:
        # Ritorna pagina login con errore
        html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8" />
                <title>Login Failed</title>
                <style>
                    :root {{
                        --bg: #0b1020;
                        --text: #eef2ff;
                        --accent: #67e8f9;
                    }}
                    body {{ background: var(--bg); color: var(--text); font-family: Inter, system-ui; }}
                    .container {{ max-width: 400px; margin: 100px auto; text-align: center; }}
                    .error {{ color: #ff6b6b; margin: 20px 0; }}
                    a {{ color: var(--accent); text-decoration: none; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Credenziali non valide</h2>
                    <p class="error">Username o password scorretti</p>
                    <a href="/login">← Torna al login</a>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=401)

    token = secrets.token_urlsafe(32)
    ACTIVE_SESSIONS[token] = user.id
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("session_token", token, httponly=True, samesite="lax")
    return response


@app.get(
    "/logout",
    tags=["auth"],
    summary="Termina la sessione",
    description="Rimuove il cookie di sessione e disconnette l'utente corrente.",
)
def logout(request: Request) -> RedirectResponse:
    token = request.cookies.get("session_token")
    if token and token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response


@app.get("/register")
def register_page() -> HTMLResponse:
    """Pagina di registrazione"""
    html = """
    <!doctype html>
    <html lang="it">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>GameMatch - Registrati</title>
            <style>
                :root {
                    color-scheme: dark;
                    --bg: #0b1020;
                    --panel: #121a33;
                    --text: #eef2ff;
                    --muted: #aab4d6;
                    --accent: #67e8f9;
                    --accent-2: #a78bfa;
                }
                * { box-sizing: border-box; }
                body {
                    margin: 0;
                    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    background:
                        radial-gradient(circle at top left, rgba(103, 232, 249, 0.18), transparent 35%),
                        radial-gradient(circle at top right, rgba(167, 139, 250, 0.18), transparent 30%),
                        linear-gradient(180deg, #0b1020 0%, #060912 100%);
                    color: var(--text);
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    padding: 32px;
                }
                .card {
                    width: min(400px, 100%);
                    background: rgba(18, 26, 51, 0.88);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 24px;
                    padding: 36px;
                    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
                    backdrop-filter: blur(16px);
                }
                h1 {
                    margin: 0 0 12px;
                    font-size: 2.2rem;
                    line-height: 1;
                }
                p {
                    margin: 0 0 24px;
                    color: var(--muted);
                    font-size: 0.95rem;
                }
                .form-group {
                    margin-bottom: 16px;
                }
                label {
                    display: block;
                    margin-bottom: 6px;
                    font-size: 0.9rem;
                    color: var(--text);
                }
                input {
                    width: 100%;
                    padding: 10px 12px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    background: rgba(255, 255, 255, 0.04);
                    color: var(--text);
                    font-size: 1rem;
                }
                input:focus {
                    border-color: var(--accent);
                    outline: none;
                }
                button {
                    width: 100%;
                    padding: 11px;
                    background: linear-gradient(90deg, rgba(103, 232, 249, 0.3), rgba(167, 139, 250, 0.3));
                    border: 1px solid rgba(103, 232, 249, 0.4);
                    color: var(--text);
                    border-radius: 10px;
                    cursor: pointer;
                    font-size: 1rem;
                    margin-top: 8px;
                }
                button:hover {
                    border-color: var(--accent);
                    background: linear-gradient(90deg, rgba(103, 232, 249, 0.5), rgba(167, 139, 250, 0.5));
                }
                .link {
                    text-align: center;
                    margin-top: 16px;
                }
                a {
                    color: var(--accent);
                    text-decoration: none;
                }
                a:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            <main class="card">
                <h1>📝 Registrati</h1>
                <p>Crea un nuovo account GameMatch</p>
                
                <form method="POST" action="/register/submit">
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" id="username" name="username" required minlength="3">
                    </div>
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required minlength="6">
                    </div>
                    <div class="form-group">
                        <label for="confirm">Conferma Password</label>
                        <input type="password" id="confirm" name="confirm" required minlength="6">
                    </div>
                    <button type="submit">Registrati</button>
                </form>

                <div class="link">
                    Hai già un account? <a href="/login">Accedi</a>
                </div>
            </main>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post(
    "/register/submit",
    tags=["auth"],
    summary="Registra un nuovo utente",
    description="Valida i dati del form di registrazione e crea un account GameMatch.",
)
def register_submit(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm: str = Form(...),
    db: Session = Depends(get_db)
):
    """Gestisce il submit del form di registrazione"""
    # Validazioni
    if password != confirm:
        html = """
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8" />
                <title>Registration Error</title>
                <style>
                    body { background: #0b1020; color: #eef2ff; font-family: Inter, system-ui; }
                    .container { max-width: 400px; margin: 100px auto; text-align: center; }
                    .error { color: #ff6b6b; margin: 20px 0; }
                    a { color: #67e8f9; text-decoration: none; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Errore Registrazione</h2>
                    <p class="error">Le password non coincidono</p>
                    <a href="/register">← Torna alla registrazione</a>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=400)
    
    # Controlla se username esiste
    if get_user_by_username(db, username):
        html = """
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8" />
                <title>Registration Error</title>
                <style>
                    body { background: #0b1020; color: #eef2ff; font-family: Inter, system-ui; }
                    .container { max-width: 400px; margin: 100px auto; text-align: center; }
                    .error { color: #ff6b6b; margin: 20px 0; }
                    a { color: #67e8f9; text-decoration: none; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Errore Registrazione</h2>
                    <p class="error">Username già esistente</p>
                    <a href="/register">← Torna alla registrazione</a>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=400)
    
    # Crea l'utente
    user = create_user(db, username, email, password, is_admin=0)
    
    html = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8" />
            <title>Registrazione Completata</title>
            <style>
                body {{ background: #0b1020; color: #eef2ff; font-family: Inter, system-ui; }}
                .container {{ max-width: 400px; margin: 100px auto; text-align: center; }}
                .success {{ color: #4ade80; margin: 20px 0; }}
                a {{ color: #67e8f9; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>✅ Registrazione Completata!</h2>
                <p class="success">Benvenuto {username}!</p>
                <p>Ora puoi accedere al tuo account</p>
                <a href="/login">Accedi →</a>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/")
def root() -> HTMLResponse:
    """Root endpoint — Pagina di presentazione"""
    html = """
    <!doctype html>
    <html lang="it">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>GameMatch API</title>
            <style>
                :root {
                    color-scheme: dark;
                    --bg: #0b1020;
                    --panel: #121a33;
                    --panel-2: #182344;
                    --text: #eef2ff;
                    --muted: #aab4d6;
                    --accent: #67e8f9;
                    --accent-2: #a78bfa;
                }
                * { box-sizing: border-box; }
                body {
                    margin: 0;
                    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    background:
                        radial-gradient(circle at top left, rgba(103, 232, 249, 0.18), transparent 35%),
                        radial-gradient(circle at top right, rgba(167, 139, 250, 0.18), transparent 30%),
                        linear-gradient(180deg, #0b1020 0%, #060912 100%);
                    color: var(--text);
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    padding: 32px;
                }
                .card {
                    width: min(920px, 100%);
                    background: rgba(18, 26, 51, 0.88);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 24px;
                    padding: 36px;
                    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
                    backdrop-filter: blur(16px);
                }
                .badge {
                    display: inline-flex;
                    padding: 8px 12px;
                    border-radius: 999px;
                    background: rgba(103, 232, 249, 0.12);
                    color: var(--accent);
                    font-size: 0.9rem;
                    letter-spacing: 0.02em;
                    margin-bottom: 16px;
                }
                h1 {
                    margin: 0 0 12px;
                    font-size: clamp(2.2rem, 4vw, 4rem);
                    line-height: 1;
                }
                p {
                    margin: 0;
                    color: var(--muted);
                    font-size: 1.05rem;
                    line-height: 1.65;
                }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 16px;
                    margin-top: 28px;
                }
                .panel {
                    background: linear-gradient(180deg, rgba(24, 35, 68, 0.9), rgba(18, 26, 51, 0.9));
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 18px;
                    padding: 18px;
                }
                .panel h2 {
                    margin: 0 0 10px;
                    font-size: 1rem;
                }
                .links {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    margin-top: 26px;
                }
                a {
                    color: var(--text);
                    text-decoration: none;
                    background: linear-gradient(90deg, rgba(103, 232, 249, 0.18), rgba(167, 139, 250, 0.18));
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    padding: 12px 16px;
                    border-radius: 14px;
                }
                a:hover {
                    border-color: rgba(103, 232, 249, 0.45);
                }
                code {
                    color: var(--accent);
                }
            </style>
        </head>
        <body>
            <main class="card">
                <div class="badge">GameMatch API online</div>
                <h1>GameMatch</h1>
                <p>
                    Backend FastAPI per la gestione di utenti, team e match.
                    Il progetto espone una root informativa, endpoint di salute e
                    una pagina esempi per verificare rapidamente gli schemi Pydantic.
                </p>

                <section class="grid" aria-label="Stato progetto">
                    <article class="panel">
                        <h2>Autenticazione</h2>
                        <p>Login, registrazione e gestione utenti.</p>
                    </article>
                    <article class="panel">
                        <h2>Endpoint utili</h2>
                        <p><code>/login</code>, <code>/register</code>, <code>/dashboard</code></p>
                    </article>
                    <article class="panel">
                        <h2>Database</h2>
                        <p>users, games, teams, matches, team_memberships.</p>
                    </article>
                </section>

                <div class="links">
                    <a href="/login">🔐 Accedi</a>
                    <a href="/register">📝 Registrati</a>
                    <a href="/health">📊 Status</a>
                    <a href="/docs">📖 Swagger</a>
                    <a href="/tables">🗄️ DB Schema</a>
                </div>
            </main>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/health")
def health() -> HTMLResponse:
    """Health check — Dashboard visiva dello stato"""
    table_names = inspect(engine).get_table_names()
    table_count = len(table_names)
    active_status = "Operativo"
    last_check = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    html = f"""
    <!doctype html>
    <html lang="it">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>GameMatch - Stato del sito</title>
            <style>
                :root {{
                    color-scheme: dark;
                    --bg: #07111f;
                    --card: rgba(12, 21, 40, 0.92);
                    --card-2: rgba(20, 31, 58, 0.95);
                    --text: #edf2ff;
                    --muted: #9fb0d0;
                    --green: #4ade80;
                    --cyan: #67e8f9;
                    --violet: #a78bfa;
                }}
                * {{ box-sizing: border-box; }}
                body {{
                    margin: 0;
                    min-height: 100vh;
                    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    color: var(--text);
                    background:
                        radial-gradient(circle at 20% 20%, rgba(103, 232, 249, 0.18), transparent 25%),
                        radial-gradient(circle at 80% 0%, rgba(167, 139, 250, 0.18), transparent 30%),
                        linear-gradient(180deg, #07111f 0%, #050810 100%);
                    padding: 32px;
                }}
                .wrap {{ max-width: 1100px; margin: 0 auto; }}
                .hero {{
                    display: grid;
                    grid-template-columns: 1.4fr 0.9fr;
                    gap: 20px;
                    align-items: stretch;
                }}
                .panel {{
                    background: var(--card);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 28px;
                    padding: 28px;
                    box-shadow: 0 24px 80px rgba(0,0,0,0.35);
                    backdrop-filter: blur(18px);
                }}
                .title {{ margin: 0 0 12px; font-size: clamp(2.2rem, 4vw, 4.2rem); line-height: 1; }}
                .subtitle {{ margin: 0; color: var(--muted); font-size: 1.05rem; line-height: 1.7; }}
                .badge {{
                    display: inline-flex;
                    align-items: center;
                    gap: 10px;
                    padding: 10px 14px;
                    border-radius: 999px;
                    background: rgba(74, 222, 128, 0.12);
                    color: var(--green);
                    margin-bottom: 18px;
                    border: 1px solid rgba(74, 222, 128, 0.22);
                    font-size: 0.95rem;
                }}
                .dot {{
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    background: var(--green);
                    box-shadow: 0 0 0 6px rgba(74, 222, 128, 0.18);
                }}
                .status-ring {{
                    width: 220px;
                    height: 220px;
                    border-radius: 50%;
                    margin: 0 auto;
                    display: grid;
                    place-items: center;
                    background:
                        radial-gradient(circle at center, rgba(7, 17, 31, 0.95) 0 58%, transparent 59%),
                        conic-gradient(from 220deg, var(--green), var(--cyan), var(--violet), var(--green));
                    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06);
                }}
                .status-core {{
                    width: 165px;
                    height: 165px;
                    border-radius: 50%;
                    display: grid;
                    place-items: center;
                    text-align: center;
                    background: linear-gradient(180deg, rgba(20,31,58,0.98), rgba(10,18,35,0.98));
                    border: 1px solid rgba(255,255,255,0.08);
                }}
                .status-core strong {{ display: block; font-size: 1.25rem; margin-bottom: 4px; }}
                .status-core span {{ color: var(--muted); font-size: 0.92rem; }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    gap: 16px;
                    margin-top: 20px;
                }}
                .stat {{
                    background: var(--card-2);
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 18px;
                    padding: 18px;
                }}
                .stat .label {{ color: var(--muted); font-size: 0.88rem; }}
                .stat .value {{ font-size: 1.4rem; margin-top: 10px; }}
                .section {{ margin-top: 22px; }}
                .grid {{
                    display: grid;
                    grid-template-columns: repeat(4, minmax(0, 1fr));
                    gap: 16px;
                    margin-top: 20px;
                }}
                .mini {{
                    background: var(--card-2);
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 18px;
                    padding: 18px;
                }}
                .mini h2 {{ margin: 0 0 8px; font-size: 1rem; }}
                .mini p {{ margin: 0; color: var(--muted); line-height: 1.55; }}
                .table-chip {{
                    display: inline-flex;
                    margin: 8px 8px 0 0;
                    padding: 8px 12px;
                    border-radius: 999px;
                    background: rgba(103, 232, 249, 0.12);
                    color: var(--cyan);
                    border: 1px solid rgba(103, 232, 249, 0.18);
                }}
                .links {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 22px; }}
                a {{
                    color: var(--text);
                    text-decoration: none;
                    background: linear-gradient(90deg, rgba(103, 232, 249, 0.18), rgba(167, 139, 250, 0.18));
                    border: 1px solid rgba(255,255,255,0.1);
                    padding: 12px 16px;
                    border-radius: 14px;
                }}
                a:hover {{ border-color: rgba(103, 232, 249, 0.45); }}
                .muted {{ color: var(--muted); }}
                @media (max-width: 900px) {{
                    .hero, .grid, .stats {{ grid-template-columns: 1fr; }}
                }}
            </style>
        </head>
        <body>
            <main class="wrap">
                <div class="hero">
                    <section class="panel">
                        <div class="badge"><span class="dot"></span> Controllo in tempo reale</div>
                        <h1 class="title">Stato del sito</h1>
                        <p class="subtitle">
                            Dashboard visiva per verificare rapidamente se GameMatch è online,
                            quali tabelle sono state create e quando è stato eseguito l'ultimo controllo.
                        </p>

                        <div class="stats">
                            <div class="stat">
                                <div class="label">Stato</div>
                                <div class="value">{active_status}</div>
                            </div>
                            <div class="stat">
                                <div class="label">Tabelle DB</div>
                                <div class="value">{table_count}</div>
                            </div>
                            <div class="stat">
                                <div class="label">Ultima verifica</div>
                                <div class="value" style="font-size: 1rem; line-height: 1.45;">{last_check}</div>
                            </div>
                        </div>

                        <div class="section">
                            <div class="muted">Tabelle presenti nel database</div>
                            <div>
                                {''.join(f'<span class="table-chip">{name}</span>' for name in table_names) if table_names else '<span class="muted">Nessuna tabella trovata</span>'}
                            </div>
                        </div>
                    </section>

                    <aside class="panel" style="display:grid; place-items:center; text-align:center;">
                        <div class="status-ring">
                            <div class="status-core">
                                <div>
                                    <strong>Online</strong>
                                    <span>Servizi operativi</span>
                                </div>
                            </div>
                        </div>
                    </aside>
                </div>

                <section class="grid" style="margin-top: 20px;">
                    <article class="mini">
                        <h2>API</h2>
                        <p>Endpoint di salute, esempi e documentazione già disponibili.</p>
                    </article>
                    <article class="mini">
                        <h2>Database</h2>
                        <p>Modello relazionale con users, games, teams, matches e team_memberships.</p>
                    </article>
                    <article class="mini">
                        <h2>Build</h2>
                        <p>FastAPI, Pydantic e SQLAlchemy pronti per lo sviluppo.</p>
                    </article>
                    <article class="mini">
                        <h2>Deploy</h2>
                        <p>Struttura compatibile con VPS e ambienti cloud standard.</p>
                    </article>
                </section>

                <div class="links">
                    <a href="/health/json">Controllo tecnico</a>
                    <a href="/tables">Vedi tabelle complete</a>
                    <a href="/docs">Apri Swagger UI</a>
                    <a href="/">Torna alla home</a>
                </div>
            </main>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get(
    "/health/json",
    tags=["utility"],
    summary="Stato tecnico JSON",
    description="Restituisce un payload minimale per i controlli automatici e i monitoraggi.",
)
def health_json() -> dict[str, str]:
    """Health check in JSON"""
    return {"status": "ok"}


@app.get("/status", response_class=HTMLResponse)
def status() -> HTMLResponse:
    """Status page — Alias per /health"""
    return health()


@app.get(
    "/tables",
    tags=["utility"],
    summary="Elenca tabelle e colonne",
    description="Restituisce i nomi delle tabelle e la definizione delle colonne lette dal database.",
)
def tables() -> dict[str, object]:
    """Liste tutte le tabelle del database con i loro schemi"""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    tables_info: list[dict[str, object]] = []

    for table_name in table_names:
        columns = [
            {
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column["nullable"],
                "primary_key": column["primary_key"],
            }
            for column in inspector.get_columns(table_name)
        ]
        tables_info.append({"table": table_name, "columns": columns})

    return {"database": table_names, "tables": tables_info}


@app.get(
    "/examples",
    tags=["utility"],
    summary="Esempi di risposta schema",
    description="Mostra esempi JSON pronti per verificare gli schemi Pydantic principali.",
)
def examples() -> dict[str, object]:
    """Esempi di risposta per verificare gli schemi Pydantic"""
    return {
        "user": UserRead(id=1, username="proGamer", email="pro@email.com"),
        "team": TeamRead(id=10, name="NightRaiders", creator_id=1, members=[]),
        "game": GameRead(id=2, name="Valorant", genre="FPS"),
        "match": MatchRead(
            id=100,
            scheduled_at=datetime.fromisoformat("2026-06-01T18:00:00"),
            game_id=2,
            team1_id=10,
            team2_id=11,
            game=GameRead(id=2, name="Valorant", genre="FPS"),
            team1=TeamRead(id=10, name="NightRaiders", creator_id=1, members=[]),
            team2=TeamRead(id=11, name="SkyHunters", creator_id=3, members=[]),
        ),
    }


@app.get("/dashboard")
def dashboard(request: Request, user_id: Optional[int] = None, db: Session = Depends(get_db)) -> HTMLResponse:
    """Dashboard separata per admin e utenti normali"""
    current_user = _get_user_from_session(request, db)
    if not current_user and user_id is not None:
        current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    if current_user.is_admin:
        normal_users = db.query(User).filter(User.is_admin == 0, User.is_team_creator == 0).order_by(User.id.asc()).all()
        creator_users = db.query(User).filter(User.is_team_creator == 1, User.is_admin == 0).order_by(User.id.asc()).all()
        all_requests = db.query(TeamRequest).order_by(TeamRequest.created_at.desc()).limit(50).all()
        creator_role_requests = (
            db.query(TeamCreatorRequest)
            .filter(TeamCreatorRequest.status == "pending")
            .order_by(TeamCreatorRequest.created_at.desc())
            .limit(50)
            .all()
        )
        table_names = inspect(engine).get_table_names()

        rows = []
        for user in normal_users:
            rows.append(
                f"""
                <tr>
                    <td>{user.id}</td>
                    <td>{user.username}</td>
                    <td>{user.email}</td>
                    <td>
                        <form method="POST" action="/admin/users/{user.id}/set-creator" style="display:inline; margin-right:8px;">
                            <button type="submit" class="btn">Promuovi a creatore team</button>
                        </form>
                    </td>
                    <td>
                        <form method="POST" action="/admin/users/{user.id}/update" style="display:flex; gap:6px; flex-wrap:wrap;">
                            <input type="text" name="username" value="{user.username}" required />
                            <input type="email" name="email" value="{user.email}" required />
                            <button type="submit" class="btn">Salva</button>
                        </form>
                    </td>
                    <td>
                        <form method="POST" action="/admin/users/{user.id}/delete">
                            <button type="submit" class="btn btn-danger">Elimina</button>
                        </form>
                    </td>
                </tr>
                """
            )

        request_rows = []
        for item in all_requests:
            request_rows.append(
                f"""
                <tr>
                    <td>{item.id}</td>
                    <td>{item.user.username if item.user else 'N/A'}</td>
                    <td>{item.game}</td>
                    <td>{item.rank}</td>
                    <td>{item.role or '-'}</td>
                    <td>{item.attack_main or '-'}</td>
                    <td>{item.defense_main or '-'}</td>
                    <td>{item.preferred_mode or '-'}</td>
                    <td>{item.recommended_team or '-'}</td>
                    <td>{item.response_message}</td>
                    <td>{item.created_at.strftime('%d/%m %H:%M')}</td>
                </tr>
                """
            )

        creator_request_rows = []
        for req in creator_role_requests:
            creator_request_rows.append(
                f"""
                <tr>
                    <td>{req.id}</td>
                    <td>{req.user.username if req.user else 'N/A'}</td>
                    <td>{req.message or '-'}</td>
                    <td>{req.status}</td>
                    <td>{req.created_at.strftime('%d/%m %H:%M')}</td>
                    <td>
                        <form method="POST" action="/admin/creator-requests/{req.id}/approve" style="display:inline;">
                            <button type="submit" class="btn">Approva</button>
                        </form>
                        <form method="POST" action="/admin/creator-requests/{req.id}/reject" style="display:inline; margin-left:8px;">
                            <button type="submit" class="btn btn-danger">Rifiuta</button>
                        </form>
                    </td>
                </tr>
                """
            )

        creator_user_rows = "".join([
            f"<tr><td>{u.id}</td><td>{u.username}</td><td>{u.email}</td><td>Team Creator</td><td><form method=\"POST\" action=\"/admin/users/{u.id}/unset-creator\"><button type=\"submit\" class=\"btn btn-danger\">Rendi utente normale</button></form></td></tr>"
            for u in creator_users
        ])

        html = f"""
        <!doctype html>
        <html lang="it">
            <head>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <title>GameMatch - Admin Dashboard</title>
                <style>
                    body {{ margin: 0; font-family: Inter, system-ui, sans-serif; background: #0b1020; color: #eef2ff; padding: 24px; }}
                    .container {{ max-width: 1200px; margin: 0 auto; }}
                    .card {{ background: #121a33; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 20px; margin-bottom: 16px; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    th, td {{ padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); text-align: left; }}
                    input {{ padding: 8px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.05); color: #eef2ff; }}
                    .btn {{ padding: 8px 12px; border-radius: 8px; border: 1px solid #67e8f9; background: rgba(103,232,249,0.2); color: #eef2ff; cursor: pointer; }}
                    .btn-danger {{ border-color: #f87171; background: rgba(248,113,113,0.18); }}
                    .links a {{ color: #67e8f9; margin-right: 12px; text-decoration: none; }}
                    .chips span {{ display: inline-block; padding: 6px 10px; margin: 4px; border-radius: 999px; background: rgba(103,232,249,0.12); color: #67e8f9; font-size: 0.85rem; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="card">
                        <h1>Admin Dashboard</h1>
                        <p>Benvenuto {current_user.username}. Qui puoi modificare ed eliminare solo utenti normali.</p>
                        <div class="links">
                            <a href="/dashboard">Ricarica dashboard</a>
                            <a href="/health">Status server</a>
                            <a href="/tables">Tabelle DB</a>
                            <a href="/examples">Esempi risposte</a>
                            <a href="/docs">Swagger</a>
                            <a href="/logout">Logout</a>
                        </div>
                        <div class="chips" style="margin-top: 12px;">
                            {''.join(f'<span>{t}</span>' for t in table_names)}
                        </div>
                    </div>
                    <div class="card">
                        <h2>Gestione utenti normali</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Username</th>
                                    <th>Email</th>
                                    <th>Ruolo Team</th>
                                    <th>Modifica</th>
                                    <th>Elimina</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join(rows)}
                            </tbody>
                        </table>
                    </div>
                    <div class="card">
                        <h2>Utenze creatori team (non admin sito)</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Username</th>
                                    <th>Email</th>
                                    <th>Ruolo</th>
                                    <th>Azione</th>
                                </tr>
                            </thead>
                            <tbody>
                                {creator_user_rows if creator_user_rows else '<tr><td colspan="5">Nessun creatore team.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                    <div class="card">
                        <h2>Richieste ruolo creatore team</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th><th>Utente</th><th>Messaggio</th><th>Stato</th><th>Data</th><th>Azione</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join(creator_request_rows) if creator_request_rows else '<tr><td colspan="6">Nessuna richiesta ruolo creatore.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                    <div class="card">
                        <h2>Richieste e risposte utenti (ultime 50)</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th><th>Utente</th><th>Gioco</th><th>Rank</th><th>Ruolo</th>
                                    <th>Main Att.</th><th>Main Dif.</th><th>Mode</th><th>Team</th><th>Risposta</th><th>Data</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join(request_rows) if request_rows else '<tr><td colspan="11">Nessuna richiesta ancora.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html)

    game_buttons = "".join([
        f'<a class="game-btn" href="/request/new?game={game}">{game}</a>'
        for game in GAME_OPTIONS
    ])

    creator_request = (
        db.query(TeamCreatorRequest)
        .filter(TeamCreatorRequest.user_id == current_user.id, TeamCreatorRequest.status == "pending")
        .first()
    )
    latest_creator_review = (
        db.query(TeamCreatorRequest)
        .filter(
            TeamCreatorRequest.user_id == current_user.id,
            TeamCreatorRequest.status.in_(["approved", "rejected"]),
            TeamCreatorRequest.seen_by_user == 0,
        )
        .order_by(TeamCreatorRequest.reviewed_at.desc())
        .first()
    )

    review_notification_html = ""
    if latest_creator_review:
        is_approved = latest_creator_review.status == "approved"
        notif_title = "Richiesta creatore team accettata" if is_approved else "Richiesta creatore team rifiutata"
        notif_msg = (
            "Gli admin del sito hanno approvato la tua richiesta. Ora puoi usare un account come creatore team."
            if is_approved
            else "Gli admin del sito hanno rifiutato la tua richiesta. Puoi inviarne una nuova con piu dettagli."
        )
        border_color = "rgba(52,211,153,0.6)" if is_approved else "rgba(248,113,113,0.6)"
        bg_color = "rgba(52,211,153,0.12)" if is_approved else "rgba(248,113,113,0.12)"
        review_notification_html = f"""
            <div class="card" style="border-color:{border_color}; background:{bg_color};">
                <h2 style="margin-top:0;">{notif_title}</h2>
                <p>{notif_msg}</p>
                <form method="POST" action="/creator/request/{latest_creator_review.id}/ack">
                    <button type="submit" class="game-btn" style="max-width: 280px;">Ok, ho letto la notifica</button>
                </form>
            </div>
        """
    if current_user.is_team_creator:
        creator_request_cta = '<p>Hai gia il ruolo di creatore team.</p>'
    elif creator_request:
        creator_request_cta = '<p>Hai gia una richiesta in attesa per diventare creatore di team.</p>'
    else:
        creator_request_cta = '''
            <form method="POST" action="/creator/request">
                <input type="text" name="message" placeholder="Scrivi una breve motivazione (opzionale)" style="width:100%; padding:10px; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:#0f172a; color:#f8fafc;" />
                <button type="submit" class="game-btn" style="margin-top:10px;">Richiedi di diventare creatore di team</button>
            </form>
        '''
    creator_badge = '<span style="padding:6px 10px; border-radius:999px; background:rgba(52,211,153,0.2); border:1px solid rgba(52,211,153,0.45);">CREATORE TEAM</span>' if current_user.is_team_creator else ''

    my_requests = db.query(TeamRequest).filter(TeamRequest.user_id == current_user.id).order_by(TeamRequest.created_at.desc()).limit(20).all()
    history_rows = "".join([
        f"<tr><td>{req.game}</td><td>{req.rank}</td><td>{req.recommended_team or '-'}</td><td>{req.response_message}</td><td>{req.created_at.strftime('%d/%m %H:%M')}</td></tr>"
        for req in my_requests
    ])

    creator_panel_html = ""
    if current_user.is_team_creator:
        my_teams = db.query(Team).filter(Team.creator_id == current_user.id).order_by(Team.created_at.desc()).all()
        recruitment_map: dict[int, TeamRecruitment] = {}
        for post in db.query(TeamRecruitment).join(Team).filter(Team.creator_id == current_user.id).all():
            recruitment_map[post.team_id] = post
        my_tryouts = (
            db.query(TryoutSession)
            .join(Team)
            .filter(Team.creator_id == current_user.id)
            .order_by(TryoutSession.scheduled_at.asc())
            .all()
        )

        team_rows = "".join([
            f"""
            <tr>
                <td>{team.id}</td>
                <td>{team.name}</td>
                <td>{recruitment_map[team.id].game if team.id in recruitment_map else '-'}</td>
                <td>{recruitment_map[team.id].looking_for if team.id in recruitment_map else '-'}</td>
                <td>{team.created_at.strftime('%d/%m %H:%M')}</td>
                <td>
                    <form method=\"POST\" action=\"/creator/teams/{team.id}/recruitment\" style=\"display:flex; gap:8px; flex-wrap:wrap;\">
                        <select id=\"team-game-{team.id}\" name=\"game\" required onchange=\"updateLookingFor('team-game-{team.id}','team-looking-{team.id}')\" style=\"padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:#0f172a; color:#f8fafc;\">{''.join([f'<option value="{g}" {"selected" if team.id in recruitment_map and recruitment_map[team.id].game == g else ""}>{g}</option>' for g in GAME_OPTIONS])}</select>
                        <select id=\"team-looking-{team.id}\" name=\"looking_for\" required style=\"padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:#0f172a; color:#f8fafc;\">{''.join([f'<option value="{opt}" {"selected" if team.id in recruitment_map and recruitment_map[team.id].looking_for == opt else ""}>{opt}</option>' for opt in _looking_for_options_for_game(recruitment_map[team.id].game if team.id in recruitment_map else GAME_OPTIONS[0])])}</select>
                        <button type=\"submit\" class=\"game-btn\" style=\"padding:8px 10px;\">Aggiorna recruiting</button>
                    </form>
                    <form method=\"POST\" action=\"/creator/teams/{team.id}/tryouts/create\" style=\"display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;\">
                        <input type=\"datetime-local\" name=\"scheduled_at\" required style=\"padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:#0f172a; color:#f8fafc;\" />
                        <input type=\"number\" min=\"1\" max=\"20\" name=\"slots\" value=\"4\" required style=\"width:90px; padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:#0f172a; color:#f8fafc;\" />
                        <input type=\"text\" name=\"notes\" placeholder=\"Info provino\" style=\"padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:#0f172a; color:#f8fafc;\" />
                        <button type=\"submit\" class=\"game-btn\" style=\"padding:8px 10px;\">Aggiungi provino</button>
                    </form>
                    <form method=\"POST\" action=\"/creator/teams/{team.id}/delete\" style=\"margin-top:8px;\">
                        <button type=\"submit\" class=\"game-btn\" style=\"padding:8px 10px; border-color:rgba(248,113,113,0.6); background:rgba(248,113,113,0.18);\">Elimina team</button>
                    </form>
                </td>
            </tr>
            """
            for team in my_teams
        ])

        tryout_rows = "".join([
            f"""
            <tr>
                <td>{session.team.name if session.team else '-'}</td>
                <td>{session.scheduled_at.strftime('%d/%m/%Y %H:%M')}</td>
                <td>{session.slots}</td>
                <td>{session.status}</td>
                <td>{session.notes or '-'}</td>
                <td>
                    <form method=\"POST\" action=\"/creator/tryouts/{session.id}/delete\">
                        <button type=\"submit\" class=\"game-btn\" style=\"padding:8px 10px; border-color:rgba(248,113,113,0.6); background:rgba(248,113,113,0.18);\">Elimina provino</button>
                    </form>
                </td>
            </tr>
            """
            for session in my_tryouts
        ])

        creator_panel_html = f"""
            <div class="card">
                <h2>Pannello Creatore Team</h2>
                <p>Qui puoi creare e gestire i tuoi team, specificare per quale gioco recluti e aprire sessioni provini.</p>
                <form method="POST" action="/creator/teams/create">
                    <input type="text" name="team_name" required minlength="3" maxlength="100" placeholder="Nome del nuovo team" style="width:100%; padding:10px; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:#0f172a; color:#f8fafc;" />
                    <select id="create-team-game" name="game" required onchange="updateLookingFor('create-team-game','create-team-looking')" style="width:100%; margin-top:8px; padding:10px; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:#0f172a; color:#f8fafc;">{''.join([f'<option value="{g}">{g}</option>' for g in GAME_OPTIONS])}</select>
                    <select id="create-team-looking" name="looking_for" required style="width:100%; margin-top:8px; padding:10px; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:#0f172a; color:#f8fafc;">{''.join([f'<option value="{opt}">{opt}</option>' for opt in _looking_for_options_for_game(GAME_OPTIONS[0])])}</select>
                    <button type="submit" class="game-btn" style="margin-top:10px;">Crea Team</button>
                </form>
                <table>
                    <thead><tr><th>ID</th><th>Nome Team</th><th>Gioco</th><th>Cerchiamo</th><th>Creato il</th><th>Gestione team/provini</th></tr></thead>
                    <tbody>{team_rows if team_rows else '<tr><td colspan="6">Non hai ancora creato team.</td></tr>'}</tbody>
                </table>
                <h3 style="margin-top:18px;">Sessioni provini attive</h3>
                <table>
                    <thead><tr><th>Team</th><th>Data/Ora</th><th>Slot</th><th>Stato</th><th>Note</th><th>Azione</th></tr></thead>
                    <tbody>{tryout_rows if tryout_rows else '<tr><td colspan="6">Nessuna sessione provini creata.</td></tr>'}</tbody>
                </table>
                <script>
                    const lookingForByGame = {json.dumps({g: _looking_for_options_for_game(g) for g in GAME_OPTIONS})};

                    function updateLookingFor(gameSelectId, lookingSelectId) {{
                        const gameSelect = document.getElementById(gameSelectId);
                        const lookingSelect = document.getElementById(lookingSelectId);
                        if (!gameSelect || !lookingSelect) return;
                        const selectedGame = gameSelect.value;
                        const options = lookingForByGame[selectedGame] || [];
                        const currentValue = lookingSelect.value;
                        lookingSelect.innerHTML = "";
                        for (const item of options) {{
                            const opt = document.createElement("option");
                            opt.value = item;
                            opt.textContent = item;
                            lookingSelect.appendChild(opt);
                        }}
                        if (options.includes(currentValue)) {{
                            lookingSelect.value = currentValue;
                        }}
                    }}

                    document.addEventListener("DOMContentLoaded", () => {{
                        updateLookingFor("create-team-game", "create-team-looking");
                        {''.join([f"updateLookingFor('team-game-{team.id}','team-looking-{team.id}');" for team in my_teams])}
                    }});
                </script>
            </div>
        """

    html = f"""
    <!doctype html>
    <html lang="it">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>GameMatch - User Dashboard</title>
            <style>
                body {{ margin: 0; font-family: Inter, system-ui, sans-serif; background: #0b1020; color: #eef2ff; padding: 24px; }}
                .container {{ max-width: 900px; margin: 0 auto; }}
                .card {{ background: #121a33; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 20px; margin-bottom: 16px; }}
                .games {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-top: 12px; }}
                .game-btn {{ display: inline-block; padding: 14px; border-radius: 12px; border: 1px solid #67e8f9; background: rgba(103,232,249,0.16); color: #eef2ff; text-decoration: none; text-align: center; }}
                .links a {{ color: #67e8f9; margin-right: 12px; text-decoration: none; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 9px; border-bottom: 1px solid rgba(255,255,255,0.08); text-align: left; }}
            </style>
        </head>
        <body>
            <div class="container">
                {review_notification_html}
                <div class="card">
                    <h1>User Dashboard</h1>
                    <p>Ciao {current_user.username} {creator_badge}. A che gioco vuoi fare richiesta per un team?</p>
                    <div class="links">
                        <a href="/dashboard">Ricarica dashboard</a>
                        <a href="/logout">Logout</a>
                    </div>
                    <div class="games">{game_buttons}</div>
                </div>

                <div class="card">
                    <h2>Diventa creatore di team</h2>
                    <p>Gli admin del sito possono approvare la tua richiesta per creare team con un account dedicato.</p>
                    {creator_request_cta}
                </div>

                {creator_panel_html}

                <div class="card">
                    <h2>Storico richieste e risposte</h2>
                    <table>
                        <thead><tr><th>Gioco</th><th>Rank</th><th>Team consigliato</th><th>Risposta</th><th>Data</th></tr></thead>
                        <tbody>{history_rows if history_rows else '<tr><td colspan="5">Nessuna richiesta inviata.</td></tr>'}</tbody>
                    </table>
                </div>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post(
    "/creator/request",
    tags=["creator"],
    summary="Richiedi il ruolo di team creator",
    description="Registra una richiesta pendente per abilitare l'account creator.",
)
def request_creator_role(
    message: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = _get_user_from_session(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user.is_admin:
        return HTMLResponse(content="Gli admin sito non possono inviare questa richiesta", status_code=400)
    if user.is_team_creator:
        return HTMLResponse(content="Sei gia creatore di team", status_code=400)

    pending = (
        db.query(TeamCreatorRequest)
        .filter(TeamCreatorRequest.user_id == user.id, TeamCreatorRequest.status == "pending")
        .first()
    )
    if pending:
        return RedirectResponse(url="/dashboard", status_code=302)

    req = TeamCreatorRequest(user_id=user.id, message=message.strip() or None, status="pending")
    db.add(req)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post("/creator/teams/create")
def creator_create_team(
    team_name: str = Form(...),
    game: str = Form(...),
    looking_for: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = _get_user_from_session(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not user.is_team_creator:
        return HTMLResponse(content="Solo i creatori team possono creare team", status_code=403)

    clean_name = team_name.strip()
    if len(clean_name) < 3:
        return HTMLResponse(content="Nome team troppo corto", status_code=400)
    if game not in GAME_OPTIONS:
        return HTMLResponse(content="Gioco non supportato", status_code=400)
    allowed_looking_for = _looking_for_options_for_game(game)
    if looking_for not in allowed_looking_for:
        return HTMLResponse(content="Opzione 'cosa si cerca' non valida per il gioco selezionato", status_code=400)
    clean_looking_for = looking_for.strip()

    existing = (
        db.query(Team)
        .filter(Team.creator_id == user.id, Team.name == clean_name)
        .first()
    )
    if existing:
        return HTMLResponse(content="Hai gia un team con questo nome", status_code=400)

    team = Team(name=clean_name, creator_id=user.id)
    db.add(team)
    db.commit()
    db.refresh(team)

    recruitment = TeamRecruitment(
        team_id=team.id,
        game=game,
        looking_for=clean_looking_for,
    )
    db.add(recruitment)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post("/creator/teams/{team_id}/recruitment")
def creator_update_recruitment(
    team_id: int,
    game: str = Form(...),
    looking_for: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = _get_user_from_session(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not user.is_team_creator:
        return HTMLResponse(content="Solo i creatori team possono aggiornare recruiting", status_code=403)
    if game not in GAME_OPTIONS:
        return HTMLResponse(content="Gioco non supportato", status_code=400)
    allowed_looking_for = _looking_for_options_for_game(game)
    if looking_for not in allowed_looking_for:
        return HTMLResponse(content="Opzione 'cosa si cerca' non valida per il gioco selezionato", status_code=400)

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return HTMLResponse(content="Team non trovato", status_code=404)
    if team.creator_id != user.id:
        return HTMLResponse(content="Puoi modificare solo i tuoi team", status_code=403)

    post = db.query(TeamRecruitment).filter(TeamRecruitment.team_id == team.id).first()
    if not post:
        post = TeamRecruitment(team_id=team.id, game=game, looking_for=looking_for.strip())
        db.add(post)
    else:
        post.game = game
        post.looking_for = looking_for.strip()
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post("/creator/teams/{team_id}/tryouts/create")
def creator_create_tryout(
    team_id: int,
    scheduled_at: str = Form(...),
    slots: int = Form(...),
    notes: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = _get_user_from_session(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not user.is_team_creator:
        return HTMLResponse(content="Solo i creatori team possono creare provini", status_code=403)

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return HTMLResponse(content="Team non trovato", status_code=404)
    if team.creator_id != user.id:
        return HTMLResponse(content="Puoi creare provini solo per i tuoi team", status_code=403)

    try:
        scheduled = datetime.fromisoformat(scheduled_at)
    except ValueError:
        return HTMLResponse(content="Data provino non valida", status_code=400)

    if slots < 1 or slots > 20:
        return HTMLResponse(content="Slot provino non validi", status_code=400)

    session = TryoutSession(
        team_id=team.id,
        scheduled_at=scheduled,
        slots=slots,
        notes=notes.strip() or None,
        status="open",
    )
    db.add(session)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post("/creator/teams/{team_id}/delete")
def creator_delete_team(team_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_session(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not user.is_team_creator:
        return HTMLResponse(content="Solo i creatori team possono eliminare team", status_code=403)

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return HTMLResponse(content="Team non trovato", status_code=404)
    if team.creator_id != user.id:
        return HTMLResponse(content="Puoi eliminare solo i tuoi team", status_code=403)

    db.delete(team)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post("/creator/tryouts/{tryout_id}/delete")
def creator_delete_tryout(tryout_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_session(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not user.is_team_creator:
        return HTMLResponse(content="Solo i creatori team possono eliminare provini", status_code=403)

    session = db.query(TryoutSession).filter(TryoutSession.id == tryout_id).first()
    if not session:
        return HTMLResponse(content="Sessione provino non trovata", status_code=404)
    if not session.team or session.team.creator_id != user.id:
        return HTMLResponse(content="Puoi eliminare solo i tuoi provini", status_code=403)

    db.delete(session)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/request/new")
def request_new(game: str, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    user = _get_user_from_session(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user.is_admin:
        return RedirectResponse(url="/dashboard", status_code=302)

    if game not in GAME_OPTIONS:
        return HTMLResponse(content="Gioco non supportato", status_code=400)

    rank_options = "".join([
        f'<option value="{r}">{r}</option>' for r in GAME_RANK_OPTIONS.get(game, [])
    ])

    if game == "Rainbow Six Siege":
        attack_options = "".join([f'<option value="{a}">{a}</option>' for a in GAME_CONFIG[game]["attack_mains"]])
        defense_options = "".join([f'<option value="{d}">{d}</option>' for d in GAME_CONFIG[game]["defense_mains"]])
        mode_options = "".join([f'<option value="{m}">{m}</option>' for m in GAME_CONFIG[game]["modes"]])
        game_specific = f"""
            <label>Main in Attacco</label>
            <select name="attack_main" required>{attack_options}</select>
            <label>Main in Difesa</label>
            <select name="defense_main" required>{defense_options}</select>
            <label>Stile / Ruolo squadra</label>
            <select name="preferred_mode" required>{mode_options}</select>
            <input type="hidden" name="role" value="" />
        """
    else:
        role_options = "".join([f'<option value="{r}">{r}</option>' for r in GAME_CONFIG[game]["roles"]])
        game_specific = f"""
            <label>Ruolo</label>
            <select name="role" required>{role_options}</select>
            <input type="hidden" name="attack_main" value="" />
            <input type="hidden" name="defense_main" value="" />
            <input type="hidden" name="preferred_mode" value="" />
        """

    html = f"""
    <!doctype html>
    <html lang="it">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Richiesta Team - {game}</title>
        <style>
          body {{ margin:0; font-family: Inter, system-ui, sans-serif; background:#0b1020; color:#eef2ff; padding:24px; }}
          .box {{ max-width:760px; margin:0 auto; background:#121a33; border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:20px; }}
                    .selected-game {{ display:inline-block; margin-top:6px; padding:8px 12px; border-radius:999px; border:1px solid rgba(255,255,255,0.15); background:rgba(255,255,255,0.06); color:#f8fafc; }}
          label {{ display:block; margin-top:12px; margin-bottom:6px; }}
                    select, input, textarea {{ width:100%; padding:10px; border-radius:8px; border:1px solid rgba(255,255,255,0.18); background:#0f172a; color:#f8fafc; }}
                    select option {{ color:#0f172a; background:#ffffff; }}
          .btn {{ margin-top:14px; padding:10px 14px; border-radius:8px; border:1px solid #67e8f9; background:rgba(103,232,249,0.2); color:#eef2ff; cursor:pointer; }}
                    .links a {{ color:#e2e8f0; margin-right:10px; text-decoration:none; }}
        </style>
      </head>
      <body>
        <div class="box">
          <h1>Richiesta Team - {game}</h1>
          <p>Inserisci le tue credenziali per il matchmaking competitivo.</p>
          <div class="links"><a href="/dashboard">← Torna dashboard</a><a href="/logout">Logout</a></div>
          <form method="POST" action="/request/submit">
            <label>Gioco</label>
                        <div class="selected-game">{game}</div>
                        <input type="hidden" name="game" value="{game}" />
            <label>Rank</label>
            <select name="rank" required>{rank_options}</select>
            {game_specific}
            <label>Note</label>
            <textarea name="notes" placeholder="Disponibilita, orari, obiettivi"></textarea>
            <button class="btn" type="submit">Invia richiesta e ricevi risposta</button>
          </form>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post(
    "/admin/users/{target_user_id}/update",
    tags=["admin"],
    summary="Aggiorna un utente",
    description="Permette all'admin di modificare username ed email di un account non amministrativo.",
)
def admin_update_user(
    target_user_id: int,
    username: str = Form(...),
    email: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    admin = _get_user_from_session(request, db)
    if not admin or not admin.is_admin:
        return HTMLResponse(content="Accesso negato", status_code=403)

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        return HTMLResponse(content="Utente non trovato", status_code=404)
    if target.is_admin:
        return HTMLResponse(content="Non puoi modificare un admin", status_code=400)

    target.username = username.strip()
    target.email = email.strip()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return HTMLResponse(content="Username o email gia in uso", status_code=400)

    return RedirectResponse(url="/dashboard", status_code=302)


@app.put(
    "/api/admin/users/{target_user_id}",
    tags=["admin"],
    summary="Update utente (API)",
    description="Aggiorna username ed email via JSON (metodo PUT).",
    response_model=ActionResponse,
)
def admin_update_user_api(
    target_user_id: int,
    payload: AdminUserUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ActionResponse:
    admin = _get_user_from_session(request, db)
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="Accesso negato")

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    if target.is_admin:
        raise HTTPException(status_code=400, detail="Non puoi modificare un admin")

    target.username = payload.username.strip()
    target.email = payload.email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username o email gia in uso")

    return ActionResponse(status="ok", message="Utente aggiornato")


@app.patch(
    "/api/admin/users/{target_user_id}/rename",
    tags=["admin"],
    summary="Rinomina utente (API)",
    description="Rinomina un utente via JSON (metodo PATCH).",
    response_model=ActionResponse,
)
def admin_rename_user_api(
    target_user_id: int,
    payload: AdminUserRenameRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ActionResponse:
    admin = _get_user_from_session(request, db)
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="Accesso negato")

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    if target.is_admin:
        raise HTTPException(status_code=400, detail="Non puoi rinominare un admin")

    target.username = payload.new_username.strip()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username gia in uso")

    return ActionResponse(status="ok", message="Username aggiornato")


@app.post(
    "/admin/users/{target_user_id}/delete",
    tags=["admin"],
    summary="Elimina un utente",
    description="Rimuove un account non amministrativo dal database.",
)
def admin_delete_user(
    target_user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    admin = _get_user_from_session(request, db)
    if not admin or not admin.is_admin:
        return HTMLResponse(content="Accesso negato", status_code=403)

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        return HTMLResponse(content="Utente non trovato", status_code=404)
    if target.is_admin:
        return HTMLResponse(content="Non puoi eliminare un admin", status_code=400)

    db.delete(target)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.delete(
    "/api/admin/users/{target_user_id}",
    tags=["admin"],
    summary="Delete utente (API)",
    description="Elimina un utente non admin via metodo DELETE.",
    response_model=ActionResponse,
)
def admin_delete_user_api(
    target_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> ActionResponse:
    admin = _get_user_from_session(request, db)
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="Accesso negato")

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    if target.is_admin:
        raise HTTPException(status_code=400, detail="Non puoi eliminare un admin")

    db.delete(target)
    db.commit()
    return ActionResponse(status="ok", message="Utente eliminato")


@app.post(
    "/admin/users/{target_user_id}/set-creator",
    tags=["admin"],
    summary="Promuovi a team creator",
    description="Imposta il flag team creator per un utente non amministrativo.",
)
def admin_set_creator(target_user_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _get_user_from_session(request, db)
    if not admin or not admin.is_admin:
        return HTMLResponse(content="Accesso negato", status_code=403)

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        return HTMLResponse(content="Utente non trovato", status_code=404)
    if target.is_admin:
        return HTMLResponse(content="Un admin sito non puo essere solo creatore team", status_code=400)

    target.is_team_creator = 1
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post(
    "/admin/users/{target_user_id}/unset-creator",
    tags=["admin"],
    summary="Rimuovi il ruolo creator",
    description="Disattiva il ruolo team creator per un utente non amministrativo.",
)
def admin_unset_creator(target_user_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _get_user_from_session(request, db)
    if not admin or not admin.is_admin:
        return HTMLResponse(content="Accesso negato", status_code=403)

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        return HTMLResponse(content="Utente non trovato", status_code=404)
    if target.is_admin:
        return HTMLResponse(content="Non puoi modificare il ruolo team creator di un admin sito", status_code=400)

    target.is_team_creator = 0
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post(
    "/admin/creator-requests/{request_id}/approve",
    tags=["admin"],
    summary="Approva una richiesta creator",
    description="Approva la richiesta e abilita l'utente come team creator.",
)
def approve_creator_request(request_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _get_user_from_session(request, db)
    if not admin or not admin.is_admin:
        return HTMLResponse(content="Accesso negato", status_code=403)

    creator_request = db.query(TeamCreatorRequest).filter(TeamCreatorRequest.id == request_id).first()
    if not creator_request:
        return HTMLResponse(content="Richiesta non trovata", status_code=404)

    creator_request.status = "approved"
    creator_request.seen_by_user = 0
    creator_request.reviewed_at = datetime.utcnow()
    if creator_request.user:
        creator_request.user.is_team_creator = 1
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post(
    "/admin/creator-requests/{request_id}/reject",
    tags=["admin"],
    summary="Rifiuta una richiesta creator",
    description="Rifiuta la richiesta e aggiorna lo stato di revisione.",
)
def reject_creator_request(request_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _get_user_from_session(request, db)
    if not admin or not admin.is_admin:
        return HTMLResponse(content="Accesso negato", status_code=403)

    creator_request = db.query(TeamCreatorRequest).filter(TeamCreatorRequest.id == request_id).first()
    if not creator_request:
        return HTMLResponse(content="Richiesta non trovata", status_code=404)

    creator_request.status = "rejected"
    creator_request.seen_by_user = 0
    creator_request.reviewed_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post(
    "/creator/request/{request_id}/ack",
    tags=["creator"],
    summary="Conferma notifica richiesta",
    description="Marca come letta la notifica relativa a una richiesta creator approvata o respinta.",
)
def creator_request_ack(request_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user_from_session(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    req = db.query(TeamCreatorRequest).filter(TeamCreatorRequest.id == request_id).first()
    if not req or req.user_id != user.id:
        return HTMLResponse(content="Notifica non trovata", status_code=404)

    req.seen_by_user = 1
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@app.post(
    "/request/submit",
    tags=["matchmaking"],
    summary="Invia una richiesta matchmaking",
    description="Salva una richiesta utente con gioco, rank e ruolo e suggerisce un team compatibile.",
)
def submit_request(
    game: str = Form(...),
    rank: str = Form(...),
    role: str = Form(""),
    attack_main: str = Form(""),
    defense_main: str = Form(""),
    preferred_mode: str = Form(""),
    notes: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = _get_user_from_session(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user.is_admin:
        return HTMLResponse(content="Gli admin non inviano richieste", status_code=400)
    if game not in GAME_OPTIONS:
        return HTMLResponse(content="Gioco non supportato", status_code=400)
    if rank not in GAME_RANK_OPTIONS.get(game, []):
        return HTMLResponse(content="Rank non valido per il gioco selezionato", status_code=400)

    best = _match_team(game=game, rank=rank, role=role, preferred_mode=preferred_mode)
    if best:
        team_name = best["name"]
        if game == "Rainbow Six Siege":
            response_message = f"Match trovato: {team_name}. Profilo valido per il mode {preferred_mode}."
        else:
            response_message = f"Match trovato: {team_name}. Ruolo richiesto: {best.get('role', 'flex')}."
    else:
        team_name = None
        response_message = "Nessun team compatibile ora. Riprova con un altro rank/ruolo o gioco."

    req = TeamRequest(
        user_id=user.id,
        game=game,
        rank=rank,
        role=role.strip() or None,
        attack_main=attack_main.strip() or None,
        defense_main=defense_main.strip() or None,
        preferred_mode=preferred_mode.strip() or None,
        notes=notes.strip() or None,
        recommended_team=team_name,
        response_message=response_message,
    )
    db.add(req)
    db.commit()

    # Mantiene la compatibilità con la vecchia tabella profilo
    profile = db.query(PlayerProfile).filter(PlayerProfile.user_id == user.id).first()
    if not profile:
        profile = PlayerProfile(user_id=user.id)
        db.add(profile)
    profile.preferred_game = game
    profile.role = role if role else (preferred_mode or "N/A")
    profile.rank = rank
    profile.weekly_hours = 8
    profile.notes = notes.strip() or None
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=302)



@app.get("/")
def root() -> HTMLResponse:
    """Root endpoint — Pagina di presentazione"""
    html = """
    <!doctype html>
    <html lang="it">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>GameMatch API</title>
            <style>
                :root {
                    color-scheme: dark;
                    --bg: #0b1020;
                    --panel: #121a33;
                    --panel-2: #182344;
                    --text: #eef2ff;
                    --muted: #aab4d6;
                    --accent: #67e8f9;
                    --accent-2: #a78bfa;
                }
                * { box-sizing: border-box; }
                body {
                    margin: 0;
                    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    background:
                        radial-gradient(circle at top left, rgba(103, 232, 249, 0.18), transparent 35%),
                        radial-gradient(circle at top right, rgba(167, 139, 250, 0.18), transparent 30%),
                        linear-gradient(180deg, #0b1020 0%, #060912 100%);
                    color: var(--text);
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    padding: 32px;
                }
                .card {
                    width: min(920px, 100%);
                    background: rgba(18, 26, 51, 0.88);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 24px;
                    padding: 36px;
                    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
                    backdrop-filter: blur(16px);
                }
                .badge {
                    display: inline-flex;
                    padding: 8px 12px;
                    border-radius: 999px;
                    background: rgba(103, 232, 249, 0.12);
                    color: var(--accent);
                    font-size: 0.9rem;
                    letter-spacing: 0.02em;
                    margin-bottom: 16px;
                }
                h1 {
                    margin: 0 0 12px;
                    font-size: clamp(2.2rem, 4vw, 4rem);
                    line-height: 1;
                }
                p {
                    margin: 0;
                    color: var(--muted);
                    font-size: 1.05rem;
                    line-height: 1.65;
                }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 16px;
                    margin-top: 28px;
                }
                .panel {
                    background: linear-gradient(180deg, rgba(24, 35, 68, 0.9), rgba(18, 26, 51, 0.9));
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 18px;
                    padding: 18px;
                }
                .panel h2 {
                    margin: 0 0 10px;
                    font-size: 1rem;
                }
                .links {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    margin-top: 26px;
                }
                a {
                    color: var(--text);
                    text-decoration: none;
                    background: linear-gradient(90deg, rgba(103, 232, 249, 0.18), rgba(167, 139, 250, 0.18));
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    padding: 12px 16px;
                    border-radius: 14px;
                }
                a:hover {
                    border-color: rgba(103, 232, 249, 0.45);
                }
                code {
                    color: var(--accent);
                }
            </style>
        </head>
        <body>
            <main class="card">
                <div class="badge">GameMatch API online</div>
                <h1>GameMatch</h1>
                <p>
                    Backend FastAPI per la gestione di utenti, team e match.
                    Il progetto espone una root informativa, endpoint di salute e
                    una pagina esempi per verificare rapidamente gli schemi Pydantic.
                </p>

                <section class="grid" aria-label="Stato progetto">
                    <article class="panel">
                        <h2>Stato</h2>
                        <p>Server avviato e pronto a ricevere richieste.</p>
                    </article>
                    <article class="panel">
                        <h2>Endpoint utili</h2>
                        <p><code>/health</code>, <code>/examples</code>, <code>/docs</code></p>
                    </article>
                    <article class="panel">
                        <h2>Database</h2>
                        <p>users, games, teams, matches, team_memberships.</p>
                    </article>
                </section>

                <div class="links">
                    <a href="/docs">Apri Swagger UI</a>
                    <a href="/redoc">Apri ReDoc</a>
                    <a href="/health">Verifica stato</a>
                    <a href="/tables">Vedi tabelle DB</a>
                    <a href="/examples">Vedi esempi JSON</a>
                </div>
            </main>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/health")
def health() -> HTMLResponse:
    """Health check — Dashboard visiva dello stato"""
    table_names = inspect(engine).get_table_names()
    table_count = len(table_names)
    active_status = "Operativo"
    last_check = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    html = f"""
    <!doctype html>
    <html lang="it">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>GameMatch - Stato del sito</title>
            <style>
                :root {{
                    color-scheme: dark;
                    --bg: #07111f;
                    --card: rgba(12, 21, 40, 0.92);
                    --card-2: rgba(20, 31, 58, 0.95);
                    --text: #edf2ff;
                    --muted: #9fb0d0;
                    --green: #4ade80;
                    --cyan: #67e8f9;
                    --violet: #a78bfa;
                }}
                * {{ box-sizing: border-box; }}
                body {{
                    margin: 0;
                    min-height: 100vh;
                    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    color: var(--text);
                    background:
                        radial-gradient(circle at 20% 20%, rgba(103, 232, 249, 0.18), transparent 25%),
                        radial-gradient(circle at 80% 0%, rgba(167, 139, 250, 0.18), transparent 30%),
                        linear-gradient(180deg, #07111f 0%, #050810 100%);
                    padding: 32px;
                }}
                .wrap {{ max-width: 1100px; margin: 0 auto; }}
                .hero {{
                    display: grid;
                    grid-template-columns: 1.4fr 0.9fr;
                    gap: 20px;
                    align-items: stretch;
                }}
                .panel {{
                    background: var(--card);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 28px;
                    padding: 28px;
                    box-shadow: 0 24px 80px rgba(0,0,0,0.35);
                    backdrop-filter: blur(18px);
                }}
                .title {{ margin: 0 0 12px; font-size: clamp(2.2rem, 4vw, 4.2rem); line-height: 1; }}
                .subtitle {{ margin: 0; color: var(--muted); font-size: 1.05rem; line-height: 1.7; }}
                .badge {{
                    display: inline-flex;
                    align-items: center;
                    gap: 10px;
                    padding: 10px 14px;
                    border-radius: 999px;
                    background: rgba(74, 222, 128, 0.12);
                    color: var(--green);
                    margin-bottom: 18px;
                    border: 1px solid rgba(74, 222, 128, 0.22);
                    font-size: 0.95rem;
                }}
                .dot {{
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    background: var(--green);
                    box-shadow: 0 0 0 6px rgba(74, 222, 128, 0.18);
                }}
                .status-ring {{
                    width: 220px;
                    height: 220px;
                    border-radius: 50%;
                    margin: 0 auto;
                    display: grid;
                    place-items: center;
                    background:
                        radial-gradient(circle at center, rgba(7, 17, 31, 0.95) 0 58%, transparent 59%),
                        conic-gradient(from 220deg, var(--green), var(--cyan), var(--violet), var(--green));
                    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06);
                }}
                .status-core {{
                    width: 165px;
                    height: 165px;
                    border-radius: 50%;
                    display: grid;
                    place-items: center;
                    text-align: center;
                    background: linear-gradient(180deg, rgba(20,31,58,0.98), rgba(10,18,35,0.98));
                    border: 1px solid rgba(255,255,255,0.08);
                }}
                .status-core strong {{ display: block; font-size: 1.25rem; margin-bottom: 4px; }}
                .status-core span {{ color: var(--muted); font-size: 0.92rem; }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    gap: 16px;
                    margin-top: 20px;
                }}
                .stat {{
                    background: var(--card-2);
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 18px;
                    padding: 18px;
                }}
                .stat .label {{ color: var(--muted); font-size: 0.88rem; }}
                .stat .value {{ font-size: 1.4rem; margin-top: 10px; }}
                .section {{ margin-top: 22px; }}
                .grid {{
                    display: grid;
                    grid-template-columns: repeat(4, minmax(0, 1fr));
                    gap: 16px;
                    margin-top: 20px;
                }}
                .mini {{
                    background: var(--card-2);
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 18px;
                    padding: 18px;
                }}
                .mini h2 {{ margin: 0 0 8px; font-size: 1rem; }}
                .mini p {{ margin: 0; color: var(--muted); line-height: 1.55; }}
                .table-chip {{
                    display: inline-flex;
                    margin: 8px 8px 0 0;
                    padding: 8px 12px;
                    border-radius: 999px;
                    background: rgba(103, 232, 249, 0.12);
                    color: var(--cyan);
                    border: 1px solid rgba(103, 232, 249, 0.18);
                }}
                .links {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 22px; }}
                a {{
                    color: var(--text);
                    text-decoration: none;
                    background: linear-gradient(90deg, rgba(103, 232, 249, 0.18), rgba(167, 139, 250, 0.18));
                    border: 1px solid rgba(255,255,255,0.1);
                    padding: 12px 16px;
                    border-radius: 14px;
                }}
                a:hover {{ border-color: rgba(103, 232, 249, 0.45); }}
                .muted {{ color: var(--muted); }}
                @media (max-width: 900px) {{
                    .hero, .grid, .stats {{ grid-template-columns: 1fr; }}
                }}
            </style>
        </head>
        <body>
            <main class="wrap">
                <div class="hero">
                    <section class="panel">
                        <div class="badge"><span class="dot"></span> Controllo in tempo reale</div>
                        <h1 class="title">Stato del sito</h1>
                        <p class="subtitle">
                            Dashboard visiva per verificare rapidamente se GameMatch è online,
                            quali tabelle sono state create e quando è stato eseguito l'ultimo controllo.
                        </p>

                        <div class="stats">
                            <div class="stat">
                                <div class="label">Stato</div>
                                <div class="value">{active_status}</div>
                            </div>
                            <div class="stat">
                                <div class="label">Tabelle DB</div>
                                <div class="value">{table_count}</div>
                            </div>
                            <div class="stat">
                                <div class="label">Ultima verifica</div>
                                <div class="value" style="font-size: 1rem; line-height: 1.45;">{last_check}</div>
                            </div>
                        </div>

                        <div class="section">
                            <div class="muted">Tabelle presenti nel database</div>
                            <div>
                                {''.join(f'<span class="table-chip">{name}</span>' for name in table_names) if table_names else '<span class="muted">Nessuna tabella trovata</span>'}
                            </div>
                        </div>
                    </section>

                    <aside class="panel" style="display:grid; place-items:center; text-align:center;">
                        <div class="status-ring">
                            <div class="status-core">
                                <div>
                                    <strong>Online</strong>
                                    <span>Servizi operativi</span>
                                </div>
                            </div>
                        </div>
                    </aside>
                </div>

                <section class="grid" style="margin-top: 20px;">
                    <article class="mini">
                        <h2>API</h2>
                        <p>Endpoint di salute, esempi e documentazione già disponibili.</p>
                    </article>
                    <article class="mini">
                        <h2>Database</h2>
                        <p>Modello relazionale con users, games, teams, matches e team_memberships.</p>
                    </article>
                    <article class="mini">
                        <h2>Build</h2>
                        <p>FastAPI, Pydantic e SQLAlchemy pronti per lo sviluppo.</p>
                    </article>
                    <article class="mini">
                        <h2>Deploy</h2>
                        <p>Struttura compatibile con VPS e ambienti cloud standard.</p>
                    </article>
                </section>

                <div class="links">
                    <a href="/health/json">Controllo tecnico</a>
                    <a href="/tables">Vedi tabelle complete</a>
                    <a href="/docs">Apri Swagger UI</a>
                    <a href="/">Torna alla home</a>
                </div>
            </main>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/health/json")
def health_json() -> dict[str, str]:
    """Health check in JSON"""
    return {"status": "ok"}


@app.get("/status", response_class=HTMLResponse)
def status() -> HTMLResponse:
    """Status page — Alias per /health"""
    return health()


@app.get("/tables")
def tables() -> dict[str, object]:
    """Liste tutte le tabelle del database con i loro schemi"""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    tables_info: list[dict[str, object]] = []

    for table_name in table_names:
        columns = [
            {
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column["nullable"],
                "primary_key": column["primary_key"],
            }
            for column in inspector.get_columns(table_name)
        ]
        tables_info.append({"table": table_name, "columns": columns})

    return {"database": table_names, "tables": tables_info}


@app.get("/examples")
def examples() -> dict[str, object]:
    """Esempi di risposta per verificare gli schemi Pydantic"""
    return {
        "user": UserRead(id=1, username="proGamer", email="pro@email.com"),
        "team": TeamRead(id=10, name="NightRaiders", creator_id=1, members=[]),
        "game": GameRead(id=2, name="Valorant", genre="FPS"),
        "match": MatchRead(
            id=100,
            scheduled_at=datetime.fromisoformat("2026-06-01T18:00:00"),
            game_id=2,
            team1_id=10,
            team2_id=11,
            game=GameRead(id=2, name="Valorant", genre="FPS"),
            team1=TeamRead(id=10, name="NightRaiders", creator_id=1, members=[]),
            team2=TeamRead(id=11, name="SkyHunters", creator_id=3, members=[]),
        ),
    }

