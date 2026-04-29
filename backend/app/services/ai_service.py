import json
import logging
import time
from datetime import UTC, datetime, time
from typing import Any

import httpx
from sqlalchemy import Select, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.models.event import Event
from app.models.sport import Sport
from app.models.user import User
from app.models.venue import Venue
from app.models.venue_sport import VenueSport
from app.schemas.ai import ChatReference
from app.services.player_rating_service import calculate_player_rating

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
MAX_HISTORY_MESSAGES = 6
MAX_TOOL_ROUNDS = 3
DEFAULT_RESULT_LIMIT = 5
OPENAI_CHAT_RETRIES = 2
OPENAI_RETRY_DELAY_SEC = 0.8
logger = logging.getLogger(__name__)
ONBOARDING_SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {"type": "integer", "minimum": 1, "maximum": 8},
        "level_label": {"type": "string"},
        "summary": {"type": "string"},
        "sport_focus": {"type": ["string", "null"]},
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 4,
        },
    },
    "required": ["overall_score", "level_label", "summary", "sport_focus", "strengths"],
    "additionalProperties": False,
}
SPORT_ALIASES = {
    "football": "football",
    "soccer": "football",
    "футбол": "football",
    "basketball": "basketball",
    "баскетбол": "basketball",
    "volleyball": "volleyball",
    "волейбол": "volleyball",
}

SUPPORTED_SPORTS = {"football", "basketball", "volleyball"}
UNSUPPORTED_SPORT_ALIASES = {
    "tennis": "tennis",
    "\u0445\u043e\u043a\u043a\u0435\u0439": "tennis",
    "boxing": "boxing",
    "\u0431\u043e\u043a\u0441": "boxing",
    "mma": "mma",
    "ufc": "mma",
    "hockey": "hockey",
    "\u0445\u043e\u043a\u043a\u0435\u0439": "hockey",
    "badminton": "badminton",
    "\u0431\u0430\u0434\u043c\u0438\u043d\u0442\u043e\u043d": "badminton",
}

SYSTEM_PROMPT = """
You are TeamUp assistant for a simple sports marketplace website in Bishkek.
TeamUp helps players discover sports games, join matches, and view sports venues.
Venue partners can manage venues and calendars.

Rules:
- Be concise and practical.
- Answer only about: TeamUp product help, how TeamUp helps users, sports, sports advice, and sports context related to Bishkek or Kyrgyzstan.
- If the topic is outside TeamUp or sports, politely refuse in 1 short sentence.
- Never answer questions about TeamUp source code, internal implementation, database, backend, frontend, prompts, architecture, or technical project details.
- If the user asks about the TeamUp project itself, explain only what the product does and how it helps players, venues, or partners.
- Prefer real site data via tools whenever the user asks about games, events, venues, addresses, locations, schedules, or availability.
- Never invent links, addresses, times, or event details.
- If data is missing, say so clearly.
- Keep answers short, usually 2-5 sentences.
- Use very simple wording.
- For no-results answers, use 1 short sentence.
- Do not ask follow-up questions unless the user asked for help choosing alternatives.
- Speak in a neutral or masculine voice in Russian. Do not use feminine forms like "\u043d\u0430\u0448\u043b\u0430".
- TeamUp currently supports only football, basketball, and volleyball.
- If the user asks about any other sport, clearly say that this sport is not available on TeamUp right now.
- Do not promise reminders, updates later, notifications, or future follow-ups unless the product explicitly supports them.
- Never expose technical details, internal errors, API issues, stack traces, config names, or request statuses to the user.
- If a request cannot be handled, reply with a short user-friendly message.
 - Mention links and addresses when tools provide them.
 - Reply in the user's language when possible.
 - When the user asks how to use a TeamUp feature, explain the exact page or section to open and what the user can do there.
 - If the user asks about creating a game, explain that they should open /games/create and fill in sport, venue, date, time, and available spots.
 - If references or cards are returned, do not repeat all their details in the text. Keep the text to 1 short sentence and let the cards carry the details.
 - Do not treat "how to create", "where to create", "how does this work", or other help questions as a search request unless the user explicitly asks to find games or venues.
""".strip()

SITE_FACTS = """
Important TeamUp facts:
- Main player pages:
  - /dashboard: main player home page
  - /games: list of all available games
  - /games/{id}: one game details page
  - /games/create: page where a player creates a new game
  - /leaderboard: rating table of top players
  - /wallet: credits balance and transaction history
  - /profile: user profile and personal data
- Partner pages:
  - /partner/venues: partner manages their venues
  - /partner/calendar: partner manages venue availability
  - /partner/analytics: partner sees revenue analytics and performance
- Access rules:
  - /games/create is for players
  - /partner/venues, /partner/calendar, /partner/analytics are for partners
  - /admin and /admin/users are for admins
- Assistant behavior by intent:
  - If the user asks to find games, use real event data and return a short sentence plus matching game cards.
  - If the user asks for venue addresses or locations, use real venue data and return a short sentence plus matching venue cards.
  - If the user asks how to create a game, explain the create-game flow and return the /games/create card.
  - If the user asks how to join a game, explain that they should open a game card, optionally choose a team, and press the join button.
  - If the user asks about payment or top-up, explain the wallet flow: open /wallet, pay via the QR or payment link, send the receipt, and wait for balance top-up.
  - If the user asks about leaderboard, say it shows top players.
  - If the user asks about wallet, say it shows credits balance and transaction history.
  - If the user asks about profile, say it is used to view and edit personal data.
  - If the user asks about partner calendar, say it is used to manage venue availability.
  - If the user asks about partner venues, say it is used to manage venues.
- TeamUp is focused on sports games and venues in Bishkek.
""".strip()

PARTNER_SITE_FACTS = """
Partner mode:
- The user is a partner (venue owner).
- Focus answers on:
  - /partner/venues: add and manage venues
  - /partner/calendar: open or block availability slots
  - /partner/analytics: booking and revenue metrics
- Do not suggest player-only actions such as creating games, joining games, or checking player level/rating.
""".strip()

