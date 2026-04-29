from pydantic import BaseModel, Field, field_validator

from app.schemas.common import RequestModel, normalize_optional_text, normalize_text, validate_language_code


class ChatMessage(RequestModel):
    role: str = Field(pattern="^(user|assistant)$")
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return normalize_text(value, "text", max_length=4000)


class ChatRequest(RequestModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=8)
    language: str | None = Field(default=None, max_length=10)
    user_role: str | None = Field(default=None, pattern="^(player|partner|admin)$")

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        return validate_language_code(value)


class ChatReference(BaseModel):
    type: str
    title: str
    subtitle: str | None = None
    url: str | None = None


class ChatResponse(BaseModel):
    text: str
    references: list[ChatReference] = Field(default_factory=list)


class OnboardingEvaluationRequest(RequestModel):
    answers: dict[str, str] = Field(min_length=1, max_length=30)
    language: str | None = Field(default=None, max_length=10)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        return validate_language_code(value)

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for key, answer in value.items():
            normalized_key = normalize_text(str(key), "answer key", max_length=50)
            normalized_answer = normalize_optional_text(answer, f"answer '{normalized_key}'", max_length=500)
            if normalized_answer:
                cleaned[normalized_key] = normalized_answer
        if not cleaned:
            raise ValueError("answers must contain at least one non-empty answer")
        return cleaned


class OnboardingEvaluationResponse(BaseModel):
    overall_score: int = Field(ge=1, le=8)
    player_rating: float = Field(ge=1, le=8)
    level_label: str
    summary: str
    sport_focus: str | None = None
    strengths: list[str] = Field(default_factory=list)
