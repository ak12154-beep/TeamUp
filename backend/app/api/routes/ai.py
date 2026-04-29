from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.participant import EventParticipant
from app.models.user import User
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    OnboardingEvaluationRequest,
    OnboardingEvaluationResponse,
)
from app.services.ai_service import (
    AIServiceError,
    chat_with_assistant,
    evaluate_onboarding_answers,
    save_onboarding_assessment_for_user,
)
from app.services.player_rating_service import calculate_player_rating

router = APIRouter(prefix="/ai")


def _service_unavailable_message(language: str | None, context: str) -> str:
    """Возвращает локализованное сообщение о временной недоступности AI-функции."""
    is_english = (language or "").lower().startswith("en")
    if context == "assessment":
        if is_english:
            return "Level estimation is temporarily unavailable. Please try again later."
        return "Оценка уровня временно недоступна. Попробуйте еще раз позже."

    if is_english:
        return "Assistant is temporarily unavailable. Please try again later."
    return "Ассистент временно недоступен. Попробуйте еще раз позже."


def _existing_level_summary(score: int, level_label: str | None, language: str | None) -> str:
    """Формирует краткое описание уже сохраненной оценки уровня пользователя."""
    is_english = (language or "").lower().startswith("en")
    label = level_label or ("estimated level" if is_english else "примерный уровень")
    if is_english:
        return f"Your saved level is {score}/10. Current label: {label}. The system does not assign scores above 8."
    return f"Ваш сохраненный уровень: {score}/10. Текущая метка: {label}. Система не ставит баллы выше 8."


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обрабатывает запрос к AI-ассистенту и возвращает ответ с карточками-ссылками."""
    role = current_user.role or payload.user_role
    try:
        result = chat_with_assistant(
            db=db,
            messages=[message.model_dump() for message in payload.messages],
            language=payload.language,
            user_role=role,
        )
    except AIServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=_service_unavailable_message(payload.language, "chat"),
        ) from exc
    return ChatResponse(**result)


@router.post("/onboarding/evaluate", response_model=OnboardingEvaluationResponse)
def evaluate_onboarding(
    payload: OnboardingEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Оценивает onboarding-ответы пользователя и сохраняет результат в профиль."""
    try:
        games_played = db.scalar(
            select(func.count(EventParticipant.id)).where(
                EventParticipant.user_id == current_user.id,
                EventParticipant.status == "joined",
            )
        ) or 0

        if current_user.onboarding_score is not None:
            raw_score = current_user.onboarding_score
            score = min(raw_score, 8)
            return OnboardingEvaluationResponse(
                overall_score=score,
                player_rating=calculate_player_rating(raw_score, games_played),
                level_label=current_user.onboarding_level_label or "",
                summary=_existing_level_summary(
                    score,
                    current_user.onboarding_level_label,
                    payload.language,
                ),
                sport_focus=current_user.onboarding_sport_focus,
                strengths=[],
            )

        result = evaluate_onboarding_answers(
            answers=payload.answers,
            language=payload.language,
            user_role=current_user.role,
        )
        save_onboarding_assessment_for_user(db, current_user, result)
        db.commit()
        db.refresh(current_user)
    except AIServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=_service_unavailable_message(payload.language, "assessment"),
        ) from exc
    return OnboardingEvaluationResponse(**result)