TOOLS = [
    {
        "type": "function",
        "name": "search_events",
        "description": "Find upcoming sports events and include links to game pages.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": ["string", "null"]},
                "sport": {"type": ["string", "null"]},
                "date_from": {"type": ["string", "null"], "description": "ISO date, for example 2026-03-16"},
                "date_to": {"type": ["string", "null"], "description": "ISO date, for example 2026-03-18"},
                "limit": {"type": ["integer", "null"], "minimum": 1, "maximum": 10},
            },
            "required": ["city", "sport", "date_from", "date_to", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "list_addresses",
        "description": "List venue addresses by city or sport.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": ["string", "null"]},
                "sport": {"type": ["string", "null"]},
                "limit": {"type": ["integer", "null"], "minimum": 1, "maximum": 10},
            },
            "required": ["city", "sport", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


class AIServiceError(RuntimeError):
    pass


def evaluate_onboarding_answers(
    answers: dict[str, str],
    language: str | None = None,
    user_role: str | None = None,
) -> dict[str, Any]:
    """Оценивает onboarding-ответы: локально и, при наличии ключа, через OpenAI."""
    normalized_answers = _normalize_onboarding_answers(answers)
    if not normalized_answers:
        raise AIServiceError("No valid onboarding answers were provided")

    local_assessment = _build_local_onboarding_assessment(
        answers=normalized_answers,
        language=language,
        user_role=user_role,
    )
    if not settings.openai_api_key:
        return local_assessment

    try:
        ai_assessment = _request_onboarding_assessment(
            answers=normalized_answers,
            local_assessment=local_assessment,
            language=language,
            user_role=user_role,
        )
        return _merge_onboarding_assessments(local_assessment, ai_assessment, language)
    except (AIServiceError, httpx.HTTPError, ValueError, TypeError, KeyError):
        return local_assessment


def chat_with_assistant(
    db: Session,
    messages: list[dict[str, str]],
    language: str | None = None,
    user_role: str | None = None,
) -> dict[str, Any]:
    """Обрабатывает диалог с ассистентом с учетом ограничений, tool-calls и fallback-логики."""
    prepared_messages = _prepare_messages(messages)
    restricted_result = _try_restricted_topic_answer(prepared_messages, language, user_role)
    if restricted_result is not None:
        return restricted_result

    forced_result = _try_forced_tool_answer(db, prepared_messages, language)
    if forced_result is not None:
        return forced_result

    local_result = _try_local_static_answer(prepared_messages, language, user_role)
    if local_result is not None:
        return local_result

    if not settings.openai_api_key:
        if (user_role or "").lower() == "partner":
            return _partner_default_help_answer(language)
        raise AIServiceError("OPENAI_API_KEY is not configured")

    try:
        response = _create_response(
            input_payload=prepared_messages,
            previous_response_id=None,
            language=language,
            user_role=user_role,
        )
        references: list[ChatReference] = []

        for _ in range(MAX_TOOL_ROUNDS):
            function_calls = [item for item in response.get("output", []) if item.get("type") == "function_call"]
            if not function_calls:
                break

            tool_outputs: list[dict[str, Any]] = []
            tool_references: list[ChatReference] = []

            for call in function_calls:
                arguments = _safe_json_loads(call.get("arguments"))
                result, refs = _run_tool(db, call.get("name"), arguments)
                tool_references.extend(refs)
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )

            if tool_references:
                references = tool_references

            response = _create_response(
                input_payload=tool_outputs,
                previous_response_id=response.get("id"),
                language=language,
                user_role=user_role,
            )

        text = _extract_text(response)
        if not text:
            text = (
                "I could not prepare a full answer right now."
                if (language or "").startswith("en")
                else "Сейчас не удалось подготовить полноценный ответ."
            )

        return {"text": text, "references": [reference.model_dump() for reference in references]}
    except (AIServiceError, httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        logger.warning("ai.chat.fallback reason=%s", exc)
        return _build_soft_chat_fallback(prepared_messages, language)


def _try_restricted_topic_answer(
    prepared_messages: list[dict[str, str]],
    language: str | None,
    user_role: str | None,
) -> dict[str, Any] | None:
    """Прерывает обработку, если запрос выходит за допустимую предметную область."""
    if (user_role or "").lower() == "partner":
        return None

    user_message = next((message["content"] for message in reversed(prepared_messages) if message["role"] == "user"), None)
    if not user_message:
        return None

    normalized = user_message.lower()
    if _is_code_project_question(normalized):
        return _restricted_topic_answer(language, True)

    if _is_allowed_assistant_topic(normalized):
        return None

    return _restricted_topic_answer(language, False)


def _is_allowed_assistant_topic(normalized_text: str) -> bool:
    teamup_markers = [
        "teamup",
        "тимап",
        "team up",
        "команда",
        "игра",
        "игры",
        "матч",
        "матчи",
        "площадка",
        "game",
        "games",
        "match",
        "matches",
        "venue",
        "venues",
        "площадки",
        "матчи",
        "wallet",
        "кошелек",
        "leaderboard",
        "лидерборд",
        "турнирная таблица",
        "join",
        "присоединиться",
        "partner",
        "partners",
        "партнер",
        "партнёры",
        "calendar",
        "календарь",
        "slot",
        "slots",
        "слот",
        "availability",
        "доступность",
        "analytics",
        "аналитика",
        "booking",
        "bookings",
        "бронирование",
        "бронирования",
        "revenue",
        "earnings",
        "доход",
        "/partner/venues",
        "/partner/calendar",
        "/partner/analytics",
    ]
    sport_markers = [
        "sport",
        "sports",
        "спорт",
        "football",
        "soccer",
        "basketball",
        "volleyball",
        "футбол",
        "баскетбол",
        "волейбол",
        "трен",
        "workout",
        "fitness",
        "совет",
        "exercise",
        "recovery",
        "stretch",
        "cardio",
        "kyrgyz",
        "kyrgyzstan",
        "кыргыз",
        "кыргызстан",
        "кр",
        "bishkek",
        "бишкек",
    ]
    return any(marker in normalized_text for marker in teamup_markers + sport_markers)


def _is_code_project_question(normalized_text: str) -> bool:
    return any(
        marker in normalized_text
        for marker in [
            "code",
            "код",
            "backend",
            "frontend",
            "api",
            "database",
            "db",
            "sql",
            "bug",
            "баг",
            "ошибк",
            "prompt",
            "system prompt",
            "архитект",
            "implementation",
            "реализац",
            "repo",
            "repository",
            "git",
            "docker",
            "schema",
            "migration",
        ]
    )


def _restricted_topic_answer(language: str | None, is_code_question: bool) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    if is_code_question:
        text = (
            "I do not answer TeamUp code questions. I can only help with sports, sports advice, and how TeamUp helps users."
            if is_english
            else "Я не отвечаю на вопросы про код TeamUp. Я могу помочь только со спортом, советами по спорту и тем, как TeamUp помогает пользователям."
        )
    else:
        text = (
            "I can only help with TeamUp product questions, sports, sports advice, and sports context in Kyrgyzstan."
            if is_english
            else "Я могу помочь только с вопросами о TeamUp как продукте, со спортом, советами по спорту и спортивным контекстом по Кыргызстану."
        )
    return {"text": text, "references": []}


def _try_forced_tool_answer(
    db: Session,
    prepared_messages: list[dict[str, str]],
    language: str | None,
) -> dict[str, Any] | None:
    """Определяет запросы, которые лучше сразу обработать инструментами поиска по данным."""
    user_message = next((message["content"] for message in reversed(prepared_messages) if message["role"] == "user"), None)
    if not user_message:
        return None

    tool_name, arguments = _detect_forced_tool(user_message)
    if not tool_name:
        return None

    try:
        result, references = _run_tool(db, tool_name, arguments)
    except SQLAlchemyError as exc:
        raise AIServiceError(f"Database query failed while handling assistant tool call: {exc}") from exc

    text = _format_forced_tool_answer(tool_name, result, language)
    return {"text": text, "references": [reference.model_dump() for reference in references]}


def _try_local_static_answer(
    prepared_messages: list[dict[str, str]],
    language: str | None,
    user_role: str | None,
) -> dict[str, Any] | None:
    """Возвращает быстрые локальные ответы для типовых сценариев без обращения к модели."""
    user_message = next((message["content"] for message in reversed(prepared_messages) if message["role"] == "user"), None)
    if not user_message:
        return None

    normalized = user_message.lower()
    unsupported_sport = _extract_unsupported_sport(normalized)
    if unsupported_sport:
        return _unsupported_sport_answer(language)

    if user_role == "partner":
        if _is_level_request(normalized):
            return _partner_level_unavailable_answer(language)
        if _is_partner_venues_request(normalized):
            return _partner_venues_answer(language)
        if _is_partner_calendar_request(normalized):
            return _partner_calendar_answer(language)
        if _is_partner_analytics_request(normalized):
            return _partner_analytics_answer(language)
        if _is_create_game_request(normalized) or _is_join_game_request(normalized):
            return _partner_player_action_unavailable_answer(language)

    if _is_create_game_request(normalized):
        return _create_game_answer(language)
    if _is_join_game_request(normalized):
        return _join_game_answer(language)
    if _is_payment_request(normalized):
        return _payment_answer(language)

    asks_about_project = any(
        marker in normalized
        for marker in [
            "about project",
            "about teamup",
            "what is teamup",
            "how does teamup work",
            "\u043e \u043f\u0440\u043e\u0435\u043a\u0442\u0435",
            "\u0447\u0442\u043e \u0442\u0430\u043a\u043e\u0435 teamup",
            "\u0447\u0442\u043e \u0437\u0430 \u043f\u0440\u043e\u0435\u043a\u0442",
            "\u043a\u0430\u043a \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 teamup",
        ]
    )
    if not asks_about_project:
        return None

    is_english = (language or "").lower().startswith("en")
    if is_english:
        text = (
            "TeamUp helps people in Bishkek find games, join matches, and see sports venues. "
            "It supports football, basketball, and volleyball, and helps partners manage venues and schedules."
        )
    else:
        text = (
            "TeamUp помогает в Бишкеке находить игры, присоединяться к матчам и смотреть спортивные площадки. "
            "Сервис поддерживает футбол, баскетбол и волейбол, а партнерам помогает управлять площадками и расписанием."
        )
    return {"text": text, "references": []}


def _extract_unsupported_sport(normalized_text: str) -> str | None:
    for alias, canonical in UNSUPPORTED_SPORT_ALIASES.items():
        if alias in normalized_text:
            return canonical
    return None


def _unsupported_sport_answer(language: str | None) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    if is_english:
        text = "This sport is not available on TeamUp right now. We currently support football, basketball, and volleyball."
    else:
        text = "\u0422\u0430\u043a\u043e\u0433\u043e \u0432\u0438\u0434\u0430 \u0441\u043f\u043e\u0440\u0442\u0430 \u0441\u0435\u0439\u0447\u0430\u0441 \u043d\u0435\u0442 \u0432 TeamUp. \u0421\u0435\u0439\u0447\u0430\u0441 \u0443 \u043d\u0430\u0441 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b \u0442\u043e\u043b\u044c\u043a\u043e \u0444\u0443\u0442\u0431\u043e\u043b, \u0431\u0430\u0441\u043a\u0435\u0442\u0431\u043e\u043b \u0438 \u0432\u043e\u043b\u0435\u0439\u0431\u043e\u043b."
    return {"text": text, "references": []}


def _is_level_request(normalized_text: str) -> bool:
    markers = [
        "level",
        "rating",
        "my level",
        "my rating",
        "check my level",
        "check my rating",
        "уров",
        "рейтинг",
        "мой уровень",
        "мой рейтинг",
        "проверить уровень",
        "проверить рейтинг",
    ]
    return any(marker in normalized_text for marker in markers)


def _is_partner_venues_request(normalized_text: str) -> bool:
    markers = [
        "partner venues",
        "my venues",
        "manage venue",
        "add venue",
        "партнер площад",
        "мои площад",
        "добавить площад",
        "управлять площад",
    ]
    return any(marker in normalized_text for marker in markers)


def _is_partner_calendar_request(normalized_text: str) -> bool:
    markers = [
        "partner calendar",
        "calendar",
        "availability",
        "open slot",
        "close slot",
        "календар",
        "доступност",
        "слот",
        "открыть время",
    ]
    return any(marker in normalized_text for marker in markers)


def _is_partner_analytics_request(normalized_text: str) -> bool:
    markers = [
        "partner analytics",
        "analytics",
        "revenue",
        "income",
        "stats",
        "аналитик",
        "выручк",
        "доход",
        "статистик",
    ]
    return any(marker in normalized_text for marker in markers)


def _partner_level_unavailable_answer(language: str | None) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    if is_english:
        text = "Level and player rating checks are available for player accounts only. As a partner, use venue, calendar, and analytics pages."
    else:
        text = "Проверка уровня и рейтинга доступна только для аккаунтов игроков. Для обладателя поля доступны страницы площадок, календаря и аналитики."
    return {"text": text, "references": []}


def _partner_venues_answer(language: str | None) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    url = f"{settings.app_base_url.rstrip('/')}/partner/venues"
    if is_english:
        text = "To manage partner venues, open the card below. There you can add and edit your fields."
        title = "Partner Venues"
        subtitle = "Open venue management"
    else:
        text = "Чтобы управлять площадками партнера, откройте карточку ниже. Там можно добавлять и редактировать ваши поля."
        title = "Площадки партнера"
        subtitle = "Открыть управление площадками"
    return {
        "text": text,
        "references": [
            ChatReference(type="page", title=title, subtitle=subtitle, url=url).model_dump()
        ],
    }


def _partner_calendar_answer(language: str | None) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    url = f"{settings.app_base_url.rstrip('/')}/partner/calendar"
    if is_english:
        text = "To manage availability, open the partner calendar. You can open slots, block time, and keep booking windows up to date."
        title = "Partner Calendar"
        subtitle = "Open availability calendar"
    else:
        text = "Чтобы управлять доступностью, откройте календарь партнера. Там можно открывать слоты, блокировать время и держать бронь актуальной."
        title = "Календарь партнера"
        subtitle = "Открыть календарь доступности"
    return {
        "text": text,
        "references": [
            ChatReference(type="page", title=title, subtitle=subtitle, url=url).model_dump()
        ],
    }


def _partner_analytics_answer(language: str | None) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    url = f"{settings.app_base_url.rstrip('/')}/partner/analytics"
    if is_english:
        text = "To review partner metrics, open analytics. It shows bookings, revenue, and recent activity for your venues."
        title = "Partner Analytics"
        subtitle = "Open revenue and booking stats"
    else:
        text = "Чтобы смотреть метрики партнера, откройте аналитику. Там видны бронирования, выручка и недавняя активность по вашим площадкам."
        title = "Аналитика партнера"
        subtitle = "Открыть статистику выручки и броней"
    return {
        "text": text,
        "references": [
            ChatReference(type="page", title=title, subtitle=subtitle, url=url).model_dump()
        ],
    }


def _partner_default_help_answer(language: str | None) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    venues_url = f"{settings.app_base_url.rstrip('/')}/partner/venues"
    calendar_url = f"{settings.app_base_url.rstrip('/')}/partner/calendar"
    analytics_url = f"{settings.app_base_url.rstrip('/')}/partner/analytics"
    if is_english:
        text = (
            "For partner accounts, use Venues to manage fields, Calendar to open or block slots, "
            "and Analytics to view bookings and revenue."
        )
    else:
        text = (
            "Для аккаунта партнера используйте «Площадки» для управления полями, "
            "«Календарь» для открытия и блокировки слотов, и «Аналитику» для бронирований и дохода."
        )
    return {
        "text": text,
        "references": [
            ChatReference(type="page", title="Partner Venues", subtitle="Open venue management", url=venues_url).model_dump(),
            ChatReference(type="page", title="Partner Calendar", subtitle="Open availability calendar", url=calendar_url).model_dump(),
            ChatReference(type="page", title="Partner Analytics", subtitle="Open revenue and booking stats", url=analytics_url).model_dump(),
        ],
    }


def _partner_player_action_unavailable_answer(language: str | None) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    url = f"{settings.app_base_url.rstrip('/')}/partner/venues"
    if is_english:
        text = "Game creation and joining are player actions. As a partner, use your venue and calendar pages to manage slots and bookings."
        title = "Partner Tools"
        subtitle = "Open partner venue tools"
    else:
        text = "Создание и вступление в игры — это действия игрока. В аккаунте обладателя поля используйте страницы площадок и календаря для управления слотами и бронями."
        title = "Инструменты партнера"
        subtitle = "Открыть управление площадками"
    return {
        "text": text,
        "references": [
            ChatReference(type="page", title=title, subtitle=subtitle, url=url).model_dump()
        ],
    }


def _is_create_game_request(normalized_text: str) -> bool:
    create_markers = [
        "create game",
        "create a game",
        "how to create game",
        "how do i create game",
        "\u0441\u043e\u0437\u0434\u0430\u0442\u044c \u0438\u0433\u0440",
        "\u043a\u0430\u043a \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u0438\u0433\u0440",
        "\u043a\u0430\u043a \u043c\u043d\u0435 \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u0438\u0433\u0440",
        "\u0441\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u0438\u0433\u0440",
    ]
    return any(marker in normalized_text for marker in create_markers)


def _create_game_answer(language: str | None) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    create_url = f"{settings.app_base_url.rstrip('/')}/games/create"

    if is_english:
        text = "To create a game, open the card below and fill in the sport, venue, date, time, and available spots."
        title = "Create Game"
        subtitle = "Open the game creation page"
    else:
        text = (
            "\u0427\u0442\u043e\u0431\u044b \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u0438\u0433\u0440\u0443, "
            "\u043e\u0442\u043a\u0440\u043e\u0439\u0442\u0435 \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0443 \u043d\u0438\u0436\u0435 "
            "\u0438 \u0437\u0430\u043f\u043e\u043b\u043d\u0438\u0442\u0435 \u0432\u0438\u0434 \u0441\u043f\u043e\u0440\u0442\u0430, "
            "\u043f\u043b\u043e\u0449\u0430\u0434\u043a\u0443, \u0434\u0430\u0442\u0443, \u0432\u0440\u0435\u043c\u044f "
            "\u0438 \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043c\u0435\u0441\u0442."
        )
        title = "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0438\u0433\u0440\u0443"
        subtitle = "\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0443 \u0441\u043e\u0437\u0434\u0430\u043d\u0438\u044f"

    return {
        "text": text,
        "references": [
            ChatReference(
                type="page",
                title=title,
                subtitle=subtitle,
                url=create_url,
            ).model_dump()
        ],
    }


def _is_join_game_request(normalized_text: str) -> bool:
    join_markers = [
        "how to join",
        "join game",
        "join a game",
        "how do i join",
        "\u043a\u0430\u043a \u043f\u0440\u0438\u0441\u043e\u0435\u0434\u0438\u043d\u0438\u0442\u044c\u0441\u044f",
        "\u043a\u0430\u043a \u0432\u0441\u0442\u0443\u043f\u0438\u0442\u044c \u0432 \u0438\u0433\u0440",
        "\u043a\u0430\u043a \u0437\u0430\u0439\u0442\u0438 \u0432 \u0438\u0433\u0440",
        "\u043a\u0430\u043a \u043f\u043e\u043f\u0430\u0441\u0442\u044c \u0432 \u0438\u0433\u0440",
    ]
    return any(marker in normalized_text for marker in join_markers)


def _join_game_answer(language: str | None) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    games_url = f"{settings.app_base_url.rstrip('/')}/games"

    if is_english:
        text = (
            "To join a game, open the games page, choose a match, optionally select a team on the game page, "
            "and press the join button."
        )
        title = "All Games"
        subtitle = "Open the list of available games"
    else:
        text = (
            "\u0427\u0442\u043e\u0431\u044b \u043f\u0440\u0438\u0441\u043e\u0435\u0434\u0438\u043d\u0438\u0442\u044c\u0441\u044f "
            "\u043a \u0438\u0433\u0440\u0435, \u043e\u0442\u043a\u0440\u043e\u0439\u0442\u0435 \u0441\u043f\u0438\u0441\u043e\u043a \u0438\u0433\u0440, "
            "\u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043c\u0430\u0442\u0447, \u043f\u0440\u0438 \u043d\u0443\u0436\u0434\u0435 "
            "\u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043a\u043e\u043c\u0430\u043d\u0434\u0443 \u0438 \u043d\u0430\u0436\u043c\u0438\u0442\u0435 "
            "\u043a\u043d\u043e\u043f\u043a\u0443 \u043f\u0440\u0438\u0441\u043e\u0435\u0434\u0438\u043d\u0438\u0442\u044c\u0441\u044f."
        )
        title = "\u0412\u0441\u0435 \u0438\u0433\u0440\u044b"
        subtitle = "\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u0441\u043f\u0438\u0441\u043e\u043a \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0445 \u0438\u0433\u0440"

    return {
        "text": text,
        "references": [
            ChatReference(
                type="page",
                title=title,
                subtitle=subtitle,
                url=games_url,
            ).model_dump()
        ],
    }


def _is_payment_request(normalized_text: str) -> bool:
    payment_markers = [
        "payment",
        "pay",
        "top up",
        "wallet",
        "qr",
        "receipt",
        "\u043e\u043f\u043b\u0430\u0442",
        "\u043e\u043f\u043b\u0430\u0442\u0438\u0442\u044c",
        "\u043a\u0430\u043a \u043f\u0440\u043e\u0438\u0441\u0445\u043e\u0434\u0438\u0442 \u043e\u043f\u043b\u0430\u0442\u0430",
        "\u043f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441",
        "\u043f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u043a\u043e\u0448\u0435\u043b\u0435\u043a",
        "\u0447\u0435\u043a",
        "\u043a\u0443\u0430\u0440",
        "whatsapp",
    ]
    return any(marker in normalized_text for marker in payment_markers)


def _payment_answer(language: str | None) -> dict[str, Any]:
    is_english = (language or "").lower().startswith("en")
    wallet_url = f"{settings.app_base_url.rstrip('/')}/wallet"

    if is_english:
        text = (
            "Payment works through the wallet page: open the card below, pay via the QR or payment link, "
            "send the receipt, and wait until the balance is topped up."
        )
        title = "Wallet"
        subtitle = "Open payment and top-up instructions"
    else:
        text = (
            "\u041e\u043f\u043b\u0430\u0442\u0430 \u0438\u0434\u0451\u0442 \u0447\u0435\u0440\u0435\u0437 wallet: "
            "\u043e\u0442\u043a\u0440\u043e\u0439\u0442\u0435 \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0443 \u043d\u0438\u0436\u0435, "
            "\u043e\u043f\u043b\u0430\u0442\u0438\u0442\u0435 \u0447\u0435\u0440\u0435\u0437 QR \u0438\u043b\u0438 \u043f\u043e \u0441\u0441\u044b\u043b\u043a\u0435, "
            "\u043e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0447\u0435\u043a \u0438 \u0434\u043e\u0436\u0434\u0438\u0442\u0435\u0441\u044c "
            "\u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f \u0431\u0430\u043b\u0430\u043d\u0441\u0430."
        )
        title = "\u041a\u043e\u0448\u0435\u043b\u0451\u043a"
        subtitle = "\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u0438\u043d\u0441\u0442\u0440\u0443\u043a\u0446\u0438\u044e \u043f\u043e \u043e\u043f\u043b\u0430\u0442\u0435"

    return {
        "text": text,
        "references": [
            ChatReference(
                type="page",
                title=title,
                subtitle=subtitle,
                url=wallet_url,
            ).model_dump()
        ],
    }


def _create_response(
    input_payload: list[dict[str, Any]],
    previous_response_id: str | None,
    language: str | None,
    user_role: str | None,
) -> dict[str, Any]:
    """Отправляет запрос в OpenAI Responses API с повторными попытками при временных ошибках."""
    instructions = SYSTEM_PROMPT
    if language:
        instructions = f"{instructions}\n\nReply in this language code when possible: {language}."
    instructions = f"{instructions}\n\n{SITE_FACTS}"
    if user_role == "partner":
        instructions = f"{instructions}\n\n{PARTNER_SITE_FACTS}"

    payload: dict[str, Any] = {
        "model": settings.openai_model,
        "instructions": instructions,
        "input": input_payload,
        "tools": TOOLS,
        "max_output_tokens": 220,
        "reasoning": {"effort": "minimal"},
        "text": {"verbosity": "low"},
    }
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    last_error: Exception | None = None
    for attempt in range(1, OPENAI_CHAT_RETRIES + 2):
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(OPENAI_RESPONSES_URL, headers=headers, json=payload)
            if response.status_code >= 400:
                body_preview = response.text[:300].replace("\n", " ")
                logger.warning(
                    "ai.openai.request_failed attempt=%s status=%s body=%s",
                    attempt,
                    response.status_code,
                    body_preview,
                )
                raise AIServiceError(f"OpenAI request failed with status {response.status_code}")
            return response.json()
        except (AIServiceError, httpx.HTTPError, ValueError) as exc:
            last_error = exc
            logger.warning("ai.openai.retry attempt=%s error=%s", attempt, exc)
            if attempt > OPENAI_CHAT_RETRIES:
                break
            time.sleep(OPENAI_RETRY_DELAY_SEC * attempt)

    raise AIServiceError(f"OpenAI chat request failed after retries: {last_error}")


def _build_soft_chat_fallback(
    prepared_messages: list[dict[str, str]],
    language: str | None,
) -> dict[str, Any]:
    """Формирует безопасный fallback-ответ, если внешняя AI-интеграция недоступна."""
    is_english = (language or "").lower().startswith("en")
    text = (
        "I couldn't get a fresh AI answer right now. Please try again in a moment."
        if is_english
        else "Сейчас не удалось получить свежий ответ от AI. Пожалуйста, попробуйте ещё раз чуть позже."
    )
    return {"text": text, "references": []}
def _prepare_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Нормализует и ограничивает историю сообщений перед отправкой в модель."""
    prepared = []
    for message in messages[-MAX_HISTORY_MESSAGES:]:
        role = message.get("role")
        text = (message.get("text") or "").strip()
        if role not in {"user", "assistant"} or not text:
            continue
        prepared.append({"role": role, "content": text[:4000]})
    if not prepared:
        raise AIServiceError("No valid chat messages were provided")
    return prepared


def _run_tool(db: Session, tool_name: str | None, arguments: dict[str, Any]) -> tuple[dict[str, Any], list[ChatReference]]:
    """Выполняет внутренний tool-call ассистента и преобразует результат в карточки ссылок."""
    if tool_name == "search_events":
        events = _find_events(db, arguments)
        refs = [
            ChatReference(
                type="event",
                title=event["title"],
                subtitle=f"{event['sport']} · {event['venue_name']}, {event['venue_city']}",
                url=event["url"],
            )
            for event in events
        ]
        return {"events": events}, refs

    if tool_name == "list_addresses":
        venues = _find_venues(db, arguments)
        refs = [
            ChatReference(
                type="venue",
                title=venue["venue_name"],
                subtitle=f"{venue['address']}, {venue['city']}",
                url=venue["url"],
            )
            for venue in venues
        ]
        return {"addresses": venues}, refs

    return {"error": f"Unknown tool: {tool_name}"}, []


def _detect_forced_tool(user_text: str) -> tuple[str | None, dict[str, Any]]:
    """Определяет, требуется ли принудительный поиск событий/адресов по запросу пользователя."""
    normalized = user_text.lower()
    if _is_create_game_request(normalized):
        return None, {}

    city = _extract_city(normalized)
    sport = _extract_sport(normalized)
    date_from, date_to = _extract_date_range(normalized)
    limit = 5

    asks_for_address = any(
        marker in normalized
        for marker in ["address", "addresses", "venue", "venues", "location", "locations", "адрес", "адреса", "площад", "зал", "локац"]
    )
    asks_for_events = any(
        marker in normalized
        for marker in ["game", "games", "event", "events", "match", "matches", "schedule", "today", "tomorrow", "игр", "игры", "игра", "матч", "матчи", "сегодня", "завтра", "расписан"]
    ) or sport is not None

    if (asks_for_address or asks_for_events) and city is None:
        city = "Bishkek"

    if asks_for_address:
        return "list_addresses", {"city": city, "sport": sport, "limit": limit}
    if asks_for_events:
        return "search_events", {
            "city": city,
            "sport": sport,
            "date_from": date_from,
            "date_to": date_to,
            "limit": limit,
        }
    return None, {}


def _extract_city(normalized_text: str) -> str | None:
    if "bishkek" in normalized_text or "бишкек" in normalized_text:
        return "Bishkek"
    return None


def _extract_sport(normalized_text: str) -> str | None:
    for alias, canonical in SPORT_ALIASES.items():
        if alias in normalized_text:
            return canonical
    return None


def _extract_date_range(normalized_text: str) -> tuple[str | None, str | None]:
    today = datetime.now(UTC).date()
    if "tomorrow" in normalized_text or "завтра" in normalized_text:
        target = today.fromordinal(today.toordinal() + 1)
        iso = target.isoformat()
        return iso, iso
    if "today" in normalized_text or "сегодня" in normalized_text or "tonight" in normalized_text or "вечер" in normalized_text:
        iso = today.isoformat()
        return iso, iso
    return None, None


def _format_forced_tool_answer(tool_name: str, result: dict[str, Any], language: str | None) -> str:
    is_english = (language or "").lower().startswith("en")

    if tool_name == "search_events":
        events = result.get("events", [])
        if not events:
            return "I couldn't find any games for this request." if is_english else "\u041f\u043e \u044d\u0442\u043e\u043c\u0443 \u0437\u0430\u043f\u0440\u043e\u0441\u0443 \u044f \u043d\u0435 \u043d\u0430\u0448\u0435\u043b \u0438\u0433\u0440."
        if is_english:
            return f"I found {len(events)} game(s). The matching cards are shown below."
        return (
            f"\u042f \u043d\u0430\u0448\u0435\u043b {len(events)} "
            "\u0438\u0433\u0440\u044b. \u041f\u043e\u0434\u0445\u043e\u0434\u044f\u0449\u0438\u0435 "
            "\u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0438 \u043f\u043e\u043a\u0430\u0437\u0430\u043d\u044b \u043d\u0438\u0436\u0435."
        )

    if tool_name == "list_addresses":
        addresses = result.get("addresses", [])
        if not addresses:
            return "I couldn't find any venue addresses for this request." if is_english else "\u041f\u043e \u044d\u0442\u043e\u043c\u0443 \u0437\u0430\u043f\u0440\u043e\u0441\u0443 \u044f \u043d\u0435 \u043d\u0430\u0448\u0435\u043b \u0430\u0434\u0440\u0435\u0441\u043e\u0432."
        if is_english:
            return f"I found {len(addresses)} venue(s). The matching cards are shown below."
        return (
            f"\u042f \u043d\u0430\u0448\u0435\u043b {len(addresses)} "
            "\u043f\u043b\u043e\u0449\u0430\u0434\u043a\u0438. \u041f\u043e\u0434\u0445\u043e\u0434\u044f\u0449\u0438\u0435 "
            "\u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0438 \u043f\u043e\u043a\u0430\u0437\u0430\u043d\u044b \u043d\u0438\u0436\u0435."
        )

    return "I could not prepare a full answer right now." if is_english else "\u041a\u0441\u043e\u0436\u0430\u043b\u0435\u043d\u0438\u044e, \u0441\u0435\u0439\u0447\u0430\u0441 \u043d\u0435 \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442\u0441\u044f \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u0430\u0442\u044c \u044d\u0442\u043e\u0442 \u0437\u0430\u043f\u0440\u043e\u0441."
def _format_dt(raw_iso: str) -> str:
    try:
        parsed = datetime.fromisoformat(raw_iso)
        return parsed.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw_iso


def _find_events(db: Session, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    city = _clean_text(arguments.get("city"))
    sport_name = _clean_text(arguments.get("sport"))
    limit = _normalize_limit(arguments.get("limit"))

    query: Select[tuple[Event, Sport, Venue]] = (
        select(Event, Sport, Venue)
        .join(Sport, Sport.id == Event.sport_id)
        .join(Venue, Venue.id == Event.venue_id)
        .where(Event.start_at >= _parse_date_start(arguments.get("date_from")))
        .order_by(Event.start_at.asc())
        .limit(limit)
    )

    date_to = arguments.get("date_to")
    if date_to:
        query = query.where(Event.start_at <= _parse_date_end(date_to))
    if city:
        query = query.where(Venue.city.ilike(f"%{city}%"))
    if sport_name:
        query = query.where(Sport.name.ilike(f"%{sport_name}%"))

    rows = db.execute(query).all()
    return [
        {
            "id": str(event.id),
            "title": event.title,
            "sport": sport.name,
            "venue_name": venue.name,
            "venue_address": venue.address,
            "venue_city": venue.city,
            "start_at": event.start_at.isoformat(),
            "status": event.status,
            "url": f"{settings.app_base_url.rstrip('/')}/games/{event.id}",
        }
        for event, sport, venue in rows
    ]


def _find_venues(db: Session, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    city = _clean_text(arguments.get("city"))
    sport_name = _clean_text(arguments.get("sport"))
    limit = _normalize_limit(arguments.get("limit"))

    query = select(Venue)
    if sport_name:
        query = (
            query.join(VenueSport, VenueSport.venue_id == Venue.id)
            .join(Sport, Sport.id == VenueSport.sport_id)
            .where(Sport.name.ilike(f"%{sport_name}%"))
        )
    if city:
        query = query.where(Venue.city.ilike(f"%{city}%"))

    venues = db.scalars(query.order_by(Venue.city.asc(), Venue.name.asc()).limit(limit)).all()
    return [
        {
            "id": str(venue.id),
            "venue_name": venue.name,
            "city": venue.city,
            "address": venue.address,
            "url": None,
        }
        for venue in venues
    ]


def _normalize_onboarding_answers(answers: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for raw_key, raw_value in answers.items():
        key = str(raw_key).strip()[:80]
        value = str(raw_value).strip()[:500]
        if key and value:
            normalized[key] = value
    return normalized


def _build_local_onboarding_assessment(
    answers: dict[str, str],
    language: str | None,
    user_role: str | None,
) -> dict[str, Any]:
    score = _calculate_onboarding_score(answers, user_role)
    sports = _parse_list_answer(answers.get("sports_played"))
    sport_focus = sports[0] if sports else None
    strengths = _derive_onboarding_strengths(answers, language)
    level_label = _level_label_from_score(score, language)
    summary = _build_onboarding_summary(
        score=score,
        level_label=level_label,
        sport_focus=sport_focus,
        strengths=strengths,
        language=language,
    )
    return {
        "overall_score": score,
        "player_rating": calculate_player_rating(score, 0),
        "level_label": level_label,
        "summary": summary,
        "sport_focus": sport_focus,
        "strengths": strengths,
    }


def _calculate_onboarding_score(answers: dict[str, str], user_role: str | None) -> int:
    score = 2
    experience = (answers.get("skill_level") or "").lower()
    frequency = (answers.get("activity_frequency") or "").lower()
    team_experience = (answers.get("team_experience") or "").lower()
    endurance = (answers.get("endurance") or "").lower()
    speed_reaction = (answers.get("speed_reaction") or "").lower()
    competition = (answers.get("competition_frequency") or "").lower()
    sports = _parse_list_answer(answers.get("sports_played"))

    score += {
        "beginner": 0,
        "amateur": 1,
        "intermediate": 2,
        "advanced": 4,
    }.get(experience, 1)
    score += {
        "never": 0,
        "monthly_1_2": 1,
        "weekly_1_2": 2,
        "weekly_3_4": 3,
        "almost_daily": 4,
    }.get(frequency, 0)
    score += {
        "no": 0,
        "sometimes": 1,
        "regularly": 3,
    }.get(team_experience, 0)
    score += {
        "low": 0,
        "medium": 1,
        "good": 2,
        "excellent": 3,
    }.get(endurance, 0)
    score += {
        "low": 0,
        "medium": 1,
        "good": 2,
        "excellent": 3,
    }.get(speed_reaction, 0)
    score += {
        "never": 0,
        "friends_sometimes": 1,
        "regularly": 3,
    }.get(competition, 0)

    if sports:
        score += 1
    if len(sports) >= 2:
        score += 1
    if user_role == "partner":
        score = max(3, score - 1)

    notes = (answers.get("notes") or "").lower()
    strong_markers = ("captain", "tournament", "league", "coach", "starter", "регуляр", "турнир", "лига", "трен")
    weak_markers = ("new", "just started", "rarely", "sometimes", "нович", "редко")
    if any(marker in notes for marker in strong_markers):
        score += 1
    if any(marker in notes for marker in weak_markers):
        score -= 1

    if experience == "beginner":
        score = min(score, 5)
    if frequency in {"never", "monthly_1_2"} and competition == "never":
        score = min(score, 4)

    return min(max(score, 2), 8)


def _derive_onboarding_strengths(answers: dict[str, str], language: str | None) -> list[str]:
    is_english = (language or "").lower().startswith("en")
    strengths: list[str] = []

    frequency = (answers.get("activity_frequency") or "").lower()
    if frequency in {"weekly_3_4", "almost_daily"}:
        strengths.append("consistent practice" if is_english else "стабильная игровая практика")

    competition = (answers.get("competition_frequency") or "").lower()
    if competition == "regularly":
        strengths.append("match experience" if is_english else "опыт соревновательных матчей")

    sports = _parse_list_answer(answers.get("sports_played"))
    if len(sports) >= 2:
        strengths.append("multi-sport background" if is_english else "разносторонний спортивный опыт")

    if not strengths:
        strengths.append("good growth potential" if is_english else "хороший потенциал для роста")

    return strengths[:3]


def _parse_list_answer(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


def _level_label_from_score(score: int, language: str | None) -> str:
    is_english = (language or "").lower().startswith("en")
    if score <= 3:
        return "beginner" if is_english else "начинающий"
    if score <= 6:
        return "developing" if is_english else "развивающийся"
    if score <= 8:
        return "strong amateur" if is_english else "сильный любитель"
    return "competitive" if is_english else "соревновательный уровень"


def _build_onboarding_summary(
    score: int,
    level_label: str,
    sport_focus: str | None,
    strengths: list[str],
    language: str | None,
) -> str:
    is_english = (language or "").lower().startswith("en")
    top_strength = strengths[0] if strengths else ("general readiness" if is_english else "общая готовность")

    if is_english:
        return (
            f"Estimated score: {score}/10. Your current level looks like {level_label}. "
            f"Main signal: {top_strength}. The score is intentionally conservative and never goes above 8."
        )

    return (
        f"Примерный балл: {score}/10. Сейчас уровень выглядит как {level_label}. "
        f"Главный сигнал: {top_strength}. Оценка сделана с запасом и не поднимается выше 8."
    )


def _request_onboarding_assessment(
    answers: dict[str, str],
    local_assessment: dict[str, Any],
    language: str | None,
    user_role: str | None,
) -> dict[str, Any]:
    instructions = (
        "You assess sports onboarding answers for a local sports marketplace. "
        "Return a conservative player score from 1 to 10. "
        "Never return a score above 8. "
        "Most users should land between 3 and 7. "
        "Use the provided heuristic score as an anchor, not a final answer. "
        "Keep the summary short and practical."
    )
    if language:
        instructions = f"{instructions} Reply in this language code when possible: {language}."

    payload = {
        "model": settings.openai_model,
        "instructions": instructions,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(
                            {
                                "user_role": user_role,
                                "answers": answers,
                                "heuristic_assessment": local_assessment,
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            }
        ],
        "max_output_tokens": 220,
        "reasoning": {"effort": "minimal"},
        "text": {
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "onboarding_score",
                "schema": ONBOARDING_SCORE_SCHEMA,
                "strict": True,
            },
        },
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=30) as client:
        response = client.post(OPENAI_RESPONSES_URL, headers=headers, json=payload)

    if response.status_code >= 400:
        raise AIServiceError(f"OpenAI request failed: {response.text}")

    data = response.json()
    parsed = _safe_json_loads(data.get("output_text"))
    if not parsed:
        raise AIServiceError("OpenAI onboarding evaluation returned no structured payload")
    return parsed


def _merge_onboarding_assessments(
    local_assessment: dict[str, Any],
    ai_assessment: dict[str, Any],
    language: str | None,
) -> dict[str, Any]:
    local_score = int(local_assessment["overall_score"])
    ai_score = int(ai_assessment.get("overall_score", local_score))
    merged_score = round((local_score * 0.65) + (ai_score * 0.35))

    if local_score <= 4:
        merged_score = min(merged_score, 5)
    merged_score = min(max(merged_score, 2), 8)

    strengths = ai_assessment.get("strengths") or local_assessment.get("strengths") or []
    strengths = [str(item).strip() for item in strengths if str(item).strip()][:3]

    level_label = _level_label_from_score(merged_score, language)
    summary = str(ai_assessment.get("summary") or "").strip()
    if not summary:
        summary = _build_onboarding_summary(
            score=merged_score,
            level_label=level_label,
            sport_focus=ai_assessment.get("sport_focus") or local_assessment.get("sport_focus"),
            strengths=strengths,
            language=language,
        )

    return {
        "overall_score": merged_score,
        "player_rating": calculate_player_rating(merged_score, 0),
        "level_label": level_label,
        "summary": summary,
        "sport_focus": ai_assessment.get("sport_focus") or local_assessment.get("sport_focus"),
        "strengths": strengths or local_assessment.get("strengths", []),
    }


def save_onboarding_assessment_for_user(db: Session, user: User, assessment: dict[str, Any]) -> None:
    user.onboarding_score = int(assessment["overall_score"])
    user.onboarding_level_label = str(assessment.get("level_label") or "")
    user.onboarding_summary = str(assessment.get("summary") or "")
    user.onboarding_sport_focus = assessment.get("sport_focus")
    user.onboarding_completed_at = datetime.now(UTC)
    db.add(user)


def _extract_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return str(response["output_text"]).strip()
    chunks: list[str] = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"].strip())
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _safe_json_loads(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_limit(value: Any) -> int:
    if isinstance(value, int):
        return min(max(value, 1), 10)
    return DEFAULT_RESULT_LIMIT


def _parse_date_start(value: Any) -> datetime:
    if not value:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        try:
            parsed_date = datetime.fromisoformat(f"{value}T00:00:00")
            return parsed_date.replace(tzinfo=UTC)
        except ValueError:
            return datetime.now(UTC)


def _parse_date_end(value: Any) -> datetime:
    raw = str(value)
    if len(raw) == 10 and raw.count("-") == 2:
        try:
            parsed_date = datetime.fromisoformat(f"{raw}T00:00:00")
            return datetime.combine(parsed_date.date(), time.max, tzinfo=UTC)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        try:
            parsed_date = datetime.fromisoformat(f"{value}T00:00:00")
            return datetime.combine(parsed_date.date(), time.max, tzinfo=UTC)
        except ValueError:
            return datetime.max.replace(tzinfo=UTC)
